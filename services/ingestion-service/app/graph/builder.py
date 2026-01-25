"""Graph builder for orchestrating extraction and storage."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.graph.extractor import (
    EntityExtractor,
    ExtractionConfig,
    ExtractionResult,
    ExtractedEntity,
    ExtractedRelation,
)
from app.storage.graph_store import GraphStore

logger = logging.getLogger(__name__)


@dataclass
class GraphBuildConfig:
    """Configuration for graph building."""

    # Extraction settings
    extraction_config: ExtractionConfig = field(default_factory=ExtractionConfig)

    # Deduplication
    deduplicate_entities: bool = True
    merge_threshold: float = 0.9  # Similarity threshold for merging

    # Entity embeddings
    embed_entities: bool = False
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"


@dataclass
class GraphBuildResult:
    """Result of building a graph from documents."""

    nodes_created: int = 0
    nodes_updated: int = 0
    edges_created: int = 0
    edges_updated: int = 0
    chunks_processed: int = 0
    total_entities_extracted: int = 0
    total_relations_extracted: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)


class GraphBuilder:
    """
    Orchestrates entity extraction and graph storage.

    Handles:
    - Extracting entities/relations from text chunks
    - Deduplicating and merging entities
    - Storing nodes and edges in MongoDB
    - Optional entity embedding for semantic search
    """

    def __init__(
        self,
        graph_store: GraphStore,
        config: Optional[GraphBuildConfig] = None,
    ):
        """
        Initialize graph builder.

        Args:
            graph_store: GraphStore instance for storage
            config: Build configuration
        """
        self.store = graph_store
        self.config = config or GraphBuildConfig()
        self.extractor = EntityExtractor(self.config.extraction_config)
        self._embedder = None

    async def _get_embedder(self):
        """Get or create embedder for entity embeddings."""
        if self._embedder is None and self.config.embed_entities:
            from app.embedders.factory import get_embedder, EmbeddingProvider

            provider = EmbeddingProvider(self.config.embedding_provider)
            self._embedder = get_embedder(
                provider=provider,
                model=self.config.embedding_model,
            )
        return self._embedder

    async def close(self) -> None:
        """Clean up resources."""
        await self.extractor.close()
        if self._embedder:
            await self._embedder.close()

    async def build_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        config_id: str,
        document_id: Optional[str] = None,
    ) -> GraphBuildResult:
        """
        Build graph from a list of text chunks.

        Args:
            chunks: List of chunk dicts with 'content', 'chunk_id' keys
            config_id: Configuration ID
            document_id: Optional document ID

        Returns:
            GraphBuildResult with statistics
        """
        result = GraphBuildResult()

        for chunk in chunks:
            chunk_content = chunk.get("content", "")
            chunk_id = chunk.get("chunk_id", chunk.get("_id", ""))

            if not chunk_content:
                continue

            try:
                # Extract entities and relations
                extraction = await self.extractor.extract(chunk_content)
                result.chunks_processed += 1
                result.total_entities_extracted += len(extraction.entities)
                result.total_relations_extracted += len(extraction.relations)

                # Process extracted entities
                entity_node_map: Dict[str, str] = {}

                for entity in extraction.entities:
                    try:
                        node_id = await self.store.upsert_node(
                            config_id=config_id,
                            name=entity.name,
                            node_type=entity.entity_type,
                            properties=entity.properties,
                            source_chunk_id=str(chunk_id),
                            source_document_id=document_id,
                            confidence=entity.confidence,
                        )
                        entity_node_map[entity.name] = node_id
                        result.nodes_created += 1  # Counts both creates and updates
                    except Exception as e:
                        logger.error(f"Failed to store entity '{entity.name}': {e}")
                        result.errors.append({
                            "type": "entity_storage",
                            "entity": entity.name,
                            "error": str(e),
                        })

                # Process extracted relations
                for relation in extraction.relations:
                    try:
                        # Get or find node IDs
                        source_node_id = entity_node_map.get(relation.source_entity)
                        target_node_id = entity_node_map.get(relation.target_entity)

                        # If not in current batch, look up in store
                        if not source_node_id:
                            source_node = await self.store.get_node_by_name(
                                config_id, relation.source_entity
                            )
                            source_node_id = source_node.id if source_node else None

                        if not target_node_id:
                            target_node = await self.store.get_node_by_name(
                                config_id, relation.target_entity
                            )
                            target_node_id = target_node.id if target_node else None

                        # Create nodes if they don't exist
                        if not source_node_id:
                            source_node_id = await self.store.upsert_node(
                                config_id=config_id,
                                name=relation.source_entity,
                                node_type="unknown",
                                source_chunk_id=str(chunk_id),
                            )
                            entity_node_map[relation.source_entity] = source_node_id

                        if not target_node_id:
                            target_node_id = await self.store.upsert_node(
                                config_id=config_id,
                                name=relation.target_entity,
                                node_type="unknown",
                                source_chunk_id=str(chunk_id),
                            )
                            entity_node_map[relation.target_entity] = target_node_id

                        # Store edge
                        await self.store.upsert_edge(
                            config_id=config_id,
                            source_node_id=source_node_id,
                            target_node_id=target_node_id,
                            relation_type=relation.relation_type,
                            source_name=relation.source_entity,
                            target_name=relation.target_entity,
                            properties=relation.properties,
                            source_chunk_id=str(chunk_id),
                            confidence=relation.confidence,
                        )
                        result.edges_created += 1

                    except Exception as e:
                        logger.error(
                            f"Failed to store relation '{relation.source_entity}' -> '{relation.target_entity}': {e}"
                        )
                        result.errors.append({
                            "type": "relation_storage",
                            "relation": f"{relation.source_entity} -> {relation.target_entity}",
                            "error": str(e),
                        })

            except Exception as e:
                logger.error(f"Failed to process chunk {chunk_id}: {e}")
                result.errors.append({
                    "type": "chunk_processing",
                    "chunk_id": str(chunk_id),
                    "error": str(e),
                })

        # Embed entities if configured
        if self.config.embed_entities:
            await self._embed_new_entities(config_id, result)

        return result

    async def _embed_new_entities(
        self, config_id: str, result: GraphBuildResult
    ) -> None:
        """Embed entities that don't have embeddings yet."""
        embedder = await self._get_embedder()
        if not embedder:
            return

        try:
            # Get nodes without embeddings
            cursor = self.store.nodes.find(
                {"config_id": config_id, "embedding": {"$size": 0}},
                {"_id": 1, "name": 1, "node_type": 1},
            )

            nodes_to_embed = []
            async for doc in cursor:
                nodes_to_embed.append(doc)

            if not nodes_to_embed:
                return

            # Create text representations
            texts = [
                f"{doc['node_type']}: {doc['name']}" for doc in nodes_to_embed
            ]

            # Generate embeddings
            embedding_result = await embedder.embed(texts)

            # Update nodes with embeddings
            for i, doc in enumerate(nodes_to_embed):
                if i < len(embedding_result.embeddings):
                    await self.store.update_node_embedding(
                        str(doc["_id"]),
                        embedding_result.embeddings[i],
                        embedding_result.model,
                    )

            logger.info(f"Embedded {len(nodes_to_embed)} entities")

        except Exception as e:
            logger.error(f"Failed to embed entities: {e}")
            result.errors.append({
                "type": "entity_embedding",
                "error": str(e),
            })

    async def build_from_text(
        self,
        text: str,
        config_id: str,
        chunk_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> GraphBuildResult:
        """
        Build graph from a single text.

        Args:
            text: Text content
            config_id: Configuration ID
            chunk_id: Optional chunk ID
            document_id: Optional document ID

        Returns:
            GraphBuildResult with statistics
        """
        chunk = {
            "content": text,
            "chunk_id": chunk_id or "single_chunk",
        }
        return await self.build_from_chunks([chunk], config_id, document_id)

    async def get_entity_context(
        self,
        config_id: str,
        entity_names: List[str],
        depth: int = 1,
    ) -> Dict[str, Any]:
        """
        Get graph context for a list of entities.

        Useful for enriching RAG retrieval with graph knowledge.

        Args:
            config_id: Configuration ID
            entity_names: List of entity names to get context for
            depth: Traversal depth

        Returns:
            Dict with nodes and edges related to the entities
        """
        all_nodes = []
        all_edges = []
        seen_node_ids = set()
        seen_edge_ids = set()

        for name in entity_names:
            node = await self.store.get_node_by_name(config_id, name)
            if not node or not node.id:
                continue

            if node.id in seen_node_ids:
                continue

            # Get neighborhood
            subgraph = await self.store.get_neighbors(node.id, depth=depth)

            for n in subgraph["nodes"]:
                node_id = n.get("_id") or n.get("id")
                if node_id and node_id not in seen_node_ids:
                    seen_node_ids.add(node_id)
                    all_nodes.append(n)

            for e in subgraph["edges"]:
                edge_id = e.get("_id") or e.get("id")
                if edge_id and edge_id not in seen_edge_ids:
                    seen_edge_ids.add(edge_id)
                    all_edges.append(e)

        return {
            "nodes": all_nodes,
            "edges": all_edges,
            "entity_count": len(all_nodes),
            "relation_count": len(all_edges),
        }

    async def extract_entities_from_query(
        self,
        query: str,
    ) -> List[str]:
        """
        Extract entity mentions from a query.

        Useful for identifying which entities to look up in the graph.

        Args:
            query: User query text

        Returns:
            List of entity names found in query
        """
        result = await self.extractor.extract(query)
        return [entity.name for entity in result.entities]

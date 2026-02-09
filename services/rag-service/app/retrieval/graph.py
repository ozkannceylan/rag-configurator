"""Graph retriever using knowledge graph traversal."""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.retrieval.base import (
    BaseRetriever,
    RetrievalConfig,
    RetrievedChunk,
    SourceType,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph."""

    node_id: str
    name: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # Relevance score to query
    depth: int = 0  # Distance from query-matched nodes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type,
            "properties": self.properties,
            "score": self.score,
            "depth": self.depth,
        }


@dataclass
class GraphEdge:
    """Represents an edge in the knowledge graph."""

    edge_id: str
    source_node: str
    target_node: str
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "edge_id": self.edge_id,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "relation_type": self.relation_type,
            "properties": self.properties,
            "weight": self.weight,
        }


@dataclass
class GraphContext:
    """Context extracted from knowledge graph."""

    nodes: List[GraphNode]
    edges: List[GraphEdge]
    query_entities: List[str]  # Entities mentioned in query

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "query_entities": self.query_entities,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }


@dataclass
class GraphConfig:
    """Configuration for graph retrieval."""

    # Node matching
    top_k_nodes: int = 5
    min_node_score: float = 0.5

    # Traversal
    max_depth: int = 2
    max_nodes_per_level: int = 10

    # Chunk retrieval
    top_k_chunks: int = 10
    include_graph_context: bool = True

    # Embedding settings
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    # Vector search settings
    vector_index_name: str = "node_vector_index"
    num_candidates: int = 50

    # Filters
    node_types: Optional[List[str]] = None
    relation_types: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphConfig":
        """Create from dictionary."""
        return cls(
            top_k_nodes=data.get("top_k_nodes", 5),
            min_node_score=data.get("min_node_score", 0.5),
            max_depth=data.get("max_depth", 2),
            max_nodes_per_level=data.get("max_nodes_per_level", 10),
            top_k_chunks=data.get("top_k_chunks", 10),
            include_graph_context=data.get("include_graph_context", True),
            embedding_provider=data.get("embedding_provider", "openai"),
            embedding_model=data.get("embedding_model", "text-embedding-3-small"),
            vector_index_name=data.get("vector_index_name", "node_vector_index"),
            num_candidates=data.get("num_candidates", 50),
            node_types=data.get("node_types"),
            relation_types=data.get("relation_types"),
        )


@dataclass
class GraphRetrievalResult:
    """Result of graph-based retrieval."""

    chunks: List[RetrievedChunk]
    graph_context: Optional[GraphContext] = None
    query_entities: List[str] = field(default_factory=list)
    retrieval_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "graph_context": self.graph_context.to_dict() if self.graph_context else None,
            "query_entities": self.query_entities,
            "retrieval_time_ms": self.retrieval_time_ms,
        }


class GraphRetriever(BaseRetriever):
    """
    Knowledge graph traversal retriever.

    Retrieval flow:
    1. Query → Find matching nodes (semantic search on node embeddings)
    2. Traverse graph edges up to max_depth
    3. Collect chunks linked to discovered nodes
    4. Return chunks with graph context
    """

    NODES_COLLECTION = "graph_nodes"
    EDGES_COLLECTION = "graph_edges"
    CHUNKS_COLLECTION = "chunks"

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        config: Optional[RetrievalConfig] = None,
        graph_config: Optional[GraphConfig] = None,
        embedder: Optional[Any] = None,
    ):
        """
        Initialize graph retriever.

        Args:
            db: MongoDB database instance
            config: Base retrieval configuration
            graph_config: Graph-specific configuration
            embedder: Embedding provider instance
        """
        super().__init__(config)
        self.db = db
        self.nodes = db[self.NODES_COLLECTION]
        self.edges = db[self.EDGES_COLLECTION]
        self.chunks = db[self.CHUNKS_COLLECTION]
        self.graph_config = graph_config or GraphConfig()
        self._embedder = embedder
        self._use_vector_search: Optional[bool] = None

    async def _get_embedder(self):
        """Get or create embedder instance."""
        if self._embedder is None:
            from app.retrieval.embedder import get_embedder

            self._embedder = await get_embedder(
                provider=self.graph_config.embedding_provider,
                model=self.graph_config.embedding_model,
            )
        return self._embedder

    async def close(self) -> None:
        """Clean up resources."""
        if self._embedder and hasattr(self._embedder, "close"):
            await self._embedder.close()

    async def _check_vector_search(self) -> bool:
        """Check if vector search on nodes is available."""
        if self._use_vector_search is not None:
            return self._use_vector_search

        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.graph_config.vector_index_name,
                        "path": "embedding",
                        "queryVector": [0.0] * 1536,
                        "numCandidates": 1,
                        "limit": 1,
                    }
                },
                {"$limit": 1},
            ]
            await self.nodes.aggregate(pipeline).to_list(length=1)
            self._use_vector_search = True
            logger.info("Node vector search is available")
        except Exception as e:
            logger.info(f"Node vector search not available: {e}")
            logger.info("Falling back to cosine similarity")
            self._use_vector_search = False

        return self._use_vector_search

    async def retrieve(
        self,
        query: str,
        config_id: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks using knowledge graph traversal.

        Args:
            query: User query text
            config_id: RAG pipeline configuration ID
            top_k: Number of chunks to return
            filters: Additional filters

        Returns:
            List of retrieved chunks sorted by relevance
        """
        result = await self.retrieve_with_context(
            query=query,
            config_id=config_id,
            top_k=top_k,
            filters=filters,
        )
        return result.chunks

    async def retrieve_with_context(
        self,
        query: str,
        config_id: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> GraphRetrievalResult:
        """
        Retrieve chunks with full graph context.

        Args:
            query: User query text
            config_id: RAG pipeline configuration ID
            top_k: Number of chunks to return
            filters: Additional filters

        Returns:
            GraphRetrievalResult with chunks and context
        """
        import time

        start_time = time.time()
        k = top_k if top_k is not None else self.graph_config.top_k_chunks
        filters = filters or {}

        # Step 1: Find matching nodes from query
        matched_nodes = await self._find_matching_nodes(query, config_id, filters)

        if not matched_nodes:
            logger.debug("No matching nodes found in graph")
            return GraphRetrievalResult(
                chunks=[],
                retrieval_time_ms=(time.time() - start_time) * 1000,
            )

        # Step 2: Traverse graph to find related nodes
        all_nodes, all_edges = await self._traverse_graph(
            starting_nodes=matched_nodes,
            config_id=config_id,
            max_depth=self.graph_config.max_depth,
            filters=filters,
        )

        # Step 3: Collect chunks from all discovered nodes
        chunks = await self._get_chunks_from_nodes(
            nodes=all_nodes,
            config_id=config_id,
            top_k=k,
        )

        # Build graph context
        graph_context = None
        if self.graph_config.include_graph_context:
            graph_context = GraphContext(
                nodes=all_nodes,
                edges=all_edges,
                query_entities=[n.name for n in matched_nodes],
            )

        retrieval_time = (time.time() - start_time) * 1000

        return GraphRetrievalResult(
            chunks=chunks,
            graph_context=graph_context,
            query_entities=[n.name for n in matched_nodes],
            retrieval_time_ms=retrieval_time,
        )

    async def _find_matching_nodes(
        self,
        query: str,
        config_id: str,
        filters: Dict[str, Any],
    ) -> List[GraphNode]:
        """Find nodes matching the query using semantic search."""
        # Generate query embedding
        embedder = await self._get_embedder()
        query_embedding = await embedder.embed_query(query)

        if not query_embedding:
            return []

        use_vector = await self._check_vector_search()

        if use_vector:
            return await self._find_nodes_with_vector_search(
                query_embedding=query_embedding,
                config_id=config_id,
                filters=filters,
            )
        else:
            return await self._find_nodes_with_cosine(
                query_embedding=query_embedding,
                config_id=config_id,
                filters=filters,
            )

    async def _find_nodes_with_vector_search(
        self,
        query_embedding: List[float],
        config_id: str,
        filters: Dict[str, Any],
    ) -> List[GraphNode]:
        """Find nodes using MongoDB Atlas Vector Search."""
        # Build filter
        vector_filter: Dict[str, Any] = {"config_id": config_id}

        if self.graph_config.node_types:
            vector_filter["node_type"] = {"$in": self.graph_config.node_types}

        # Build pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.graph_config.vector_index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": self.graph_config.num_candidates,
                    "limit": self.graph_config.top_k_nodes,
                    "filter": vector_filter,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "node_type": 1,
                    "properties": 1,
                    "source_chunks": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        cursor = self.nodes.aggregate(pipeline)
        results = await cursor.to_list(length=self.graph_config.top_k_nodes)

        nodes = []
        for doc in results:
            score = doc.get("score", 0.0)
            if score >= self.graph_config.min_node_score:
                node = GraphNode(
                    node_id=str(doc.get("_id")),
                    name=doc.get("name", ""),
                    node_type=doc.get("node_type", "unknown"),
                    properties=doc.get("properties", {}),
                    score=score,
                    depth=0,
                )
                nodes.append(node)

        return nodes

    async def _find_nodes_with_cosine(
        self,
        query_embedding: List[float],
        config_id: str,
        filters: Dict[str, Any],
    ) -> List[GraphNode]:
        """Find nodes using in-memory cosine similarity."""
        # Build query filter
        query_filter: Dict[str, Any] = {
            "config_id": config_id,
            "embedding": {"$exists": True, "$ne": []},
        }

        if self.graph_config.node_types:
            query_filter["node_type"] = {"$in": self.graph_config.node_types}

        # Fetch nodes with embeddings
        cursor = self.nodes.find(query_filter)
        docs = await cursor.to_list(length=500)  # Limit for performance

        if not docs:
            return []

        # Calculate cosine similarity
        scored_nodes = []
        for doc in docs:
            node_embedding = doc.get("embedding", [])
            if not node_embedding:
                continue

            score = self._cosine_similarity(query_embedding, node_embedding)

            if score >= self.graph_config.min_node_score:
                node = GraphNode(
                    node_id=str(doc.get("_id")),
                    name=doc.get("name", ""),
                    node_type=doc.get("node_type", "unknown"),
                    properties=doc.get("properties", {}),
                    score=score,
                    depth=0,
                )
                scored_nodes.append(node)

        # Sort by score and take top_k
        scored_nodes.sort(key=lambda x: x.score, reverse=True)
        return scored_nodes[: self.graph_config.top_k_nodes]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def _traverse_graph(
        self,
        starting_nodes: List[GraphNode],
        config_id: str,
        max_depth: int,
        filters: Dict[str, Any],
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Traverse graph starting from matched nodes.

        Uses BFS to traverse up to max_depth levels.
        """
        all_nodes: Dict[str, GraphNode] = {n.node_id: n for n in starting_nodes}
        all_edges: Dict[str, GraphEdge] = {}

        current_level_ids: Set[str] = {n.node_id for n in starting_nodes}

        for depth in range(1, max_depth + 1):
            if not current_level_ids:
                break

            # Find edges connected to current level nodes
            edge_query: Dict[str, Any] = {
                "config_id": config_id,
                "$or": [
                    {"source_node": {"$in": list(current_level_ids)}},
                    {"target_node": {"$in": list(current_level_ids)}},
                ],
            }

            # Filter by relation types if specified
            if self.graph_config.relation_types:
                edge_query["relation_type"] = {"$in": self.graph_config.relation_types}

            cursor = self.edges.find(edge_query)
            edge_docs = await cursor.to_list(length=1000)

            next_level_ids: Set[str] = set()

            for edge_doc in edge_docs:
                edge_id = str(edge_doc.get("_id"))
                if edge_id in all_edges:
                    continue

                edge = GraphEdge(
                    edge_id=edge_id,
                    source_node=edge_doc.get("source_node", ""),
                    target_node=edge_doc.get("target_node", ""),
                    relation_type=edge_doc.get("relation_type", ""),
                    properties=edge_doc.get("properties", {}),
                    weight=edge_doc.get("weight", 1.0),
                )
                all_edges[edge_id] = edge

                # Find connected nodes
                for node_id in [edge.source_node, edge.target_node]:
                    if node_id not in all_nodes:
                        next_level_ids.add(node_id)

            # Limit nodes per level
            if len(next_level_ids) > self.graph_config.max_nodes_per_level:
                next_level_ids = set(list(next_level_ids)[: self.graph_config.max_nodes_per_level])

            # Fetch node details for new nodes
            if next_level_ids:
                node_cursor = self.nodes.find({"_id": {"$in": list(next_level_ids)}})
                node_docs = await node_cursor.to_list(length=len(next_level_ids))

                for node_doc in node_docs:
                    node_id = str(node_doc.get("_id"))
                    node = GraphNode(
                        node_id=node_id,
                        name=node_doc.get("name", ""),
                        node_type=node_doc.get("node_type", "unknown"),
                        properties=node_doc.get("properties", {}),
                        score=0.0,  # Traversed nodes have lower relevance
                        depth=depth,
                    )
                    all_nodes[node_id] = node

            current_level_ids = next_level_ids

        return list(all_nodes.values()), list(all_edges.values())

    async def _get_chunks_from_nodes(
        self,
        nodes: List[GraphNode],
        config_id: str,
        top_k: int,
    ) -> List[RetrievedChunk]:
        """Get chunks linked to the discovered nodes."""
        # Collect all source chunk IDs from nodes
        chunk_ids: Set[str] = set()
        node_chunk_map: Dict[str, List[str]] = {}  # chunk_id -> node_ids

        for node in nodes:
            # Get source chunks from node properties or look up
            source_chunks = node.properties.get("source_chunks", [])

            if not source_chunks:
                # Look up in database
                node_doc = await self.nodes.find_one(
                    {"_id": node.node_id},
                    {"source_chunks": 1},
                )
                if node_doc:
                    source_chunks = node_doc.get("source_chunks", [])

            for chunk_id in source_chunks:
                chunk_ids.add(chunk_id)
                if chunk_id not in node_chunk_map:
                    node_chunk_map[chunk_id] = []
                node_chunk_map[chunk_id].append(node.node_id)

        if not chunk_ids:
            return []

        # Fetch chunks
        cursor = self.chunks.find(
            {
                "_id": {"$in": list(chunk_ids)},
                "config_id": config_id,
            },
            {"embedding": 0},  # Exclude large embedding field
        )
        chunk_docs = await cursor.to_list(length=top_k * 2)

        # Build node score map
        node_scores = {n.node_id: n.score for n in nodes}

        # Convert to RetrievedChunk with scores based on connected nodes
        chunks = []
        for doc in chunk_docs:
            chunk_id = str(doc.get("_id"))

            # Calculate score based on connected nodes
            connected_node_ids = node_chunk_map.get(chunk_id, [])
            if connected_node_ids:
                # Use max score of connected nodes
                score = max(node_scores.get(nid, 0.0) for nid in connected_node_ids)
            else:
                score = 0.5  # Default score

            # Enrich with document metadata
            doc_metadata = await self._get_document_metadata(doc.get("document_id"))
            if doc_metadata:
                doc["file_name"] = doc_metadata.get("file_name")
                doc["file_path"] = doc_metadata.get("file_path")
                doc["file_type"] = doc_metadata.get("file_type")

            # Add graph context to metadata
            doc_metadata_extra = doc.get("metadata", {})
            doc_metadata_extra["connected_entities"] = [
                nodes_dict.get(nid, {}).get("name", nid)
                for nid in connected_node_ids
                if (nodes_dict := {n.node_id: {"name": n.name} for n in nodes})
            ]

            chunk = RetrievedChunk.from_mongo_doc(
                doc=doc,
                score=score,
                source_type=SourceType.GRAPH,
            )
            chunk.metadata["connected_entities"] = [
                n.name for n in nodes if n.node_id in connected_node_ids
            ]
            chunks.append(chunk)

        # Sort by score and take top_k
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks[:top_k]

    async def _get_document_metadata(
        self, document_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get document metadata for enrichment."""
        if not document_id:
            return None

        try:
            doc = await self.db["documents"].find_one(
                {"_id": document_id},
                {"file_name": 1, "file_path": 1, "file_type": 1},
            )
            return doc
        except Exception:
            return None

    async def get_entity_subgraph(
        self,
        entity_names: List[str],
        config_id: str,
        max_depth: int = 2,
    ) -> GraphContext:
        """
        Get subgraph centered on specific entities.

        Useful for explaining relationships between known entities.

        Args:
            entity_names: List of entity names to find
            config_id: Configuration ID
            max_depth: Maximum traversal depth

        Returns:
            GraphContext with nodes and edges
        """
        # Find nodes by name
        starting_nodes: List[GraphNode] = []

        for name in entity_names:
            node_doc = await self.nodes.find_one({
                "config_id": config_id,
                "name_normalized": name.lower().strip(),
            })

            if node_doc:
                node = GraphNode(
                    node_id=str(node_doc.get("_id")),
                    name=node_doc.get("name", ""),
                    node_type=node_doc.get("node_type", "unknown"),
                    properties=node_doc.get("properties", {}),
                    score=1.0,
                    depth=0,
                )
                starting_nodes.append(node)

        if not starting_nodes:
            return GraphContext(nodes=[], edges=[], query_entities=entity_names)

        # Traverse graph
        all_nodes, all_edges = await self._traverse_graph(
            starting_nodes=starting_nodes,
            config_id=config_id,
            max_depth=max_depth,
            filters={},
        )

        return GraphContext(
            nodes=all_nodes,
            edges=all_edges,
            query_entities=[n.name for n in starting_nodes],
        )

    async def find_path(
        self,
        source_entity: str,
        target_entity: str,
        config_id: str,
        max_depth: int = 5,
    ) -> Optional[List[GraphEdge]]:
        """
        Find shortest path between two entities.

        Args:
            source_entity: Starting entity name
            target_entity: Target entity name
            config_id: Configuration ID
            max_depth: Maximum path length

        Returns:
            List of edges in the path, or None if no path found
        """
        # Find source node
        source_doc = await self.nodes.find_one({
            "config_id": config_id,
            "name_normalized": source_entity.lower().strip(),
        })
        if not source_doc:
            return None

        # Find target node
        target_doc = await self.nodes.find_one({
            "config_id": config_id,
            "name_normalized": target_entity.lower().strip(),
        })
        if not target_doc:
            return None

        source_id = str(source_doc.get("_id"))
        target_id = str(target_doc.get("_id"))

        if source_id == target_id:
            return []

        # BFS to find shortest path
        visited: Set[str] = {source_id}
        queue: List[Tuple[str, List[GraphEdge]]] = [(source_id, [])]

        for _ in range(max_depth):
            if not queue:
                break

            next_queue: List[Tuple[str, List[GraphEdge]]] = []

            for current_id, path in queue:
                # Get edges from current node
                cursor = self.edges.find({
                    "config_id": config_id,
                    "$or": [
                        {"source_node": current_id},
                        {"target_node": current_id},
                    ],
                })
                edge_docs = await cursor.to_list(length=100)

                for edge_doc in edge_docs:
                    edge = GraphEdge(
                        edge_id=str(edge_doc.get("_id")),
                        source_node=edge_doc.get("source_node", ""),
                        target_node=edge_doc.get("target_node", ""),
                        relation_type=edge_doc.get("relation_type", ""),
                        properties=edge_doc.get("properties", {}),
                        weight=edge_doc.get("weight", 1.0),
                    )

                    # Get other node
                    other_id = (
                        edge.target_node
                        if edge.source_node == current_id
                        else edge.source_node
                    )

                    if other_id == target_id:
                        return path + [edge]

                    if other_id not in visited:
                        visited.add(other_id)
                        next_queue.append((other_id, path + [edge]))

            queue = next_queue

        return None

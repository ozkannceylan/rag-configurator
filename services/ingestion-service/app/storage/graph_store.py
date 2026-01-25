"""Graph storage for nodes and edges in MongoDB."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GraphNode(BaseModel):
    """MongoDB document model for graph nodes."""

    id: Optional[str] = Field(None, alias="_id")
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    node_type: str = Field(..., description="Entity type")
    name: str = Field(..., description="Entity name")
    name_normalized: str = Field("", description="Normalized name for matching")

    # Properties
    properties: Dict[str, Any] = Field(default_factory=dict)

    # Embedding for semantic search
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = Field("")

    # Source tracking
    source_chunks: List[str] = Field(
        default_factory=list, description="Chunk IDs where entity was found"
    )
    source_documents: List[str] = Field(
        default_factory=list, description="Document IDs where entity was found"
    )

    # Metadata
    mention_count: int = Field(1, description="Number of times entity was mentioned")
    confidence: float = Field(1.0, description="Extraction confidence")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        if self.id:
            data["_id"] = self.id
        return data


class GraphEdge(BaseModel):
    """MongoDB document model for graph edges."""

    id: Optional[str] = Field(None, alias="_id")
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    relation_type: str = Field(..., description="Relationship type")

    # Node references
    source_node: str = Field(..., description="Source node ID")
    target_node: str = Field(..., description="Target node ID")

    # For quick lookups without joins
    source_name: str = Field("", description="Source entity name")
    target_name: str = Field("", description="Target entity name")

    # Properties
    properties: Dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(1.0, description="Edge weight/strength")
    confidence: float = Field(1.0, description="Extraction confidence")

    # Source tracking
    source_chunks: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        if self.id:
            data["_id"] = self.id
        return data


class GraphStore:
    """
    Storage layer for knowledge graph nodes and edges.

    Uses MongoDB collections:
    - graph_nodes: Entity nodes with embeddings
    - graph_edges: Relationships between nodes
    """

    NODES_COLLECTION = "graph_nodes"
    EDGES_COLLECTION = "graph_edges"

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize graph store.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.nodes = db[self.NODES_COLLECTION]
        self.edges = db[self.EDGES_COLLECTION]

    async def initialize_indexes(self) -> None:
        """Create necessary indexes for efficient queries."""
        logger.info("Creating graph store indexes...")

        # Node indexes
        await self.nodes.create_index("config_id")
        await self.nodes.create_index("node_type")
        await self.nodes.create_index("name_normalized")
        await self.nodes.create_index([("config_id", 1), ("name_normalized", 1)])
        await self.nodes.create_index([("config_id", 1), ("node_type", 1)])

        # Edge indexes
        await self.edges.create_index("config_id")
        await self.edges.create_index("relation_type")
        await self.edges.create_index("source_node")
        await self.edges.create_index("target_node")
        await self.edges.create_index([("config_id", 1), ("source_node", 1)])
        await self.edges.create_index([("config_id", 1), ("target_node", 1)])

        logger.info("Graph store indexes created")

    # ==================== Node Operations ====================

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize entity name for matching."""
        return name.lower().strip()

    async def upsert_node(
        self,
        config_id: str,
        name: str,
        node_type: str,
        properties: Optional[Dict[str, Any]] = None,
        source_chunk_id: Optional[str] = None,
        source_document_id: Optional[str] = None,
        confidence: float = 1.0,
    ) -> str:
        """
        Insert or update a node, merging if it already exists.

        Args:
            config_id: Configuration ID
            name: Entity name
            node_type: Entity type
            properties: Additional properties
            source_chunk_id: Source chunk ID
            source_document_id: Source document ID
            confidence: Extraction confidence

        Returns:
            Node ID
        """
        name_normalized = self.normalize_name(name)

        # Check for existing node
        existing = await self.nodes.find_one(
            {"config_id": config_id, "name_normalized": name_normalized}
        )

        if existing:
            # Update existing node
            update_data: Dict[str, Any] = {
                "updated_at": datetime.utcnow(),
            }

            # Merge properties
            if properties:
                for key, value in properties.items():
                    update_data[f"properties.{key}"] = value

            # Add source references
            add_to_set: Dict[str, Any] = {}
            if source_chunk_id:
                add_to_set["source_chunks"] = source_chunk_id
            if source_document_id:
                add_to_set["source_documents"] = source_document_id

            update_ops: Dict[str, Any] = {
                "$set": update_data,
                "$inc": {"mention_count": 1},
            }
            if add_to_set:
                update_ops["$addToSet"] = add_to_set

            await self.nodes.update_one({"_id": existing["_id"]}, update_ops)
            return str(existing["_id"])
        else:
            # Create new node
            node = GraphNode(
                config_id=config_id,
                name=name,
                name_normalized=name_normalized,
                node_type=node_type,
                properties=properties or {},
                source_chunks=[source_chunk_id] if source_chunk_id else [],
                source_documents=[source_document_id] if source_document_id else [],
                confidence=confidence,
            )

            data = node.to_mongo()
            data["_id"] = str(ObjectId())

            await self.nodes.insert_one(data)
            return data["_id"]

    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        doc = await self.nodes.find_one({"_id": node_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return GraphNode(**doc)
        return None

    async def get_node_by_name(
        self, config_id: str, name: str
    ) -> Optional[GraphNode]:
        """Get a node by name."""
        name_normalized = self.normalize_name(name)
        doc = await self.nodes.find_one(
            {"config_id": config_id, "name_normalized": name_normalized}
        )
        if doc:
            doc["_id"] = str(doc["_id"])
            return GraphNode(**doc)
        return None

    async def get_nodes_by_config(
        self,
        config_id: str,
        node_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GraphNode]:
        """Get nodes for a config, optionally filtered by type."""
        query: Dict[str, Any] = {"config_id": config_id}
        if node_type:
            query["node_type"] = node_type

        cursor = self.nodes.find(query).skip(skip).limit(limit)
        nodes = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            nodes.append(GraphNode(**doc))
        return nodes

    async def get_node_types(self, config_id: str) -> List[str]:
        """Get all distinct node types for a config."""
        return await self.nodes.distinct("node_type", {"config_id": config_id})

    async def update_node_embedding(
        self, node_id: str, embedding: List[float], model: str
    ) -> bool:
        """Update a node's embedding."""
        result = await self.nodes.update_one(
            {"_id": node_id},
            {
                "$set": {
                    "embedding": embedding,
                    "embedding_model": model,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.modified_count > 0

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its edges."""
        # Delete connected edges
        await self.edges.delete_many(
            {"$or": [{"source_node": node_id}, {"target_node": node_id}]}
        )

        # Delete node
        result = await self.nodes.delete_one({"_id": node_id})
        return result.deleted_count > 0

    async def delete_nodes_by_config(self, config_id: str) -> int:
        """Delete all nodes and edges for a config."""
        await self.edges.delete_many({"config_id": config_id})
        result = await self.nodes.delete_many({"config_id": config_id})
        return result.deleted_count

    async def count_nodes(self, config_id: str) -> int:
        """Count nodes for a config."""
        return await self.nodes.count_documents({"config_id": config_id})

    # ==================== Edge Operations ====================

    async def upsert_edge(
        self,
        config_id: str,
        source_node_id: str,
        target_node_id: str,
        relation_type: str,
        source_name: str = "",
        target_name: str = "",
        properties: Optional[Dict[str, Any]] = None,
        source_chunk_id: Optional[str] = None,
        confidence: float = 1.0,
    ) -> str:
        """
        Insert or update an edge.

        Args:
            config_id: Configuration ID
            source_node_id: Source node ID
            target_node_id: Target node ID
            relation_type: Relationship type
            source_name: Source entity name
            target_name: Target entity name
            properties: Additional properties
            source_chunk_id: Source chunk ID
            confidence: Extraction confidence

        Returns:
            Edge ID
        """
        # Check for existing edge
        existing = await self.edges.find_one(
            {
                "config_id": config_id,
                "source_node": source_node_id,
                "target_node": target_node_id,
                "relation_type": relation_type,
            }
        )

        if existing:
            # Update existing edge
            update_data: Dict[str, Any] = {
                "updated_at": datetime.utcnow(),
            }

            if properties:
                for key, value in properties.items():
                    update_data[f"properties.{key}"] = value

            update_ops: Dict[str, Any] = {
                "$set": update_data,
                "$inc": {"weight": 1},
            }

            if source_chunk_id:
                update_ops["$addToSet"] = {"source_chunks": source_chunk_id}

            await self.edges.update_one({"_id": existing["_id"]}, update_ops)
            return str(existing["_id"])
        else:
            # Create new edge
            edge = GraphEdge(
                config_id=config_id,
                source_node=source_node_id,
                target_node=target_node_id,
                relation_type=relation_type,
                source_name=source_name,
                target_name=target_name,
                properties=properties or {},
                source_chunks=[source_chunk_id] if source_chunk_id else [],
                confidence=confidence,
            )

            data = edge.to_mongo()
            data["_id"] = str(ObjectId())

            await self.edges.insert_one(data)
            return data["_id"]

    async def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        """Get an edge by ID."""
        doc = await self.edges.find_one({"_id": edge_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return GraphEdge(**doc)
        return None

    async def get_edges_by_node(
        self,
        node_id: str,
        direction: str = "both",
        relation_type: Optional[str] = None,
    ) -> List[GraphEdge]:
        """
        Get edges connected to a node.

        Args:
            node_id: Node ID
            direction: "outgoing", "incoming", or "both"
            relation_type: Optional filter by relation type

        Returns:
            List of edges
        """
        if direction == "outgoing":
            query: Dict[str, Any] = {"source_node": node_id}
        elif direction == "incoming":
            query = {"target_node": node_id}
        else:
            query = {"$or": [{"source_node": node_id}, {"target_node": node_id}]}

        if relation_type:
            query["relation_type"] = relation_type

        cursor = self.edges.find(query)
        edges = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            edges.append(GraphEdge(**doc))
        return edges

    async def get_edges_by_config(
        self,
        config_id: str,
        relation_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GraphEdge]:
        """Get edges for a config."""
        query: Dict[str, Any] = {"config_id": config_id}
        if relation_type:
            query["relation_type"] = relation_type

        cursor = self.edges.find(query).skip(skip).limit(limit)
        edges = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            edges.append(GraphEdge(**doc))
        return edges

    async def get_relation_types(self, config_id: str) -> List[str]:
        """Get all distinct relation types for a config."""
        return await self.edges.distinct("relation_type", {"config_id": config_id})

    async def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge."""
        result = await self.edges.delete_one({"_id": edge_id})
        return result.deleted_count > 0

    async def count_edges(self, config_id: str) -> int:
        """Count edges for a config."""
        return await self.edges.count_documents({"config_id": config_id})

    # ==================== Graph Traversal ====================

    async def get_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        relation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get neighboring nodes up to specified depth.

        Args:
            node_id: Starting node ID
            depth: Maximum traversal depth
            relation_types: Optional filter by relation types

        Returns:
            Dict with nodes and edges in the subgraph
        """
        visited_nodes: set = {node_id}
        all_nodes: List[GraphNode] = []
        all_edges: List[GraphEdge] = []

        # Get starting node
        start_node = await self.get_node(node_id)
        if start_node:
            all_nodes.append(start_node)

        current_level = [node_id]

        for _ in range(depth):
            next_level = []

            for current_node_id in current_level:
                # Get edges from this node
                edges = await self.get_edges_by_node(current_node_id)

                for edge in edges:
                    # Filter by relation type if specified
                    if relation_types and edge.relation_type not in relation_types:
                        continue

                    all_edges.append(edge)

                    # Get the other node
                    other_node_id = (
                        edge.target_node
                        if edge.source_node == current_node_id
                        else edge.source_node
                    )

                    if other_node_id not in visited_nodes:
                        visited_nodes.add(other_node_id)
                        next_level.append(other_node_id)

                        other_node = await self.get_node(other_node_id)
                        if other_node:
                            all_nodes.append(other_node)

            current_level = next_level
            if not current_level:
                break

        return {
            "nodes": [n.model_dump() for n in all_nodes],
            "edges": [e.model_dump() for e in all_edges],
        }

    async def find_path(
        self,
        source_node_id: str,
        target_node_id: str,
        max_depth: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find a path between two nodes using BFS.

        Args:
            source_node_id: Starting node ID
            target_node_id: Target node ID
            max_depth: Maximum path length

        Returns:
            List of edges in the path, or None if no path found
        """
        if source_node_id == target_node_id:
            return []

        # BFS with path tracking
        visited = {source_node_id}
        queue = [(source_node_id, [])]

        for _ in range(max_depth):
            if not queue:
                break

            next_queue = []

            for current_id, path in queue:
                edges = await self.get_edges_by_node(current_id)

                for edge in edges:
                    other_id = (
                        edge.target_node
                        if edge.source_node == current_id
                        else edge.source_node
                    )

                    if other_id == target_node_id:
                        return path + [edge.model_dump()]

                    if other_id not in visited:
                        visited.add(other_id)
                        next_queue.append((other_id, path + [edge.model_dump()]))

            queue = next_queue

        return None

    # ==================== Stats ====================

    async def get_stats(self, config_id: str) -> Dict[str, Any]:
        """Get statistics for a config's graph."""
        node_count = await self.count_nodes(config_id)
        edge_count = await self.count_edges(config_id)
        node_types = await self.get_node_types(config_id)
        relation_types = await self.get_relation_types(config_id)

        return {
            "config_id": config_id,
            "node_count": node_count,
            "edge_count": edge_count,
            "node_types": node_types,
            "relation_types": relation_types,
        }

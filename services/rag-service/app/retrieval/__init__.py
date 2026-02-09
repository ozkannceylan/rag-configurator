"""Retrieval module for RAG pipelines."""

from app.retrieval.base import BaseRetriever, RetrievedChunk, RetrievalConfig, SourceType
from app.retrieval.vector import VectorRetriever
from app.retrieval.keyword import KeywordRetriever, KeywordConfig
from app.retrieval.graph import GraphRetriever, GraphConfig, GraphContext, GraphNode, GraphEdge
from app.retrieval.hybrid import HybridRetriever, HybridConfig, FusionMethod, reciprocal_rank_fusion
from app.retrieval.factory import get_retriever, get_retriever_from_config, RetrievalMethod

__all__ = [
    # Base
    "BaseRetriever",
    "RetrievedChunk",
    "RetrievalConfig",
    "SourceType",
    # Vector
    "VectorRetriever",
    # Keyword
    "KeywordRetriever",
    "KeywordConfig",
    # Graph
    "GraphRetriever",
    "GraphConfig",
    "GraphContext",
    "GraphNode",
    "GraphEdge",
    # Hybrid
    "HybridRetriever",
    "HybridConfig",
    "FusionMethod",
    "reciprocal_rank_fusion",
    # Factory
    "get_retriever",
    "get_retriever_from_config",
    "RetrievalMethod",
]

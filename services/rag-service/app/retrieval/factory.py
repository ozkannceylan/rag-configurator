"""Factory functions for creating retrievers."""

import logging
from enum import StrEnum
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.retrieval.base import BaseRetriever, RetrievalConfig

logger = logging.getLogger(__name__)


class RetrievalMethod(StrEnum):
    """Available retrieval methods."""

    NAIVE = "naive"  # Vector only (simple RAG)
    VECTOR = "vector"  # Vector similarity search
    KEYWORD = "keyword"  # Full-text search
    GRAPH = "graph"  # Knowledge graph traversal
    HYBRID = "hybrid"  # Combined retrieval
    ADVANCED = "advanced"  # Hybrid with all features


def get_retriever(
    method: RetrievalMethod,
    db: AsyncIOMotorDatabase,
    config: RetrievalConfig | None = None,
    **kwargs: Any,
) -> BaseRetriever:
    """
    Factory function to create appropriate retriever.

    Args:
        method: Retrieval method to use
        db: MongoDB database instance
        config: Base retrieval configuration
        **kwargs: Additional configuration for specific retrievers

    Returns:
        Configured retriever instance
    """
    if method == RetrievalMethod.NAIVE or method == RetrievalMethod.VECTOR:
        from app.retrieval.vector import VectorRetriever

        return VectorRetriever(
            db=db,
            config=config,
            embedder=kwargs.get("embedder"),
        )

    elif method == RetrievalMethod.KEYWORD:
        from app.retrieval.keyword import KeywordConfig, KeywordRetriever

        keyword_config = kwargs.get("keyword_config")
        if keyword_config is None and "keyword_config_dict" in kwargs:
            keyword_config = KeywordConfig.from_dict(kwargs["keyword_config_dict"])

        return KeywordRetriever(
            db=db,
            config=config,
            keyword_config=keyword_config,
        )

    elif method == RetrievalMethod.GRAPH:
        from app.retrieval.graph import GraphConfig, GraphRetriever

        graph_config = kwargs.get("graph_config")
        if graph_config is None and "graph_config_dict" in kwargs:
            graph_config = GraphConfig.from_dict(kwargs["graph_config_dict"])

        return GraphRetriever(
            db=db,
            config=config,
            graph_config=graph_config,
            embedder=kwargs.get("embedder"),
        )

    elif method == RetrievalMethod.HYBRID:
        from app.retrieval.hybrid import HybridConfig, HybridRetriever

        hybrid_config = kwargs.get("hybrid_config")
        if hybrid_config is None and "hybrid_config_dict" in kwargs:
            hybrid_config = HybridConfig.from_dict(kwargs["hybrid_config_dict"])

        return HybridRetriever(
            db=db,
            config=config,
            hybrid_config=hybrid_config,
        )

    elif method == RetrievalMethod.ADVANCED:
        from app.retrieval.hybrid import HybridConfig, HybridRetriever

        # Advanced mode: enable all retrievers
        hybrid_config = kwargs.get("hybrid_config")
        if hybrid_config is None:
            hybrid_config = HybridConfig(
                use_vector=True,
                use_keyword=True,
                use_graph=True,
            )
            if "hybrid_config_dict" in kwargs:
                config_dict = kwargs["hybrid_config_dict"]
                config_dict.setdefault("use_vector", True)
                config_dict.setdefault("use_keyword", True)
                config_dict.setdefault("use_graph", True)
                hybrid_config = HybridConfig.from_dict(config_dict)

        return HybridRetriever(
            db=db,
            config=config,
            hybrid_config=hybrid_config,
        )

    else:
        raise ValueError(f"Unknown retrieval method: {method}")


def get_retriever_from_config(
    db: AsyncIOMotorDatabase,
    pipeline_config: dict[str, Any],
) -> BaseRetriever:
    """
    Create retriever from pipeline configuration.

    Args:
        db: MongoDB database instance
        pipeline_config: RAG pipeline configuration dict

    Returns:
        Configured retriever instance
    """
    retrieval_config = pipeline_config.get("retrieval", {})

    # Determine method
    method_str = retrieval_config.get("method", "naive")
    try:
        method = RetrievalMethod(method_str.lower())
    except ValueError:
        logger.warning(f"Unknown retrieval method: {method_str}, defaulting to naive")
        method = RetrievalMethod.NAIVE

    # Build base config
    base_config = RetrievalConfig(
        top_k=retrieval_config.get("top_k", 5),
        min_score=retrieval_config.get("min_score", 0.0),
        embedding_provider=retrieval_config.get("embedding_provider", "openai"),
        embedding_model=retrieval_config.get(
            "embedding_model", "text-embedding-3-small"
        ),
        folder_paths=retrieval_config.get("folder_paths"),
        access_tags=retrieval_config.get("access_tags"),
    )

    # Build method-specific configs
    kwargs: dict[str, Any] = {}

    if method == RetrievalMethod.KEYWORD:
        kwargs["keyword_config_dict"] = retrieval_config.get("keyword", {})

    elif method == RetrievalMethod.GRAPH:
        kwargs["graph_config_dict"] = retrieval_config.get("graph", {})

    elif method in (RetrievalMethod.HYBRID, RetrievalMethod.ADVANCED):
        kwargs["hybrid_config_dict"] = retrieval_config.get("hybrid", {})

    return get_retriever(
        method=method,
        db=db,
        config=base_config,
        **kwargs,
    )


def create_retrieval_config(
    top_k: int = 5,
    min_score: float = 0.0,
    embedding_provider: str = "openai",
    embedding_model: str = "text-embedding-3-small",
    folder_paths: list | None = None,
    access_tags: list | None = None,
    **kwargs: Any,
) -> RetrievalConfig:
    """
    Helper to create RetrievalConfig with sensible defaults.

    Args:
        top_k: Number of results to retrieve
        min_score: Minimum score threshold
        embedding_provider: Embedding provider name
        embedding_model: Embedding model name
        folder_paths: Folder paths for RBAC filtering
        access_tags: Access tags for RBAC filtering
        **kwargs: Additional config options

    Returns:
        RetrievalConfig instance
    """
    return RetrievalConfig(
        top_k=top_k,
        min_score=min_score,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        folder_paths=folder_paths,
        access_tags=access_tags,
        **kwargs,
    )

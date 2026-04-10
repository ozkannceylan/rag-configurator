"""Observability utilities (tracing, Langfuse, OpenTelemetry metrics).

All integrations degrade gracefully when their optional dependencies are not
installed.
"""

from rag_config_common.observability.tracing import setup_tracing
from rag_config_common.observability.langfuse import setup_langfuse
from rag_config_common.observability.metrics import (
    record_query_duration,
    record_retrieval_duration,
    record_llm_tokens,
    record_error,
    record_cache_hit,
    record_evaluation_score,
)

__all__ = [
    "setup_tracing",
    "setup_langfuse",
    "record_query_duration",
    "record_retrieval_duration",
    "record_llm_tokens",
    "record_error",
    "record_cache_hit",
    "record_evaluation_score",
]

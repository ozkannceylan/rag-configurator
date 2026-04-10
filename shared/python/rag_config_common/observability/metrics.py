"""OpenTelemetry metrics for RAG pipeline observability.

Exposes convenience functions that record custom metrics.  When the
``opentelemetry`` SDK is not installed every function silently no-ops so
callers never need to guard with ``try/except ImportError``.

Metrics defined:
  - ``rag_query_duration_seconds``      (histogram)
  - ``rag_retrieval_duration_seconds``  (histogram)
  - ``rag_llm_tokens_total``           (counter, labels: provider, type)
  - ``rag_errors_total``               (counter, labels: service, error_type)
  - ``rag_cache_hits_total``           (counter, labels: cache_type)
  - ``rag_evaluation_score``           (histogram, labels: metric_name)
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Attempt to import OTel.  All public functions below are safe no-ops when
# the SDK is missing.
# ---------------------------------------------------------------------------

_otel_available = False
_meter = None  # type: ignore

_query_duration = None
_retrieval_duration = None
_llm_tokens = None
_errors = None
_cache_hits = None
_evaluation_score = None

try:
    from opentelemetry import metrics as otel_metrics

    _otel_available = True
except ImportError:
    pass


def _ensure_instruments() -> None:
    """Lazily create OTel instruments on first use."""
    global _meter, _query_duration, _retrieval_duration  # noqa: PLW0603
    global _llm_tokens, _errors, _cache_hits, _evaluation_score  # noqa: PLW0603

    if not _otel_available or _meter is not None:
        return

    _meter = otel_metrics.get_meter("rag-configurator", "0.1.0")

    _query_duration = _meter.create_histogram(
        name="rag_query_duration_seconds",
        description="End-to-end RAG query latency in seconds",
        unit="s",
    )
    _retrieval_duration = _meter.create_histogram(
        name="rag_retrieval_duration_seconds",
        description="Retrieval step latency in seconds",
        unit="s",
    )
    _llm_tokens = _meter.create_counter(
        name="rag_llm_tokens_total",
        description="Total LLM tokens consumed",
        unit="tokens",
    )
    _errors = _meter.create_counter(
        name="rag_errors_total",
        description="Total error count",
    )
    _cache_hits = _meter.create_counter(
        name="rag_cache_hits_total",
        description="Total cache hit count",
    )
    _evaluation_score = _meter.create_histogram(
        name="rag_evaluation_score",
        description="Evaluation metric scores (0-1)",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_query_duration(duration_seconds: float) -> None:
    """Record the duration of a complete RAG query."""
    if not _otel_available:
        return
    _ensure_instruments()
    if _query_duration is not None:
        _query_duration.record(duration_seconds)


def record_retrieval_duration(duration_seconds: float) -> None:
    """Record the duration of a retrieval step."""
    if not _otel_available:
        return
    _ensure_instruments()
    if _retrieval_duration is not None:
        _retrieval_duration.record(duration_seconds)


def record_llm_tokens(
    count: int,
    provider: str = "unknown",
    token_type: str = "prompt",
) -> None:
    """Record LLM token usage.

    Args:
        count: Number of tokens.
        provider: LLM provider name (openai, anthropic, ...).
        token_type: ``"prompt"`` or ``"completion"``.
    """
    if not _otel_available:
        return
    _ensure_instruments()
    if _llm_tokens is not None:
        _llm_tokens.add(count, {"provider": provider, "type": token_type})


def record_error(
    service: str = "unknown",
    error_type: str = "unknown",
) -> None:
    """Increment the error counter."""
    if not _otel_available:
        return
    _ensure_instruments()
    if _errors is not None:
        _errors.add(1, {"service": service, "error_type": error_type})


def record_cache_hit(cache_type: str = "unknown") -> None:
    """Increment the cache-hit counter."""
    if not _otel_available:
        return
    _ensure_instruments()
    if _cache_hits is not None:
        _cache_hits.add(1, {"cache_type": cache_type})


def record_evaluation_score(
    score: float,
    metric_name: str = "unknown",
) -> None:
    """Record an evaluation metric score."""
    if not _otel_available:
        return
    _ensure_instruments()
    if _evaluation_score is not None:
        _evaluation_score.record(score, {"metric_name": metric_name})

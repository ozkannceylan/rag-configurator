"""TypeSafe Jev (System One) judge for frozen RAG traces.

Jev is not an autoregressive LLM. It evaluates typed questions against
structured state and returns typed answers (Score / Noul / Choice).

Transport: HTTP ``POST {base_url}/v1/systemone`` via httpx (already a service
dependency). The official ``typesafe-sdk`` package is optional and is used
when installed *and* ``use_sdk=True``.

Auth: ``TYPESAFE_API_KEY`` as ``Authorization: Bearer``. Never log the key.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.evaluation.base import BaseEvaluator
from app.evaluation.models import EvaluationResult, MetricResult
from app.evaluation.rubric import (
    DOES_PASS_CRITERIA,
    DOES_PASS_INSTRUCTIONS,
    GROUNDED_INSTRUCTIONS,
    QUALITY_INSTRUCTIONS,
    QUALITY_SCORE_CRITERIA,
    build_judge_state,
    quality_01,
)
from app.evaluation.verdict import JudgeVerdict

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.typesafe.ai"
DEFAULT_MODEL = "jev-latest"
SYSTEMONE_PATH = "/v1/systemone"

# Cost proxy from the LangChain Jev-as-a-Judge experiment (~$0.00035/call).
# TypeSafe bills input tokens; output tokens are reported but not billed.
# $0.35 / 1M input tokens ≈ $0.00035 at ~1k tokens. Override via env.
DEFAULT_JEV_USD_PER_MILLION_INPUT = 0.35
DEFAULT_JEV_FALLBACK_USD_PER_CALL = 0.00035

# Async callable: (payload: dict) -> dict
SystemOneCaller = Callable[[dict[str, Any]], Any]


def default_jev_questions() -> dict[str, Any]:
    """Score (quality 1–5) + Noul (does_pass, grounded) in one parallel call."""
    return {
        "quality": {
            "type": "score",
            "instructions": QUALITY_INSTRUCTIONS,
            "criteria": list(QUALITY_SCORE_CRITERIA),
        },
        "does_pass": {
            "type": "noul",
            "instructions": DOES_PASS_INSTRUCTIONS,
            "criteria": dict(DOES_PASS_CRITERIA),
        },
        "grounded": {
            "type": "noul",
            "instructions": GROUNDED_INSTRUCTIONS,
        },
    }


def score_to_quality_1_5(score: float, n_levels: int = 5) -> float:
    """Convert a TypeSafe Score onto a 1–5 quality scale.

    TypeSafe Score is 0-indexed over ``n_levels`` criteria (legend keys
    ``"0"`` .. ``"n-1"``). A 5-level score of ``4`` maps to quality ``5``.
    """
    value = float(score)
    if n_levels <= 1:
        return 1.0
    max_index = float(n_levels - 1)
    clamped = max(0.0, min(max_index, value))
    return 1.0 + (clamped / max_index) * 4.0


def estimate_jev_cost_usd(
    usage: dict[str, Any] | None,
    usd_per_million_input: float = DEFAULT_JEV_USD_PER_MILLION_INPUT,
    fallback_per_call: float = DEFAULT_JEV_FALLBACK_USD_PER_CALL,
) -> float:
    """USD cost proxy. Input tokens billed; fallback is the published per-call figure."""
    if not usage:
        return fallback_per_call
    input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
    try:
        tokens = float(input_tokens)
    except (TypeError, ValueError):
        return fallback_per_call
    if tokens <= 0:
        return fallback_per_call
    return tokens / 1_000_000.0 * usd_per_million_input


def parse_system_one_response(
    payload: dict[str, Any],
    *,
    latency_ms: float = 0.0,
    cost_usd: float | None = None,
    n_levels: int = 5,
) -> JudgeVerdict:
    """Parse a ``/v1/systemone`` JSON body into a :class:`JudgeVerdict`."""
    answers = payload.get("answers") or {}
    usage = payload.get("usage") or {}
    model = str(payload.get("model") or DEFAULT_MODEL).strip()

    quality_answer = answers.get("quality") or {}
    raw_score = quality_answer.get("score", 0.0)
    try:
        quality = score_to_quality_1_5(float(raw_score), n_levels=n_levels)
    except (TypeError, ValueError):
        quality = 1.0

    pass_answer = answers.get("does_pass") or {}
    try:
        pass_prob = float(pass_answer.get("noul", 0.0))
    except (TypeError, ValueError):
        pass_prob = 0.0
    pass_prob = max(0.0, min(1.0, pass_prob))

    grounded_answer = answers.get("grounded") or {}
    try:
        grounded = float(grounded_answer.get("noul", 0.0))
    except (TypeError, ValueError):
        grounded = 0.0
    grounded = max(0.0, min(1.0, grounded))

    if cost_usd is None:
        cost_usd = estimate_jev_cost_usd(usage)

    return JudgeVerdict(
        judge="jev",
        quality=quality,
        does_pass=pass_prob >= 0.5,
        does_pass_probability=pass_prob,
        groundedness=grounded,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        model=model,
        explanation=(
            f"quality_score={raw_score}, "
            f"does_pass_noul={pass_prob:.3f}, "
            f"grounded_noul={grounded:.3f}"
        ),
        raw=payload,
    )


class JevClient:
    """Thin async client for TypeSafe System One."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
        request_fn: SystemOneCaller | None = None,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.environ.get("TYPESAFE_API_KEY")
        )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._http_client = http_client
        self._request_fn = request_fn
        self._owns_client = False

    async def system_one(
        self, state: dict[str, Any], questions: dict[str, Any]
    ) -> dict[str, Any]:
        payload = {"model": self.model, "state": state, "questions": questions}
        if self._request_fn is not None:
            result = self._request_fn(payload)
            if hasattr(result, "__await__"):
                return await result
            return result
        return await self._http_system_one(payload)

    async def _http_system_one(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError(
                "TYPESAFE_API_KEY is not set. Export the key or run the compare "
                "harness with --mock."
            )
        client = self._http_client
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout_seconds)
            self._http_client = client
            self._owns_client = True
        url = f"{self.base_url}{SYSTEMONE_PATH}"
        response = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Jev System One error {response.status_code}: {response.text[:400]}"
            )
        return response.json()

    async def aclose(self) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            self._owns_client = False


class JevJudge(BaseEvaluator):
    """Evaluate a RAG trace with Jev Score + Noul questions in one call."""

    def __init__(
        self,
        *,
        client: JevClient | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        usd_per_million_input: float = DEFAULT_JEV_USD_PER_MILLION_INPUT,
        fallback_usd_per_call: float = DEFAULT_JEV_FALLBACK_USD_PER_CALL,
        pass_threshold: float = 0.5,
    ) -> None:
        self.client = client or JevClient(
            api_key=api_key,
            base_url=base_url or os.environ.get("TYPESAFE_BASE_URL", DEFAULT_BASE_URL),
            model=model or os.environ.get("TYPESAFE_MODEL", DEFAULT_MODEL),
        )
        self.usd_per_million_input = usd_per_million_input
        self.fallback_usd_per_call = fallback_usd_per_call
        self.pass_threshold = pass_threshold
        self.questions = default_jev_questions()

    async def judge_trace(
        self,
        question: str,
        retrieved_chunks: list[str],
        answer: str,
    ) -> JudgeVerdict:
        state = build_judge_state(question, retrieved_chunks, answer)
        started = time.perf_counter()
        try:
            payload = await self.client.system_one(state, self.questions)
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            logger.exception("Jev judge call failed: %s", exc)
            return JudgeVerdict(
                judge="jev",
                quality=1.0,
                does_pass=False,
                groundedness=0.0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                model=self.client.model,
                does_pass_probability=0.0,
                explanation=f"Jev error: {exc}",
                error=str(exc),
            )
        latency_ms = (time.perf_counter() - started) * 1000.0
        usage = payload.get("usage") if isinstance(payload, dict) else None
        cost = estimate_jev_cost_usd(
            usage,
            usd_per_million_input=self.usd_per_million_input,
            fallback_per_call=self.fallback_usd_per_call,
        )
        verdict = parse_system_one_response(
            payload,
            latency_ms=latency_ms,
            cost_usd=cost,
            n_levels=len(QUALITY_SCORE_CRITERIA),
        )
        verdict.does_pass = verdict.does_pass_probability >= self.pass_threshold
        return verdict

    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> EvaluationResult:
        del ground_truth  # Jev judges the produced answer against retrieved chunks.
        verdict = await self.judge_trace(query, contexts, answer)
        quality_score = quality_01(verdict.quality)
        pass_score = 1.0 if verdict.does_pass else 0.0
        metric_results = [
            MetricResult(
                name="quality",
                score=quality_score,
                explanation=verdict.explanation,
            ),
            MetricResult(
                name="does_pass",
                score=pass_score,
                explanation=f"noul={verdict.does_pass_probability:.3f}",
            ),
            MetricResult(
                name="groundedness",
                score=verdict.groundedness,
                explanation="Jev Noul P(grounded)",
            ),
        ]
        return EvaluationResult(
            scores={m.name: m.score for m in metric_results},
            metric_results=metric_results,
            metadata={
                "evaluator": "jev",
                "model": verdict.model,
                "quality_1_5": verdict.quality,
                "latency_ms": verdict.latency_ms,
                "cost_usd": verdict.cost_usd,
                "error": verdict.error,
            },
        )

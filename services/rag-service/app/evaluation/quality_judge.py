"""LLM-as-judge baseline with a 1–5 quality Score and boolean does_pass.

Uses the same state JSON and rubric as the Jev judge. Parsing is deterministic:
JSON only, markdown fences stripped, values clamped.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from app.evaluation.base import BaseEvaluator
from app.evaluation.models import EvaluationResult, MetricResult
from app.evaluation.rubric import build_judge_state, llm_judge_prompt, quality_01
from app.evaluation.verdict import JudgeVerdict
from app.llm.base import BaseLLM, Message

logger = logging.getLogger(__name__)

# Published-ish USD / 1M tokens. Proxies for compare reports, not invoices.
DEFAULT_LLM_PRICING = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
}
DEFAULT_INPUT_USD_PER_MILLION = 0.15
DEFAULT_OUTPUT_USD_PER_MILLION = 0.60


def estimate_llm_cost_usd(
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> float:
    """USD cost proxy from token usage and a small price table."""
    key = (model or "").strip().lower()
    input_rate, output_rate = DEFAULT_LLM_PRICING.get(
        key, (DEFAULT_INPUT_USD_PER_MILLION, DEFAULT_OUTPUT_USD_PER_MILLION)
    )
    for name, rates in DEFAULT_LLM_PRICING.items():
        if name in key:
            input_rate, output_rate = rates
            break
    return (
        prompt_tokens / 1_000_000.0 * input_rate
        + completion_tokens / 1_000_000.0 * output_rate
    )


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return float(value) >= 0.5
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "pass", "1"}
    return False


def parse_quality_judge_response(raw: str) -> dict[str, Any]:
    """Parse LLM JSON into quality (1–5), does_pass, groundedness, explanation."""
    text = _strip_fences(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {
                "quality": 1.0,
                "does_pass": False,
                "groundedness": 0.0,
                "explanation": f"Parse error: not JSON: {raw[:200]}",
                "error": "json_decode",
            }
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            return {
                "quality": 1.0,
                "does_pass": False,
                "groundedness": 0.0,
                "explanation": f"Parse error: {exc}",
                "error": "json_decode",
            }
    try:
        quality = float(data.get("quality", 1.0))
    except (TypeError, ValueError):
        quality = 1.0
    quality = max(1.0, min(5.0, quality))
    try:
        groundedness = float(data.get("groundedness", 0.0))
    except (TypeError, ValueError):
        groundedness = 0.0
    groundedness = max(0.0, min(1.0, groundedness))
    does_pass = _coerce_bool(data.get("does_pass", False))
    explanation = str(data.get("explanation", ""))
    return {
        "quality": quality,
        "does_pass": does_pass,
        "groundedness": groundedness,
        "explanation": explanation,
        "error": None,
    }


class QualityJudge(BaseEvaluator):
    """LLM judge that emits Score-like 1–5 quality plus a boolean pass flag."""

    def __init__(
        self,
        llm: BaseLLM,
        *,
        judge_name: str = "llm",
        temperature: float = 0.0,
        max_tokens: int = 256,
    ) -> None:
        self.llm = llm
        self.judge_name = judge_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def judge_trace(
        self,
        question: str,
        retrieved_chunks: list[str],
        answer: str,
    ) -> JudgeVerdict:
        state = build_judge_state(question, retrieved_chunks, answer)
        prompt = llm_judge_prompt(state)
        started = time.perf_counter()
        try:
            response = await self.llm.generate(
                messages=[Message.user(prompt)],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            logger.exception("LLM quality judge failed: %s", exc)
            return JudgeVerdict(
                judge=self.judge_name,
                quality=1.0,
                does_pass=False,
                groundedness=0.0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                model=self.llm.model,
                does_pass_probability=0.0,
                explanation=f"LLM judge error: {exc}",
                error=str(exc),
            )
        latency_ms = (time.perf_counter() - started) * 1000.0
        parsed = parse_quality_judge_response(response.content)
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        cost = estimate_llm_cost_usd(response.model, prompt_tokens, completion_tokens)
        does_pass = bool(parsed["does_pass"])
        return JudgeVerdict(
            judge=self.judge_name,
            quality=float(parsed["quality"]),
            does_pass=does_pass,
            groundedness=float(parsed["groundedness"]),
            latency_ms=latency_ms,
            cost_usd=cost,
            model=response.model or self.llm.model,
            does_pass_probability=1.0 if does_pass else 0.0,
            explanation=str(parsed["explanation"]),
            raw={"content": response.content, "parsed": parsed},
            error=parsed.get("error"),
        )

    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> EvaluationResult:
        del ground_truth
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
                explanation=verdict.explanation,
            ),
            MetricResult(
                name="groundedness",
                score=verdict.groundedness,
                explanation=verdict.explanation,
            ),
        ]
        return EvaluationResult(
            scores={m.name: m.score for m in metric_results},
            metric_results=metric_results,
            metadata={
                "evaluator": self.judge_name,
                "llm_model": verdict.model,
                "quality_1_5": verdict.quality,
                "latency_ms": verdict.latency_ms,
                "cost_usd": verdict.cost_usd,
                "error": verdict.error,
            },
        )

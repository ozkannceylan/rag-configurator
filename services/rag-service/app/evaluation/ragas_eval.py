"""RAGAS-style evaluation using LLM-based metric calculations.

Implements four core RAGAS metrics without requiring the ragas library:
  - faithfulness: Are answer claims supported by the context?
  - answer_relevancy: Does the answer address the query?
  - context_precision: Are retrieved contexts relevant to the query?
  - context_recall: Do contexts cover the ground truth information?

Each metric uses a structured LLM prompt to produce a 0-1 score.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.evaluation.base import BaseEvaluator
from app.evaluation.models import EvaluationResult, MetricResult
from app.llm.base import BaseLLM, Message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

FAITHFULNESS_PROMPT = """\
You are an expert evaluator. Given the following CONTEXT and ANSWER, determine how \
faithful the answer is to the provided context.

A faithful answer only makes claims that are supported by the context. Penalise \
fabricated or unsupported statements.

CONTEXT:
{context}

ANSWER:
{answer}

Score the faithfulness from 0.0 to 1.0 where:
- 1.0 = every claim in the answer is fully supported by the context
- 0.0 = the answer is entirely unsupported or contradicts the context

Respond ONLY with valid JSON in this format (no markdown):
{{"score": <float>, "explanation": "<brief explanation>"}}
"""

ANSWER_RELEVANCY_PROMPT = """\
You are an expert evaluator. Given the following QUERY and ANSWER, determine how \
relevant the answer is to the query.

QUERY:
{query}

ANSWER:
{answer}

Score the relevancy from 0.0 to 1.0 where:
- 1.0 = the answer directly and completely addresses the query
- 0.0 = the answer is completely unrelated to the query

Respond ONLY with valid JSON in this format (no markdown):
{{"score": <float>, "explanation": "<brief explanation>"}}
"""

CONTEXT_PRECISION_PROMPT = """\
You are an expert evaluator. Given the following QUERY and CONTEXTS, determine how \
precise the retrieved contexts are. Precision measures the proportion of retrieved \
contexts that are actually relevant to the query.

QUERY:
{query}

CONTEXTS:
{contexts}

Score the context precision from 0.0 to 1.0 where:
- 1.0 = every retrieved context is highly relevant to the query
- 0.0 = none of the retrieved contexts are relevant

Respond ONLY with valid JSON in this format (no markdown):
{{"score": <float>, "explanation": "<brief explanation>"}}
"""

CONTEXT_RECALL_PROMPT = """\
You are an expert evaluator. Given the following GROUND TRUTH and CONTEXTS, determine \
how well the retrieved contexts cover the information in the ground truth.

GROUND TRUTH:
{ground_truth}

CONTEXTS:
{contexts}

Score the context recall from 0.0 to 1.0 where:
- 1.0 = the contexts contain all information needed to produce the ground truth answer
- 0.0 = the contexts contain none of the information from the ground truth

Respond ONLY with valid JSON in this format (no markdown):
{{"score": <float>, "explanation": "<brief explanation>"}}
"""

# All available metric names
AVAILABLE_METRICS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]


def _parse_score_response(raw: str) -> Dict[str, Any]:
    """Parse the JSON score response from the LLM, tolerating markdown fences."""
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        score = float(data.get("score", 0.0))
        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))
        return {
            "score": score,
            "explanation": str(data.get("explanation", "")),
        }
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse LLM score response: %s – raw: %s", exc, raw[:200])
        return {"score": 0.0, "explanation": f"Parse error: {exc}"}


class RagasEvaluator(BaseEvaluator):
    """Evaluate RAG outputs using RAGAS-style LLM-based metrics.

    Args:
        llm: A ``BaseLLM`` instance used to score each metric.
        metrics: Which metrics to compute.  Defaults to all four.
    """

    def __init__(
        self,
        llm: BaseLLM,
        metrics: Optional[List[str]] = None,
    ) -> None:
        self.llm = llm
        self.metrics = metrics or list(AVAILABLE_METRICS)
        # Validate requested metrics
        for m in self.metrics:
            if m not in AVAILABLE_METRICS:
                raise ValueError(
                    f"Unknown metric '{m}'. Available: {AVAILABLE_METRICS}"
                )

    # ------------------------------------------------------------------
    # Individual metric helpers
    # ------------------------------------------------------------------

    async def _score_faithfulness(
        self, answer: str, contexts: List[str]
    ) -> MetricResult:
        combined_context = "\n\n---\n\n".join(contexts) if contexts else "(no context provided)"
        prompt = FAITHFULNESS_PROMPT.format(context=combined_context, answer=answer)
        response = await self.llm.generate(
            messages=[Message.user(prompt)],
            temperature=0.0,
            max_tokens=256,
        )
        parsed = _parse_score_response(response.content)
        return MetricResult(
            name="faithfulness",
            score=parsed["score"],
            explanation=parsed["explanation"],
        )

    async def _score_answer_relevancy(
        self, query: str, answer: str
    ) -> MetricResult:
        prompt = ANSWER_RELEVANCY_PROMPT.format(query=query, answer=answer)
        response = await self.llm.generate(
            messages=[Message.user(prompt)],
            temperature=0.0,
            max_tokens=256,
        )
        parsed = _parse_score_response(response.content)
        return MetricResult(
            name="answer_relevancy",
            score=parsed["score"],
            explanation=parsed["explanation"],
        )

    async def _score_context_precision(
        self, query: str, contexts: List[str]
    ) -> MetricResult:
        numbered = "\n".join(
            f"[{i+1}] {c}" for i, c in enumerate(contexts)
        ) if contexts else "(no contexts)"
        prompt = CONTEXT_PRECISION_PROMPT.format(query=query, contexts=numbered)
        response = await self.llm.generate(
            messages=[Message.user(prompt)],
            temperature=0.0,
            max_tokens=256,
        )
        parsed = _parse_score_response(response.content)
        return MetricResult(
            name="context_precision",
            score=parsed["score"],
            explanation=parsed["explanation"],
        )

    async def _score_context_recall(
        self, ground_truth: str, contexts: List[str]
    ) -> MetricResult:
        numbered = "\n".join(
            f"[{i+1}] {c}" for i, c in enumerate(contexts)
        ) if contexts else "(no contexts)"
        prompt = CONTEXT_RECALL_PROMPT.format(
            ground_truth=ground_truth, contexts=numbered
        )
        response = await self.llm.generate(
            messages=[Message.user(prompt)],
            temperature=0.0,
            max_tokens=256,
        )
        parsed = _parse_score_response(response.content)
        return MetricResult(
            name="context_recall",
            score=parsed["score"],
            explanation=parsed["explanation"],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> EvaluationResult:
        """Run the requested RAGAS metrics and return an ``EvaluationResult``."""
        metric_results: List[MetricResult] = []

        for metric_name in self.metrics:
            try:
                if metric_name == "faithfulness":
                    result = await self._score_faithfulness(answer, contexts)
                elif metric_name == "answer_relevancy":
                    result = await self._score_answer_relevancy(query, answer)
                elif metric_name == "context_precision":
                    result = await self._score_context_precision(query, contexts)
                elif metric_name == "context_recall":
                    if ground_truth is None:
                        result = MetricResult(
                            name="context_recall",
                            score=0.0,
                            explanation="Skipped: no ground truth provided.",
                        )
                    else:
                        result = await self._score_context_recall(ground_truth, contexts)
                else:
                    continue  # unreachable due to __init__ validation
                metric_results.append(result)
            except Exception as exc:
                logger.error("Metric '%s' failed: %s", metric_name, exc)
                metric_results.append(
                    MetricResult(
                        name=metric_name,
                        score=0.0,
                        explanation=f"Evaluation error: {exc}",
                    )
                )

        scores = {r.name: r.score for r in metric_results}

        return EvaluationResult(
            scores=scores,
            metric_results=metric_results,
            metadata={
                "evaluator": "ragas",
                "llm_model": self.llm.model,
                "metrics_requested": self.metrics,
            },
        )

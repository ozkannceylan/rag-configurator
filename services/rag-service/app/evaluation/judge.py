"""LLM-as-Judge evaluator with configurable rubrics.

Uses a (possibly different) LLM to score RAG answers against customisable
rubrics.  Default rubrics cover relevance, completeness, conciseness, and
accuracy.
"""

import json
import logging
import re

from app.evaluation.base import BaseEvaluator
from app.evaluation.models import EvaluationResult, MetricResult
from app.llm.base import BaseLLM, Message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default rubric definitions
# ---------------------------------------------------------------------------

DEFAULT_RUBRICS: dict[str, dict[str, str]] = {
    "relevance": {
        "description": "How relevant is the answer to the user's query?",
        "criteria": (
            "1.0 = directly answers the query with appropriate detail; "
            "0.5 = partially relevant but misses key aspects; "
            "0.0 = completely off-topic"
        ),
    },
    "completeness": {
        "description": "How completely does the answer address all aspects of the query?",
        "criteria": (
            "1.0 = covers every aspect of the query thoroughly; "
            "0.5 = addresses some aspects but omits important ones; "
            "0.0 = fails to address the query at all"
        ),
    },
    "conciseness": {
        "description": "Is the answer concise without unnecessary information?",
        "criteria": (
            "1.0 = every sentence adds value, no fluff; "
            "0.5 = some unnecessary padding or repetition; "
            "0.0 = extremely verbose or mostly irrelevant filler"
        ),
    },
    "accuracy": {
        "description": "How accurate is the answer relative to the provided context?",
        "criteria": (
            "1.0 = all claims are accurate and supported by context; "
            "0.5 = mostly accurate but contains minor errors; "
            "0.0 = contains significant factual errors or fabrications"
        ),
    },
}

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

JUDGE_PROMPT = """\
You are an expert judge evaluating the quality of an AI-generated answer.

QUERY:
{query}

ANSWER:
{answer}

CONTEXTS (used by the AI to generate the answer):
{contexts}

{ground_truth_section}

Evaluate the answer on the following rubrics. For each rubric, provide a score \
from 0.0 to 1.0 and a brief explanation.

RUBRICS:
{rubrics_text}

Respond ONLY with valid JSON in this format (no markdown):
{{
  "rubrics": [
    {{"name": "<rubric_name>", "score": <float>, "explanation": "<brief explanation>"}},
    ...
  ]
}}
"""


def _parse_judge_response(raw: str, rubric_names: list[str]) -> list[MetricResult]:
    """Parse the structured JSON from the judge LLM."""
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        results: list[MetricResult] = []
        rubric_items = data.get("rubrics", [])
        seen_names = set()
        for item in rubric_items:
            name = str(item.get("name", "unknown"))
            score = float(item.get("score", 0.0))
            score = max(0.0, min(1.0, score))
            explanation = str(item.get("explanation", ""))
            results.append(
                MetricResult(name=name, score=score, explanation=explanation)
            )
            seen_names.add(name)
        # Fill any rubrics the LLM missed
        for rn in rubric_names:
            if rn not in seen_names:
                results.append(
                    MetricResult(name=rn, score=0.0, explanation="Not scored by judge.")
                )
        return results
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse judge response: %s – raw: %s", exc, raw[:300])
        return [
            MetricResult(name=rn, score=0.0, explanation=f"Parse error: {exc}")
            for rn in rubric_names
        ]


class JudgeEvaluator(BaseEvaluator):
    """Evaluate RAG outputs using an LLM judge with rubric-based scoring.

    Args:
        llm: A ``BaseLLM`` instance used as the judge.  This can be a different
            model from the one that generated the answer.
        rubrics: Mapping of rubric name -> ``{"description": ..., "criteria": ...}``.
            Defaults to relevance, completeness, conciseness, accuracy.
    """

    def __init__(
        self,
        llm: BaseLLM,
        rubrics: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self.llm = llm
        self.rubrics = rubrics or dict(DEFAULT_RUBRICS)

    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> EvaluationResult:
        """Run the judge evaluation and return an ``EvaluationResult``."""
        # Build rubrics text
        rubric_lines = []
        rubric_names = []
        for name, rubric in self.rubrics.items():
            rubric_lines.append(
                f"- {name}: {rubric['description']}\n  Scoring: {rubric['criteria']}"
            )
            rubric_names.append(name)
        rubrics_text = "\n".join(rubric_lines)

        # Build context text
        contexts_text = (
            "\n\n---\n\n".join(contexts) if contexts else "(no context provided)"
        )

        # Ground truth section
        ground_truth_section = ""
        if ground_truth:
            ground_truth_section = f"GROUND TRUTH (expected answer):\n{ground_truth}\n"

        prompt = JUDGE_PROMPT.format(
            query=query,
            answer=answer,
            contexts=contexts_text,
            ground_truth_section=ground_truth_section,
            rubrics_text=rubrics_text,
        )

        try:
            response = await self.llm.generate(
                messages=[Message.user(prompt)],
                temperature=0.0,
                max_tokens=1024,
            )
            metric_results = _parse_judge_response(response.content, rubric_names)
        except Exception as exc:
            logger.error("Judge evaluation failed: %s", exc)
            metric_results = [
                MetricResult(name=rn, score=0.0, explanation=f"Judge error: {exc}")
                for rn in rubric_names
            ]

        scores = {r.name: r.score for r in metric_results}

        return EvaluationResult(
            scores=scores,
            metric_results=metric_results,
            metadata={
                "evaluator": "judge",
                "llm_model": self.llm.model,
                "rubrics": list(self.rubrics.keys()),
            },
        )

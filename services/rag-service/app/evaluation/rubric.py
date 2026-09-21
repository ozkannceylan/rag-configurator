"""Shared quality rubric used by both the Jev and LLM judges.

The rubric is intentionally small and decision-oriented: a 1–5 quality Score
plus a binary pass/fail groundedness check. It is *not* a safety/ASIL claim.
"""

from __future__ import annotations

import json
from typing import Any

# Ordered Score levels. TypeSafe Score is 0-indexed over this list.
QUALITY_SCORE_CRITERIA: list[str] = [
    "Unhelpful or contradicts the retrieved evidence; mostly unsupported.",
    "Partially relevant but incomplete or weakly grounded in the chunks.",
    "Adequate: addresses the question with some support from retrieved chunks.",
    "Good: grounded, relevant, and mostly complete given the evidence.",
    "Excellent: fully grounded in retrieved evidence, complete, and useful.",
]

QUALITY_INSTRUCTIONS = (
    "Rate the RAG answer quality given `question`, `retrieved_chunks`, and "
    "`answer`. Use only the retrieved chunks as evidence. Penalize claims that "
    "are not supported by those chunks."
)

DOES_PASS_INSTRUCTIONS = (
    "Does this RAG answer pass? Pass only if it is grounded in "
    "`retrieved_chunks` and adequately addresses `question` without material "
    "hallucination. Fail if it is off-topic, contradicts the chunks, or invents "
    "important facts."
)

DOES_PASS_CRITERIA: dict[str, str] = {
    "true": "Grounded in retrieved chunks and adequately answers the question.",
    "false": "Hallucinated, off-topic, or not supported by retrieved chunks.",
}

GROUNDED_INSTRUCTIONS = (
    "Are the factual claims in `answer` supported by `retrieved_chunks`? "
    "Ignore style. Return the probability that the answer is grounded."
)

LLM_JUDGE_PROMPT = """\
You are scoring a fixed Naive RAG trace. Use ONLY the retrieved chunks as evidence.
Do not reward fluency if the answer is ungrounded.

Rubric for `quality` (integer 1-5):
1. {c0}
2. {c1}
3. {c2}
4. {c3}
5. {c4}

`does_pass` is true only if the answer is grounded in the chunks AND adequately
addresses the question without material hallucination.

`groundedness` is a float from 0.0 to 1.0: probability the answer's claims are
supported by the chunks.

STATE JSON:
{state}

Respond ONLY with valid JSON (no markdown):
{{"quality": <int 1-5>, "does_pass": <true|false>, "groundedness": <float 0-1>, "explanation": "<brief>"}}
"""


def build_judge_state(
    question: str,
    retrieved_chunks: list[str],
    answer: str,
) -> dict[str, Any]:
    """Canonical state JSON sent to both judges."""
    return {
        "question": question,
        "retrieved_chunks": list(retrieved_chunks),
        "answer": answer,
    }


def llm_judge_prompt(state: dict[str, Any]) -> str:
    """Prompt for the LLM-as-judge baseline. Same rubric as the Jev Score/Noul."""
    criteria = QUALITY_SCORE_CRITERIA
    return LLM_JUDGE_PROMPT.format(
        c0=criteria[0],
        c1=criteria[1],
        c2=criteria[2],
        c3=criteria[3],
        c4=criteria[4],
        state=json.dumps(state, ensure_ascii=False, indent=2),
    )


def quality_01(quality_1_5: float) -> float:
    """Map a 1–5 quality score onto [0, 1] for EvaluationResult."""
    clamped = max(1.0, min(5.0, float(quality_1_5)))
    return (clamped - 1.0) / 4.0

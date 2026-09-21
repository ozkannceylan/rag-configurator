"""Shared quality rubric used by both the Jev and LLM judges.

The rubric is intentionally small and decision-oriented: a 1–5 quality Score
plus a binary pass/fail groundedness check. It is *not* a safety/ASIL claim.
"""

from __future__ import annotations

import json
from typing import Any

# The rubric separates two failure modes that an earlier version conflated:
#   - INCOMPLETENESS: the answer omits part of what was asked, but every claim
#     it does make is supported by the chunks. The reader is under-served.
#   - CONTRADICTION: the answer asserts something the chunks refute, or invents
#     a specific fact. The reader is actively misled.
#
# These are not the same severity and must not share a band. A confidently
# wrong dollar amount is worse than a missing one, because the reader acts on
# it. CONTRADICTION_CAP encodes that as an explicit precedence rule rather than
# leaving each judge to guess, which is what produced a 1.39 / 2.0 / 3.0 spread
# between Jev, the LLM baseline and the human label on the same trace.
CONTRADICTION_CAP = 2

# Ordered Score levels. TypeSafe Score is 0-indexed over this list.
QUALITY_SCORE_CRITERIA: list[str] = [
    "Useless or actively misleading: the central claim contradicts the chunks, "
    "or the answer is fabricated with no support at all.",
    "Materially wrong: at least one specific claim (a number, amount, name, "
    "date, or condition) contradicts the chunks or is invented, even if other "
    "parts of the answer are correctly grounded.",
    "Grounded but incomplete: every claim made is supported by the chunks, but "
    "part of the question is left unanswered.",
    "Good: grounded and essentially complete, with only minor omissions.",
    "Excellent: fully grounded in the chunks, complete, and directly useful.",
]

QUALITY_INSTRUCTIONS = (
    "Rate the RAG answer quality given `question`, `retrieved_chunks`, and "
    "`answer`. Use only the retrieved chunks as evidence; ignore anything you "
    "know from outside them, and do not reward fluency. "
    "Apply this precedence rule before choosing a level: if any specific claim "
    "in the answer contradicts the chunks or is invented, the score cannot "
    f"exceed {CONTRADICTION_CAP}, no matter how much of the rest is correct. "
    "Only answers whose every claim is supported may score above "
    f"{CONTRADICTION_CAP}, and among those the level is set by how completely "
    "they address the question."
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

PRECEDENCE RULE. Decide grounding before completeness. If any specific claim in
the answer contradicts the chunks or is invented, `quality` must not exceed
{cap}, however much of the rest is correct. Only an answer whose every claim is
supported may score above {cap}; among those, the level is set by how completely
it addresses the question.

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
        cap=CONTRADICTION_CAP,
        state=json.dumps(state, ensure_ascii=False, indent=2),
    )


def quality_01(quality_1_5: float) -> float:
    """Map a 1–5 quality score onto [0, 1] for EvaluationResult."""
    clamped = max(1.0, min(5.0, float(quality_1_5)))
    return (clamped - 1.0) / 4.0

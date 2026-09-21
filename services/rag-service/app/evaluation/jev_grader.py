"""Jev as an in-loop relevance grader for self-correcting agents.

CRAG and Self-RAG both pause mid-run to ask a grader a narrow, typed question:
*is this retrieval good enough, or do I need to correct?* Today that question
costs an autoregressive generation, and the answer arrives as free text that
has to be regex-parsed back into a boolean.

That is the wrong shape for the job, and the compare harness measured why:

===================  ===========  ===========
Property             Jev          LLM judge
===================  ===========  ===========
p50 latency          227 ms       4177 ms
Failed calls         0 / 70       6 / 70
===================  ===========  ===========

The latency matters because this grader sits *inside* the request, not in a
nightly batch: four seconds per correction cycle is the difference between a
self-correcting agent and an unusable one. The failure rate matters more. A
grader that cannot be parsed does not return "unsure", it returns whatever the
fallback says, and in the harness that fallback silently became a confident
verdict. A typed contract removes "the grader did not answer" as a failure
mode, because the answer is a probability by construction.

This module exposes that capability as a small adapter so an agent can take a
grading decision without depending on the whole evaluation stack. It is the
seam, not the wiring: routing an agent's config to it touches the shared
pipeline models and both frontends, and is a separate change.

Calibration note: `uncertainty_band` exists because a probability is only
useful for routing if it is calibrated. Nothing in the repository has measured
that yet, so the band defaults to empty (every call decides). Widen it only
once a reliability diagram says the middle of the range really is where the
grader is unsure. See E7 in tasks/JEV_JUDGE_V2_PLAN.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.evaluation.jev_judge import JevJudge


@dataclass
class GradingDecision:
    """One in-loop grading verdict.

    `needs_correction` is the actionable bit. `confident` is false when the
    probability lands inside the uncertainty band, which is the caller's cue to
    escalate rather than to act.
    """

    needs_correction: bool
    groundedness: float
    pass_probability: float
    confident: bool
    latency_ms: float
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.error is None


class JevRelevanceGrader:
    """Typed, sub-second relevance grading for a self-correcting agent loop."""

    def __init__(
        self,
        judge: JevJudge,
        *,
        correction_threshold: float = 0.5,
        uncertainty_band: tuple[float, float] | None = None,
    ) -> None:
        if not 0.0 <= correction_threshold <= 1.0:
            raise ValueError("correction_threshold must be in [0, 1]")
        if uncertainty_band is not None:
            low, high = uncertainty_band
            if not 0.0 <= low <= high <= 1.0:
                raise ValueError("uncertainty_band must be an ordered pair in [0, 1]")
        self.judge = judge
        self.correction_threshold = correction_threshold
        self.uncertainty_band = uncertainty_band

    def _confident(self, probability: float) -> bool:
        if self.uncertainty_band is None:
            return True
        low, high = self.uncertainty_band
        return not (low <= probability <= high)

    async def grade(
        self,
        query: str,
        retrieved_chunks: list[str],
        answer: str,
    ) -> GradingDecision:
        """Grade one retrieval/answer pair.

        A failed call is reported as `needs_correction=True` with
        `confident=False` and the error preserved. Correcting unnecessarily
        costs a retrieval; skipping a correction that was needed ships a wrong
        answer, so an unavailable grader must fail toward caution. The caller
        can still tell this apart from a real verdict via `is_valid`, which is
        the distinction the compare harness originally lost.
        """
        verdict = await self.judge.judge_trace(query, retrieved_chunks, answer)

        if verdict.error is not None:
            return GradingDecision(
                needs_correction=True,
                groundedness=0.0,
                pass_probability=0.0,
                confident=False,
                latency_ms=verdict.latency_ms,
                error=verdict.error,
            )

        probability = float(verdict.does_pass_probability)
        return GradingDecision(
            needs_correction=probability < self.correction_threshold,
            groundedness=verdict.groundedness,
            pass_probability=probability,
            confident=self._confident(probability),
            latency_ms=verdict.latency_ms,
        )

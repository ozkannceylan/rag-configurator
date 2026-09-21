"""Offline mock judges for CI and demo COMPARE_REPORT generation."""

from __future__ import annotations

import copy
import hashlib
import json
import random
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.evaluation.compare import EvalCase
from app.evaluation.jev_judge import JevClient, JevJudge, parse_system_one_response
from app.evaluation.quality_judge import parse_quality_judge_response
from app.evaluation.verdict import JudgeVerdict

DEFAULT_RECORDED_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "jev_recorded_responses.json"
)


def load_recorded_jev_responses(path: Path | None = None) -> dict[str, Any]:
    data = json.loads((path or DEFAULT_RECORDED_PATH).read_text(encoding="utf-8"))
    return data.get("responses") or {}


def case_key(question: str, answer: str) -> tuple[str, str]:
    return (question.strip(), answer.strip())


def index_cases(cases: Sequence[EvalCase]) -> dict[tuple[str, str], EvalCase]:
    return {case_key(c.question, c.answer): c for c in cases}


class RecordedJevTransport:
    """Return committed `/v1/systemone` payloads. No network."""

    def __init__(
        self,
        cases: Sequence[EvalCase],
        responses: dict[str, Any] | None = None,
        latency_ms: float = 0.0,
    ) -> None:
        self._index = index_cases(cases)
        self._responses = (
            responses if responses is not None else load_recorded_jev_responses()
        )
        self.latency_ms = latency_ms

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = payload.get("state") or {}
        case = self._index.get(
            case_key(state.get("question", ""), state.get("answer", ""))
        )
        if case is None or case.id not in self._responses:
            raise RuntimeError(
                f"No recorded Jev fixture for question={state.get('question', '')[:60]!r}"
            )
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000.0)
        return copy.deepcopy(self._responses[case.id])


def recorded_jev_judge(
    cases: Sequence[EvalCase],
    responses: dict[str, Any] | None = None,
    reported_latency_ms: float | None = None,
) -> JevJudge:
    transport = RecordedJevTransport(cases, responses=responses)
    client = JevClient(api_key="mock-not-used", request_fn=transport)
    judge = JevJudge(client=client)
    if reported_latency_ms is None:
        return judge
    inner = judge.judge_trace

    async def _judge_trace(question: str, retrieved_chunks: list[str], answer: str):
        verdict = await inner(question, retrieved_chunks, answer)
        verdict.latency_ms = float(reported_latency_ms)
        return verdict

    judge.judge_trace = _judge_trace  # type: ignore[method-assign]
    return judge


class SimulatedLLMJudge:
    """Seeded LLM-as-judge stand-in that still uses the real JSON parser.

    Adds repeat-to-repeat noise so the compare report can show variance without
    calling a provider. Not a live measurement.
    """

    def __init__(
        self,
        cases: Sequence[EvalCase],
        *,
        seed: int = 7,
        model: str = "gpt-4o-mini-sim",
        base_latency_ms: float = 180.0,
        usd_per_call: float = 0.0025,
    ) -> None:
        self._index = index_cases(cases)
        self.seed = seed
        self.model = model
        self.base_latency_ms = base_latency_ms
        self.usd_per_call = usd_per_call
        self._call_count = 0

    def _rng(self, question: str, answer: str, call_index: int) -> random.Random:
        material = f"{self.seed}:{question}:{answer}:{call_index}".encode()
        digest = hashlib.sha256(material).hexdigest()
        return random.Random(int(digest[:16], 16))

    async def judge_trace(
        self,
        question: str,
        retrieved_chunks: list[str],
        answer: str,
    ) -> JudgeVerdict:
        del retrieved_chunks
        self._call_count += 1
        case = self._index.get(case_key(question, answer))
        rng = self._rng(question, answer, self._call_count)
        if case is None:
            quality = 3.0 + rng.uniform(-1.0, 1.0)
            does_pass = quality >= 3.5
            groundedness = 0.5
        else:
            oracle_q = float(
                case.oracle_quality if case.oracle_quality is not None else 3.0
            )
            # LLM-like jitter: ~0.35 std on the 1–5 scale, occasional pass flips
            # on the borderline partial case.
            quality = oracle_q + rng.gauss(0.0, 0.35)
            does_pass = (
                bool(case.oracle_pass)
                if case.oracle_pass is not None
                else quality >= 3.5
            )
            if case.id == "remote-internet-partial":
                does_pass = rng.random() > 0.35
            elif rng.random() < 0.08:
                does_pass = not does_pass
            groundedness = 0.95 if case.oracle_pass else 0.15
            if case.id == "remote-internet-partial":
                groundedness = 0.45 + rng.uniform(-0.1, 0.1)
        quality = max(1.0, min(5.0, quality))
        groundedness = max(0.0, min(1.0, groundedness))
        raw_json = json.dumps(
            {
                "quality": round(quality, 2),
                "does_pass": does_pass,
                "groundedness": round(groundedness, 3),
                "explanation": "simulated llm judge",
            }
        )
        parsed = parse_quality_judge_response(raw_json)
        latency = self.base_latency_ms + rng.uniform(40.0, 160.0)
        return JudgeVerdict(
            judge="llm",
            quality=float(parsed["quality"]),
            does_pass=bool(parsed["does_pass"]),
            groundedness=float(parsed["groundedness"]),
            latency_ms=latency,
            cost_usd=self.usd_per_call,
            model=self.model,
            does_pass_probability=1.0 if parsed["does_pass"] else 0.0,
            explanation=str(parsed["explanation"]),
            raw={"content": raw_json, "parsed": parsed},
        )


def parse_recorded_verdict(payload: dict[str, Any]) -> JudgeVerdict:
    """Helper for unit tests that skip the async client."""
    return parse_system_one_response(payload)

"""Shared verdict types for Jev and LLM quality judges."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JudgeVerdict:
    """One judge call on a frozen RAG trace."""

    judge: str
    quality: float
    does_pass: bool
    groundedness: float
    latency_ms: float
    cost_usd: float
    model: str
    does_pass_probability: float = 1.0
    explanation: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def as_row(self) -> dict[str, Any]:
        return {
            "judge": self.judge,
            "quality": self.quality,
            "does_pass": int(self.does_pass),
            "groundedness": self.groundedness,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "model": self.model,
            "does_pass_probability": self.does_pass_probability,
            "explanation": self.explanation,
            "error": self.error,
        }

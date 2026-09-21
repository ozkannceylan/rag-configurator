"""Abstract guardrail interface and result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GuardrailCheck:
    """Result of a single guardrail check."""

    name: str
    passed: bool
    score: float = 1.0
    details: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "score": self.score,
            "details": self.details,
        }


@dataclass
class GuardrailResult:
    """Aggregated result from all guardrail checks."""

    passed: bool
    checks: list[GuardrailCheck] = field(default_factory=list)
    blocked_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
            "blocked_reason": self.blocked_reason,
        }


class BaseGuardrail(ABC):
    """Abstract base class for guardrails."""

    @abstractmethod
    async def check_input(self, query: str) -> GuardrailResult:
        """
        Run pre-query guardrail checks.

        Args:
            query: User query text.

        Returns:
            GuardrailResult with pass/fail and details.
        """
        pass

    @abstractmethod
    async def check_output(self, query: str, response: str) -> GuardrailResult:
        """
        Run post-response guardrail checks.

        Args:
            query: Original user query.
            response: Generated response text.

        Returns:
            GuardrailResult with pass/fail and details.
        """
        pass

"""Abstract base class for evaluators."""

from abc import ABC, abstractmethod

from app.evaluation.models import EvaluationResult


class BaseEvaluator(ABC):
    """Abstract evaluator that all evaluation strategies must implement."""

    @abstractmethod
    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> EvaluationResult:
        """
        Evaluate a query/answer pair.

        Args:
            query: The user query.
            answer: The generated (or provided) answer.
            contexts: List of retrieved context strings.
            ground_truth: Optional expected correct answer.

        Returns:
            EvaluationResult with scores for each metric.
        """
        ...

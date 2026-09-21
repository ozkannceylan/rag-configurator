"""Evaluation data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MetricResult(BaseModel):
    """Result of a single evaluation metric."""

    name: str = Field(
        ..., description="Metric name (e.g., faithfulness, answer_relevancy)"
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Score between 0 and 1")
    explanation: str = Field(default="", description="Explanation of the score")


class EvaluationResult(BaseModel):
    """Complete evaluation result for a query/answer pair."""

    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Metric name to score mapping",
    )
    metric_results: list[MetricResult] = Field(
        default_factory=list,
        description="Detailed results for each metric",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (e.g., model used, latency)",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the evaluation was performed",
    )

    def average_score(self) -> float:
        """Compute the mean of all metric scores."""
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)


class EvaluationRun(BaseModel):
    """A persisted evaluation run stored in the database."""

    id: str = Field(..., description="Unique run identifier")
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    user_id: str = Field(default="", description="User who triggered the evaluation")
    query: str = Field(..., description="Input query")
    answer: str = Field(..., description="Generated or provided answer")
    contexts: list[str] = Field(
        default_factory=list, description="Retrieved context chunks"
    )
    ground_truth: str | None = Field(None, description="Expected correct answer")
    results: EvaluationResult = Field(..., description="Evaluation results")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )


class EvaluationSummary(BaseModel):
    """Aggregated evaluation metrics for a configuration."""

    config_id: str = Field(..., description="RAG pipeline configuration ID")
    total_runs: int = Field(default=0, description="Total number of evaluation runs")
    avg_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Average score for each metric across all runs",
    )
    score_distribution: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Score distribution buckets per metric (e.g., 0.0-0.2, 0.2-0.4, ...)",
    )
    date_range: dict[str, str | None] = Field(
        default_factory=lambda: {"start": None, "end": None},
        description="Date range of evaluation runs (ISO format strings)",
    )

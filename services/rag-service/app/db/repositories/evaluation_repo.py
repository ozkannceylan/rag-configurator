"""MongoDB repository for evaluation runs."""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.evaluation.models import (
    EvaluationResult,
    EvaluationRun,
    EvaluationSummary,
    MetricResult,
)

logger = logging.getLogger(__name__)

COLLECTION = "evaluations"


class EvaluationRepository:
    """Persist and query evaluation runs in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db[COLLECTION]

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_evaluation(self, run: EvaluationRun) -> str:
        """Insert an evaluation run and return its document id."""
        doc = run.model_dump()
        # Ensure created_at is a proper datetime
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_evaluations_by_config(
        self,
        config_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[EvaluationRun]:
        """Return evaluation runs for a config, newest first."""
        cursor = (
            self.collection.find({"config_id": config_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        runs: List[EvaluationRun] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            runs.append(_doc_to_run(doc))
        return runs

    async def count_by_config(self, config_id: str) -> int:
        """Count total evaluation runs for a config."""
        return await self.collection.count_documents({"config_id": config_id})

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    async def get_evaluation_summary(self, config_id: str) -> EvaluationSummary:
        """Compute an aggregated summary for a config."""
        total = await self.count_by_config(config_id)

        if total == 0:
            return EvaluationSummary(config_id=config_id)

        # Aggregate scores and date range in a single pass
        score_sums: Dict[str, float] = defaultdict(float)
        score_counts: Dict[str, int] = defaultdict(int)
        # Buckets: "0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"
        distribution: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
        )
        earliest: Optional[datetime] = None
        latest: Optional[datetime] = None

        cursor = self.collection.find({"config_id": config_id})
        async for doc in cursor:
            created = doc.get("created_at")
            if isinstance(created, datetime):
                if earliest is None or created < earliest:
                    earliest = created
                if latest is None or created > latest:
                    latest = created

            results_data = doc.get("results", {})
            scores = results_data.get("scores", {})
            for metric_name, score in scores.items():
                score_sums[metric_name] += score
                score_counts[metric_name] += 1
                bucket = _score_bucket(score)
                distribution[metric_name][bucket] += 1

        avg_scores = {
            name: round(score_sums[name] / score_counts[name], 4)
            for name in score_sums
            if score_counts[name] > 0
        }

        date_range = {
            "start": earliest.isoformat() if earliest else None,
            "end": latest.isoformat() if latest else None,
        }

        return EvaluationSummary(
            config_id=config_id,
            total_runs=total,
            avg_scores=avg_scores,
            score_distribution=dict(distribution),
            date_range=date_range,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score_bucket(score: float) -> str:
    """Map a 0-1 score to a distribution bucket."""
    if score < 0.2:
        return "0.0-0.2"
    elif score < 0.4:
        return "0.2-0.4"
    elif score < 0.6:
        return "0.4-0.6"
    elif score < 0.8:
        return "0.6-0.8"
    else:
        return "0.8-1.0"


def _doc_to_run(doc: Dict[str, Any]) -> EvaluationRun:
    """Convert a MongoDB document to an ``EvaluationRun``."""
    results_data = doc.get("results", {})
    metric_results = [
        MetricResult(**mr) for mr in results_data.get("metric_results", [])
    ]
    evaluation_result = EvaluationResult(
        scores=results_data.get("scores", {}),
        metric_results=metric_results,
        metadata=results_data.get("metadata", {}),
        timestamp=results_data.get("timestamp", datetime.utcnow()),
    )
    return EvaluationRun(
        id=doc.get("id", str(doc.get("_id", ""))),
        config_id=doc.get("config_id", ""),
        user_id=doc.get("user_id", ""),
        query=doc.get("query", ""),
        answer=doc.get("answer", ""),
        contexts=doc.get("contexts", []),
        ground_truth=doc.get("ground_truth"),
        results=evaluation_result,
        created_at=doc.get("created_at", datetime.utcnow()),
    )

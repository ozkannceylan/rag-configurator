"""Tests for the evaluation framework (models, RAGAS evaluator, judge evaluator, API)."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.evaluation.models import (
    EvaluationResult,
    EvaluationRun,
    EvaluationSummary,
    MetricResult,
)
from app.evaluation.ragas_eval import (
    AVAILABLE_METRICS,
    RagasEvaluator,
    _parse_score_response,
)
from app.evaluation.judge import JudgeEvaluator, DEFAULT_RUBRICS, _parse_judge_response
from app.llm.base import BaseLLM, LLMConfig, LLMResponse, LLMUsage, Message


# =========================================================================
# Helpers
# =========================================================================


class MockLLM(BaseLLM):
    """A mock LLM that returns configurable responses."""

    def __init__(self, responses=None):
        super().__init__(config=LLMConfig(model="mock-model"))
        self._responses = responses or []
        self._call_index = 0
        self._provider_name = "mock"

    async def generate(self, messages, temperature=None, max_tokens=None, **kwargs):
        if self._call_index < len(self._responses):
            content = self._responses[self._call_index]
            self._call_index += 1
        else:
            content = '{"score": 0.5, "explanation": "default mock"}'
        return LLMResponse(
            content=content,
            model="mock-model",
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

    async def stream(self, messages, temperature=None, max_tokens=None, **kwargs):
        yield "mock stream"


# =========================================================================
# Model tests
# =========================================================================


class TestModels:
    def test_metric_result_creation(self):
        mr = MetricResult(name="faithfulness", score=0.85, explanation="Mostly supported")
        assert mr.name == "faithfulness"
        assert mr.score == 0.85
        assert mr.explanation == "Mostly supported"

    def test_metric_result_score_bounds(self):
        """Score must be between 0 and 1."""
        with pytest.raises(Exception):
            MetricResult(name="test", score=1.5, explanation="too high")
        with pytest.raises(Exception):
            MetricResult(name="test", score=-0.1, explanation="too low")

    def test_evaluation_result_average_score(self):
        result = EvaluationResult(
            scores={"a": 0.8, "b": 0.6, "c": 1.0},
            metric_results=[],
        )
        assert abs(result.average_score() - 0.8) < 1e-9

    def test_evaluation_result_average_empty(self):
        result = EvaluationResult()
        assert result.average_score() == 0.0

    def test_evaluation_run_creation(self):
        run = EvaluationRun(
            id="run-1",
            config_id="cfg-1",
            user_id="user-1",
            query="What is AI?",
            answer="AI is ...",
            contexts=["context 1"],
            ground_truth="Artificial Intelligence",
            results=EvaluationResult(scores={"faithfulness": 0.9}),
        )
        assert run.config_id == "cfg-1"
        assert run.results.scores["faithfulness"] == 0.9

    def test_evaluation_summary_creation(self):
        summary = EvaluationSummary(
            config_id="cfg-1",
            total_runs=10,
            avg_scores={"faithfulness": 0.85, "relevance": 0.9},
            score_distribution={"faithfulness": {"0.8-1.0": 8, "0.6-0.8": 2}},
            date_range={"start": "2024-01-01T00:00:00", "end": "2024-06-01T00:00:00"},
        )
        assert summary.total_runs == 10
        assert summary.avg_scores["faithfulness"] == 0.85


# =========================================================================
# RAGAS evaluator tests
# =========================================================================


class TestRagasEvaluator:
    def test_available_metrics(self):
        assert "faithfulness" in AVAILABLE_METRICS
        assert "answer_relevancy" in AVAILABLE_METRICS
        assert "context_precision" in AVAILABLE_METRICS
        assert "context_recall" in AVAILABLE_METRICS

    def test_invalid_metric_raises(self):
        llm = MockLLM()
        with pytest.raises(ValueError, match="Unknown metric"):
            RagasEvaluator(llm=llm, metrics=["nonexistent_metric"])

    async def test_faithfulness_metric(self):
        llm = MockLLM(responses=[
            '{"score": 0.9, "explanation": "Answer is well supported by context."}'
        ])
        evaluator = RagasEvaluator(llm=llm, metrics=["faithfulness"])
        result = await evaluator.evaluate(
            query="What is Python?",
            answer="Python is a programming language.",
            contexts=["Python is a high-level programming language."],
        )
        assert "faithfulness" in result.scores
        assert result.scores["faithfulness"] == 0.9
        assert len(result.metric_results) == 1

    async def test_answer_relevancy_metric(self):
        llm = MockLLM(responses=[
            '{"score": 0.85, "explanation": "Directly addresses the query."}'
        ])
        evaluator = RagasEvaluator(llm=llm, metrics=["answer_relevancy"])
        result = await evaluator.evaluate(
            query="What is Python?",
            answer="Python is a programming language.",
            contexts=["Python is used for data science."],
        )
        assert result.scores["answer_relevancy"] == 0.85

    async def test_context_precision_metric(self):
        llm = MockLLM(responses=[
            '{"score": 0.7, "explanation": "Most contexts are relevant."}'
        ])
        evaluator = RagasEvaluator(llm=llm, metrics=["context_precision"])
        result = await evaluator.evaluate(
            query="What is Python?",
            answer="Python is a language.",
            contexts=["Python is a language.", "Java is also a language."],
        )
        assert result.scores["context_precision"] == 0.7

    async def test_context_recall_with_ground_truth(self):
        llm = MockLLM(responses=[
            '{"score": 0.95, "explanation": "Contexts cover ground truth well."}'
        ])
        evaluator = RagasEvaluator(llm=llm, metrics=["context_recall"])
        result = await evaluator.evaluate(
            query="What is Python?",
            answer="Python is a language.",
            contexts=["Python is a high-level general-purpose programming language."],
            ground_truth="Python is a programming language.",
        )
        assert result.scores["context_recall"] == 0.95

    async def test_context_recall_skipped_without_ground_truth(self):
        llm = MockLLM(responses=[])
        evaluator = RagasEvaluator(llm=llm, metrics=["context_recall"])
        result = await evaluator.evaluate(
            query="What is Python?",
            answer="Python is a language.",
            contexts=["ctx"],
            ground_truth=None,
        )
        assert result.scores["context_recall"] == 0.0
        assert "Skipped" in result.metric_results[0].explanation

    async def test_all_metrics(self):
        llm = MockLLM(responses=[
            '{"score": 0.9, "explanation": "faithful"}',
            '{"score": 0.85, "explanation": "relevant"}',
            '{"score": 0.7, "explanation": "precise"}',
            '{"score": 0.8, "explanation": "good recall"}',
        ])
        evaluator = RagasEvaluator(llm=llm)
        result = await evaluator.evaluate(
            query="What is Python?",
            answer="Python is a programming language.",
            contexts=["Python is a language."],
            ground_truth="Python is a programming language.",
        )
        assert len(result.scores) == 4
        assert result.metadata["evaluator"] == "ragas"

    async def test_llm_error_handled_gracefully(self):
        """If the LLM raises, the metric gets score 0 with an error explanation."""
        llm = MockLLM()
        # Override generate to raise
        llm.generate = AsyncMock(side_effect=RuntimeError("LLM down"))
        evaluator = RagasEvaluator(llm=llm, metrics=["faithfulness"])
        result = await evaluator.evaluate(
            query="q", answer="a", contexts=["c"]
        )
        assert result.scores["faithfulness"] == 0.0
        assert "error" in result.metric_results[0].explanation.lower()

    def test_parse_score_response_valid(self):
        parsed = _parse_score_response('{"score": 0.75, "explanation": "good"}')
        assert parsed["score"] == 0.75
        assert parsed["explanation"] == "good"

    def test_parse_score_response_with_markdown(self):
        raw = '```json\n{"score": 0.6, "explanation": "ok"}\n```'
        parsed = _parse_score_response(raw)
        assert parsed["score"] == 0.6

    def test_parse_score_response_clamping(self):
        parsed = _parse_score_response('{"score": 1.5, "explanation": "over"}')
        assert parsed["score"] == 1.0
        parsed = _parse_score_response('{"score": -0.3, "explanation": "under"}')
        assert parsed["score"] == 0.0

    def test_parse_score_response_invalid_json(self):
        parsed = _parse_score_response("not json at all")
        assert parsed["score"] == 0.0
        assert "Parse error" in parsed["explanation"]


# =========================================================================
# Judge evaluator tests
# =========================================================================


class TestJudgeEvaluator:
    def test_default_rubrics_present(self):
        assert "relevance" in DEFAULT_RUBRICS
        assert "completeness" in DEFAULT_RUBRICS
        assert "conciseness" in DEFAULT_RUBRICS
        assert "accuracy" in DEFAULT_RUBRICS

    async def test_judge_evaluation(self):
        response_json = (
            '{"rubrics": ['
            '{"name": "relevance", "score": 0.9, "explanation": "on topic"},'
            '{"name": "completeness", "score": 0.8, "explanation": "mostly complete"},'
            '{"name": "conciseness", "score": 0.7, "explanation": "a bit verbose"},'
            '{"name": "accuracy", "score": 0.95, "explanation": "accurate"}'
            ']}'
        )
        llm = MockLLM(responses=[response_json])
        evaluator = JudgeEvaluator(llm=llm)
        result = await evaluator.evaluate(
            query="What is Python?",
            answer="Python is a programming language.",
            contexts=["Python is a high-level language."],
        )
        assert result.scores["relevance"] == 0.9
        assert result.scores["accuracy"] == 0.95
        assert result.metadata["evaluator"] == "judge"

    async def test_judge_with_custom_rubrics(self):
        custom_rubrics = {
            "tone": {
                "description": "Is the tone professional?",
                "criteria": "1.0 = very professional; 0.0 = very casual",
            },
        }
        response_json = '{"rubrics": [{"name": "tone", "score": 0.8, "explanation": "professional"}]}'
        llm = MockLLM(responses=[response_json])
        evaluator = JudgeEvaluator(llm=llm, rubrics=custom_rubrics)
        result = await evaluator.evaluate(
            query="q", answer="a", contexts=["c"]
        )
        assert "tone" in result.scores
        assert len(result.scores) == 1

    async def test_judge_with_ground_truth(self):
        response_json = (
            '{"rubrics": ['
            '{"name": "relevance", "score": 0.9, "explanation": "ok"},'
            '{"name": "completeness", "score": 0.85, "explanation": "ok"},'
            '{"name": "conciseness", "score": 0.8, "explanation": "ok"},'
            '{"name": "accuracy", "score": 0.95, "explanation": "ok"}'
            ']}'
        )
        llm = MockLLM(responses=[response_json])
        evaluator = JudgeEvaluator(llm=llm)
        result = await evaluator.evaluate(
            query="What is Python?",
            answer="Python is a language.",
            contexts=["Python is used in data science."],
            ground_truth="Python is a programming language.",
        )
        assert len(result.scores) == 4

    async def test_judge_llm_error(self):
        llm = MockLLM()
        llm.generate = AsyncMock(side_effect=RuntimeError("LLM error"))
        evaluator = JudgeEvaluator(llm=llm)
        result = await evaluator.evaluate(query="q", answer="a", contexts=["c"])
        # All rubric scores should be 0 due to error
        for score in result.scores.values():
            assert score == 0.0

    def test_parse_judge_response_valid(self):
        raw = '{"rubrics": [{"name": "relevance", "score": 0.8, "explanation": "ok"}]}'
        results = _parse_judge_response(raw, ["relevance"])
        assert len(results) == 1
        assert results[0].name == "relevance"
        assert results[0].score == 0.8

    def test_parse_judge_response_missing_rubric(self):
        raw = '{"rubrics": [{"name": "relevance", "score": 0.8, "explanation": "ok"}]}'
        results = _parse_judge_response(raw, ["relevance", "completeness"])
        assert len(results) == 2
        completeness = [r for r in results if r.name == "completeness"][0]
        assert completeness.score == 0.0

    def test_parse_judge_response_invalid_json(self):
        results = _parse_judge_response("garbage", ["relevance", "accuracy"])
        assert len(results) == 2
        assert all(r.score == 0.0 for r in results)


# =========================================================================
# Evaluation API endpoint tests
# =========================================================================


class TestEvaluationAPI:
    """Test the evaluation API endpoints via the ASGI test client."""

    @pytest.fixture
    def mock_eval_collection(self):
        """Create a mock MongoDB collection for evaluations."""
        coll = MagicMock()
        coll.insert_one = AsyncMock(return_value=MagicMock(inserted_id="doc-1"))
        coll.count_documents = AsyncMock(return_value=0)

        # find() returns an async-iterable cursor
        cursor = MagicMock()
        cursor.sort = MagicMock(return_value=cursor)
        cursor.skip = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)

        async def _empty_aiter():
            return
            yield  # pragma: no cover - makes this an async generator

        cursor.__aiter__ = lambda self: _empty_aiter()
        coll.find = MagicMock(return_value=cursor)

        return coll

    async def test_evaluate_endpoint(self, client, mock_mongodb, mock_eval_collection):
        """POST /api/v1/evaluation/evaluate should return evaluation results."""
        # Configure mock DB to return the evaluation collection and a config
        def getitem(name):
            if name == "evaluations":
                return mock_eval_collection
            mock_coll = MagicMock()
            mock_coll.find_one = AsyncMock(
                return_value={"_id": "config-123", "created_by": "user-456"}
            )
            return mock_coll

        mock_mongodb.__getitem__ = MagicMock(side_effect=getitem)

        # Mock the evaluator
        mock_result = EvaluationResult(
            scores={"faithfulness": 0.9},
            metric_results=[MetricResult(name="faithfulness", score=0.9, explanation="good")],
            metadata={"evaluator": "ragas"},
        )

        with patch(
            "app.api.v1.evaluation._build_evaluator"
        ) as mock_build:
            mock_evaluator = AsyncMock()
            mock_evaluator.evaluate = AsyncMock(return_value=mock_result)
            mock_build.return_value = mock_evaluator

            response = await client.post(
                "/api/v1/evaluation/evaluate",
                json={
                    "config_id": "config-123",
                    "query": "What is Python?",
                    "answer": "Python is a language.",
                    "contexts": ["Python is a programming language."],
                    "metrics": ["faithfulness"],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "faithfulness" in data["data"]["scores"]

    async def test_evaluate_endpoint_missing_auth(self, client, mock_mongodb):
        """Should reject requests without X-User-ID header."""
        # Remove the default header
        from app.main import app
        from app.db.mongodb import mongodb
        from httpx import ASGITransport, AsyncClient

        mongodb.database = mock_mongodb
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            # No X-User-ID header
        ) as ac:
            response = await ac.post(
                "/api/v1/evaluation/evaluate",
                json={
                    "config_id": "config-123",
                    "query": "What is Python?",
                    "answer": "Python is a language.",
                    "contexts": ["ctx"],
                },
            )
        assert response.status_code in (401, 403)

    async def test_get_evaluation_history(self, client, mock_mongodb, mock_eval_collection):
        """GET /api/v1/evaluation/{config_id} should return evaluation runs."""
        mock_mongodb.__getitem__ = MagicMock(return_value=mock_eval_collection)

        response = await client.get(
            "/api/v1/evaluation/config-123",
            params={"skip": 0, "limit": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "meta" in data

    async def test_get_evaluation_summary(self, client, mock_mongodb, mock_eval_collection):
        """GET /api/v1/evaluation/{config_id}/summary should return a summary."""
        mock_mongodb.__getitem__ = MagicMock(return_value=mock_eval_collection)

        response = await client.get("/api/v1/evaluation/config-123/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["config_id"] == "config-123"
        assert data["data"]["total_runs"] == 0


# =========================================================================
# Repository tests
# =========================================================================


class TestEvaluationRepository:
    async def test_create_evaluation(self):
        from app.db.repositories.evaluation_repo import EvaluationRepository

        mock_coll = MagicMock()
        mock_coll.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id="inserted-id")
        )

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_coll)

        repo = EvaluationRepository(mock_db)
        run = EvaluationRun(
            id=str(uuid.uuid4()),
            config_id="cfg-1",
            user_id="user-1",
            query="q",
            answer="a",
            contexts=["c"],
            results=EvaluationResult(scores={"f": 0.8}),
        )
        doc_id = await repo.create_evaluation(run)
        assert doc_id == "inserted-id"
        mock_coll.insert_one.assert_awaited_once()

    async def test_get_evaluations_by_config(self):
        from app.db.repositories.evaluation_repo import EvaluationRepository

        doc = {
            "_id": "doc-1",
            "id": "run-1",
            "config_id": "cfg-1",
            "user_id": "user-1",
            "query": "q",
            "answer": "a",
            "contexts": ["c"],
            "ground_truth": None,
            "results": {
                "scores": {"faithfulness": 0.9},
                "metric_results": [
                    {"name": "faithfulness", "score": 0.9, "explanation": "ok"}
                ],
                "metadata": {},
                "timestamp": datetime.utcnow().isoformat(),
            },
            "created_at": datetime.utcnow(),
        }

        # Build an async-iterable cursor mock
        cursor = MagicMock()
        cursor.sort = MagicMock(return_value=cursor)
        cursor.skip = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)

        async def async_iter():
            yield doc

        cursor.__aiter__ = lambda self: async_iter()

        mock_coll = MagicMock()
        mock_coll.find = MagicMock(return_value=cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_coll)

        repo = EvaluationRepository(mock_db)
        runs = await repo.get_evaluations_by_config("cfg-1")
        assert len(runs) == 1
        assert runs[0].config_id == "cfg-1"
        assert runs[0].results.scores["faithfulness"] == 0.9

    async def test_get_evaluation_summary_empty(self):
        from app.db.repositories.evaluation_repo import EvaluationRepository

        mock_coll = MagicMock()
        mock_coll.count_documents = AsyncMock(return_value=0)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_coll)

        repo = EvaluationRepository(mock_db)
        summary = await repo.get_evaluation_summary("cfg-1")
        assert summary.total_runs == 0
        assert summary.avg_scores == {}

    async def test_get_evaluation_summary_with_data(self):
        from app.db.repositories.evaluation_repo import EvaluationRepository

        docs = [
            {
                "config_id": "cfg-1",
                "results": {"scores": {"faithfulness": 0.8, "relevance": 0.9}},
                "created_at": datetime(2024, 1, 1),
            },
            {
                "config_id": "cfg-1",
                "results": {"scores": {"faithfulness": 0.6, "relevance": 0.7}},
                "created_at": datetime(2024, 6, 1),
            },
        ]

        async def async_iter():
            for d in docs:
                yield d

        cursor = MagicMock()
        cursor.__aiter__ = lambda self: async_iter()

        mock_coll = MagicMock()
        mock_coll.count_documents = AsyncMock(return_value=2)
        mock_coll.find = MagicMock(return_value=cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_coll)

        repo = EvaluationRepository(mock_db)
        summary = await repo.get_evaluation_summary("cfg-1")
        assert summary.total_runs == 2
        assert abs(summary.avg_scores["faithfulness"] - 0.7) < 0.01
        assert abs(summary.avg_scores["relevance"] - 0.8) < 0.01
        assert summary.date_range["start"] is not None

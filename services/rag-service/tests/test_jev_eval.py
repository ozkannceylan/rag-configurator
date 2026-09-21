"""Tests for Jev vs LLM-as-judge evaluation (CI-safe, no live keys)."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.evaluation.compare import (
    EvalCase,
    default_cases_path,
    load_eval_cases,
    pairwise_repeatability,
    percentile,
    render_compare_report,
    run_compare,
    sample_variance,
    write_artifacts,
)
from app.evaluation.jev_judge import (
    JevClient,
    JevJudge,
    estimate_jev_cost_usd,
    parse_system_one_response,
    score_to_quality_1_5,
)
from app.evaluation.mock_judges import (
    SimulatedLLMJudge,
    load_recorded_jev_responses,
    recorded_jev_judge,
)
from app.evaluation.quality_judge import QualityJudge, parse_quality_judge_response
from app.evaluation.rubric import build_judge_state, quality_01
from app.llm.base import BaseLLM, LLMConfig, LLMResponse, LLMUsage


class MockLLM(BaseLLM):
    def __init__(self, content: str):
        super().__init__(config=LLMConfig(model="mock-model"))
        self._content = content
        self._provider_name = "mock"

    async def generate(self, messages, temperature=None, max_tokens=None, **kwargs):
        return LLMResponse(
            content=self._content,
            model="mock-model",
            usage=LLMUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30),
        )

    async def stream(self, messages, temperature=None, max_tokens=None, **kwargs):
        yield self._content


class TestScoreMapping:
    def test_zero_indexed_excellent(self):
        assert score_to_quality_1_5(4.0, n_levels=5) == 5.0

    def test_zero_indexed_unhelpful(self):
        assert score_to_quality_1_5(0.0, n_levels=5) == 1.0

    def test_mid_scale(self):
        assert abs(score_to_quality_1_5(2.0, n_levels=5) - 3.0) < 1e-9

    def test_clamps_out_of_range(self):
        assert score_to_quality_1_5(-1.0, n_levels=5) == 1.0
        assert score_to_quality_1_5(9.0, n_levels=5) == 5.0

    def test_quality_01_mapping(self):
        assert quality_01(1.0) == 0.0
        assert quality_01(5.0) == 1.0
        assert abs(quality_01(3.0) - 0.5) < 1e-9


class TestJevParse:
    def test_parse_recorded_pass_case(self):
        recorded = load_recorded_jev_responses()
        verdict = parse_system_one_response(recorded["pto-allowance-grounded"])
        assert verdict.does_pass is True
        assert verdict.quality >= 4.5
        assert verdict.groundedness > 0.9
        assert verdict.judge == "jev"
        assert "jev" in verdict.model

    def test_parse_recorded_fail_case(self):
        recorded = load_recorded_jev_responses()
        verdict = parse_system_one_response(recorded["pto-hallucinated-unlimited"])
        assert verdict.does_pass is False
        assert verdict.quality < 2.0

    def test_cost_from_input_tokens(self):
        cost = estimate_jev_cost_usd({"input_tokens": 1000}, usd_per_million_input=0.35)
        assert abs(cost - 0.00035) < 1e-9

    def test_cost_fallback_without_usage(self):
        cost = estimate_jev_cost_usd(None, fallback_per_call=0.00035)
        assert cost == 0.00035

    async def test_jev_judge_uses_injected_transport(self):
        payload = load_recorded_jev_responses()["hmo-premium-grounded"]

        def request_fn(_body):
            return payload

        judge = JevJudge(client=JevClient(api_key="unused", request_fn=request_fn))
        result = await judge.evaluate(
            query="What is the employee monthly premium for the HMO medical plan?",
            answer="The HMO plan employee monthly premium is $80.",
            contexts=["HMO Plan employee premium $80"],
        )
        assert result.metadata["evaluator"] == "jev"
        assert result.scores["does_pass"] == 1.0
        assert result.scores["quality"] > 0.9

    async def test_jev_judge_error_is_soft(self):
        def request_fn(_body):
            raise RuntimeError("network down")

        judge = JevJudge(client=JevClient(api_key="unused", request_fn=request_fn))
        verdict = await judge.judge_trace("q", ["c"], "a")
        assert verdict.error is not None
        assert verdict.does_pass is False


class TestLLMParse:
    def test_valid_json(self):
        parsed = parse_quality_judge_response(
            '{"quality": 4, "does_pass": true, "groundedness": 0.9, "explanation": "ok"}'
        )
        assert parsed["quality"] == 4.0
        assert parsed["does_pass"] is True
        assert parsed["groundedness"] == 0.9
        assert parsed["error"] is None

    def test_markdown_fence(self):
        raw = '```json\n{"quality": 2, "does_pass": false, "groundedness": 0.2, "explanation": "weak"}\n```'
        parsed = parse_quality_judge_response(raw)
        assert parsed["quality"] == 2.0
        assert parsed["does_pass"] is False

    def test_clamps_quality(self):
        parsed = parse_quality_judge_response(
            '{"quality": 9, "does_pass": 1, "groundedness": 1.5, "explanation": ""}'
        )
        assert parsed["quality"] == 5.0
        assert parsed["does_pass"] is True
        assert parsed["groundedness"] == 1.0

    def test_invalid_json(self):
        parsed = parse_quality_judge_response("not json")
        assert parsed["does_pass"] is False
        assert parsed["error"] == "json_decode"

    def test_pass_string_synonyms(self):
        parsed = parse_quality_judge_response(
            '{"quality": 4, "does_pass": "pass", "groundedness": 0.8}'
        )
        assert parsed["does_pass"] is True

    async def test_quality_judge_evaluate(self):
        llm = MockLLM(
            '{"quality": 5, "does_pass": true, "groundedness": 0.99, "explanation": "grounded"}'
        )
        judge = QualityJudge(llm=llm)
        result = await judge.evaluate(
            query="How many PTO days?",
            answer="15 days for 0-2 years.",
            contexts=["0-2 years: 15 days"],
        )
        assert result.metadata["evaluator"] == "llm"
        assert result.scores["does_pass"] == 1.0
        assert result.scores["quality"] == 1.0
        assert result.metadata["quality_1_5"] == 5.0


class TestOllamaCloudJudge:
    def test_no_key_returns_none(self):
        from app.evaluation.ollama_cloud import build_ollama_cloud_llm

        assert build_ollama_cloud_llm({}) is None

    def test_local_base_url_still_uses_cloud_openai_compat(self):
        from app.evaluation.ollama_cloud import (
            DEFAULT_OLLAMA_CLOUD_OPENAI_BASE,
            build_ollama_cloud_llm,
        )
        from app.llm.ollama import OllamaLLM
        from app.llm.openai import OpenAILLM

        llm = build_ollama_cloud_llm(
            {
                "OLLAMA_API_KEY": "ollama-test-key",
                "OLLAMA_BASE_URL": "http://localhost:11434",
            }
        )
        assert isinstance(llm, OpenAILLM)
        assert not isinstance(llm, OllamaLLM)
        assert llm.config.base_url == DEFAULT_OLLAMA_CLOUD_OPENAI_BASE
        assert llm.config.model == "gpt-oss:20b"
        assert llm.config.api_key == "ollama-test-key"

    def test_ollama_com_rewritten_to_v1_not_api_v1(self):
        from app.evaluation.ollama_cloud import normalize_openai_compat_base

        assert (
            normalize_openai_compat_base("https://ollama.com")
            == "https://ollama.com/v1"
        )
        assert (
            normalize_openai_compat_base("https://ollama.com/api/v1")
            == "https://ollama.com/v1"
        )
        assert (
            normalize_openai_compat_base("https://ollama.com/v1")
            == "https://ollama.com/v1"
        )

    def test_override_base_and_model(self):
        from app.evaluation.ollama_cloud import build_ollama_cloud_llm

        llm = build_ollama_cloud_llm(
            {
                "OLLAMA_API_KEY": "k",
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "JEV_EVAL_LLM_BASE_URL": "https://ollama.com",
                "JEV_EVAL_LLM_MODEL": "kimi-k2:1t",
            }
        )
        assert llm.config.base_url == "https://ollama.com/v1"
        assert llm.config.model == "kimi-k2:1t"

    def test_non_local_ollama_base_used(self):
        from app.evaluation.ollama_cloud import build_ollama_cloud_llm

        llm = build_ollama_cloud_llm(
            {
                "OLLAMA_API_KEY": "k",
                "OLLAMA_BASE_URL": "https://ollama.com",
            }
        )
        assert llm.config.base_url == "https://ollama.com/v1"

    def test_host_docker_internal_is_local(self):
        from app.evaluation.ollama_cloud import (
            is_local_ollama_url,
            resolve_ollama_cloud_openai_base,
        )

        assert is_local_ollama_url("http://host.docker.internal:11434")
        assert (
            resolve_ollama_cloud_openai_base(
                api_key="k",
                ollama_base_url="http://host.docker.internal:11434",
            )
            == "https://ollama.com/v1"
        )

    def test_quality_evaluator_prefers_ollama_cloud(self, monkeypatch):
        from app.api.v1.evaluation import _build_evaluator
        from app.evaluation.quality_judge import QualityJudge
        from app.llm.openai import OpenAILLM

        monkeypatch.setenv("OLLAMA_API_KEY", "ollama-test-key")
        judge = _build_evaluator("quality", [])
        assert isinstance(judge, QualityJudge)
        assert isinstance(judge.llm, OpenAILLM)
        assert judge.llm.config.base_url == "https://ollama.com/v1"


class TestFixtures:
    def test_committed_cases_meet_minimum(self):
        cases = load_eval_cases(default_cases_path())
        assert len(cases) >= 5
        for case in cases:
            assert case.question
            assert case.answer
            assert case.oracle_pass is not None
            assert case.oracle_quality is not None

    def test_recorded_responses_cover_every_case(self):
        cases = load_eval_cases(default_cases_path())
        recorded = load_recorded_jev_responses()
        missing = [c.id for c in cases if c.id not in recorded]
        assert missing == []

    def test_build_judge_state_shape(self):
        state = build_judge_state("q", ["c1", "c2"], "a")
        assert state == {
            "question": "q",
            "retrieved_chunks": ["c1", "c2"],
            "answer": "a",
        }


class TestCompareMetrics:
    def test_percentile(self):
        assert percentile([1, 2, 3, 4, 5], 0.5) == 3
        assert percentile([10], 0.95) == 10
        assert percentile([], 0.5) == 0.0

    def test_sample_variance_zero_for_constant(self):
        assert sample_variance([4.0, 4.0, 4.0]) == 0.0

    def test_pairwise_repeatability_certain(self):
        assert pairwise_repeatability([True, True, True]) == 1.0
        assert pairwise_repeatability([True, False]) == 0.5

    async def test_run_compare_mock_judges(self, tmp_path):
        cases = load_eval_cases(default_cases_path())
        jev = recorded_jev_judge(cases)
        llm = SimulatedLLMJudge(cases, seed=11)
        result = await run_compare(
            cases,
            {"jev": jev.judge_trace, "llm": llm.judge_trace},
            repeats=3,
            usd_cap=2.0,
            mode="mock/demo",
        )
        assert "jev" in result.summaries
        assert "llm" in result.summaries
        jev_s = result.summaries["jev"]
        llm_s = result.summaries["llm"]
        assert jev_s.n_calls == 3 * len(cases)
        assert jev_s.agreement == 1.0
        assert jev_s.binary_repeatability == 1.0
        assert jev_s.mean_quality_variance == 0.0
        assert llm_s.mean_quality_variance >= 0.0
        assert jev_s.signal_value >= llm_s.signal_value
        report = render_compare_report(result)
        assert "mock/demo" in report
        assert "Jev vs LLM-as-judge" in report
        written = write_artifacts(result, tmp_path)
        assert written["report"].is_file()
        assert written["csv"].is_file()
        assert "judge,case_id,repeat" in written["csv"].read_text(encoding="utf-8")

    async def test_usd_cap_stops_run(self):
        cases = [
            EvalCase(
                id="one",
                question="q",
                retrieved_chunks=["c"],
                answer="a",
                oracle_pass=True,
                oracle_quality=5,
            )
        ]

        async def expensive(_q, _c, _a):
            from app.evaluation.verdict import JudgeVerdict

            return JudgeVerdict(
                judge="llm",
                quality=5.0,
                does_pass=True,
                groundedness=1.0,
                latency_ms=1.0,
                cost_usd=0.8,
                model="stub",
            )

        result = await run_compare(
            cases,
            {"llm": expensive},
            repeats=10,
            usd_cap=1.5,
            mode="live",
        )
        assert result.stopped_reason is not None
        assert result.total_cost_usd >= 1.5
        assert result.summaries["llm"].n_calls < 10


class TestEvaluationAPIJev:
    async def test_evaluate_with_jev_type(self, client, mock_mongodb):
        from app.evaluation.models import EvaluationResult, MetricResult

        mock_coll = mock_mongodb["evaluations"]

        mock_mongodb.__getitem__ = MagicMock(return_value=mock_coll)
        mock_coll.insert_one = AsyncMock(return_value=MagicMock(inserted_id="doc-1"))

        mock_result = EvaluationResult(
            scores={"quality": 1.0, "does_pass": 1.0, "groundedness": 0.99},
            metric_results=[
                MetricResult(name="quality", score=1.0, explanation="ok"),
            ],
            metadata={"evaluator": "jev"},
        )
        with patch("app.api.v1.evaluation._build_evaluator") as mock_build:
            mock_evaluator = AsyncMock()
            mock_evaluator.evaluate = AsyncMock(return_value=mock_result)
            mock_build.return_value = mock_evaluator
            response = await client.post(
                "/api/v1/evaluation/evaluate",
                json={
                    "config_id": "config-123",
                    "query": "What is Python?",
                    "answer": "A language.",
                    "contexts": ["Python is a language."],
                    "evaluator_type": "jev",
                },
            )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["metadata"]["evaluator"] == "jev"

    async def test_jev_compare_latest_404_without_artifacts(self, client, mock_mongodb):
        with patch("app.api.v1.evaluation._latest_compare_payload", return_value=None):
            response = await client.get("/api/v1/evaluation/jev-compare/latest")
        assert response.status_code == 404

    async def test_jev_compare_latest_ok(self, client, mock_mongodb):
        payload = {"mode": "mock/demo", "summaries": {"jev": {"agreement": 1.0}}}
        with patch(
            "app.api.v1.evaluation._latest_compare_payload", return_value=payload
        ):
            response = await client.get("/api/v1/evaluation/jev-compare/latest")
        assert response.status_code == 200
        assert response.json()["data"]["mode"] == "mock/demo"

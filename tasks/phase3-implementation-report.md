# Phase 3 Implementation Report

Date: 2026-04-09
Plan source: `tasks/v2-plan.md`

## Summary

Phase 3 adds evaluation and observability capabilities: a RAGAS-style evaluation framework, LLM-as-judge evaluator, evaluation API endpoints with MongoDB persistence, Langfuse integration for LLM tracing, and OpenTelemetry custom metrics.

## Implemented Deliverables

### 3.1 RAGAS Evaluation Framework

- Created `services/rag-service/app/evaluation/` package:
  - `models.py` — `MetricResult`, `EvaluationResult` (with `average_score()` helper), `EvaluationRun`, `EvaluationSummary`
  - `base.py` — `BaseEvaluator` ABC with `async evaluate()` method
  - `ragas_eval.py` — `RagasEvaluator` implementing 4 metrics via structured LLM prompts:
    - **faithfulness**: checks if answer claims are supported by context
    - **answer_relevancy**: checks if answer addresses the query
    - **context_precision**: checks if retrieved contexts are relevant
    - **context_recall**: checks if contexts cover ground truth (gracefully skipped when no ground_truth)
  - Each metric uses existing `BaseLLM` with temperature=0 for deterministic scoring
  - Robust JSON parsing with markdown fence stripping and score clamping to [0,1]

### 3.2 LLM-as-Judge Evaluator

- Created `services/rag-service/app/evaluation/judge.py`:
  - `JudgeEvaluator(BaseEvaluator)` with configurable judge LLM
  - 4 default rubrics: relevance, completeness, conciseness, accuracy
  - Custom rubrics support via constructor parameter
  - Single LLM call scoring all rubrics simultaneously

### 3.3 Evaluation API Endpoints

- Created `services/rag-service/app/api/v1/evaluation.py`:
  - `POST /api/v1/evaluation/evaluate` — run evaluation, persist results
  - `GET /api/v1/evaluation/{config_id}` — paginated evaluation history
  - `GET /api/v1/evaluation/{config_id}/summary` — aggregated metrics summary
- Created `services/rag-service/app/db/repositories/evaluation_repo.py`:
  - MongoDB CRUD for `evaluations` collection
  - Summary aggregation with 5-bucket score distribution
- Registered in `services/rag-service/app/api/v1/router.py`

### 3.4 Langfuse Integration

- Created `shared/python/rag_config_common/observability/langfuse.py`:
  - `setup_langfuse()` initializes global Langfuse client
  - `trace_llm_call()` context manager wraps LLM calls with generation spans
  - Graceful no-op via `_NoOpSpan` when langfuse is not installed
- Added `langfuse` and `langfuse-db` services to `docker-compose.yml` under `observability` profile
- Added `langfuse-db-data` volume

### 3.5 OTel Metrics (Prometheus Format)

- Created `shared/python/rag_config_common/observability/metrics.py`:
  - `rag_query_duration_seconds` (histogram)
  - `rag_retrieval_duration_seconds` (histogram)
  - `rag_llm_tokens_total` (counter with provider/type labels)
  - `rag_errors_total` (counter with service/error_type labels)
  - `rag_cache_hits_total` (counter with cache_type label)
  - `rag_evaluation_score` (histogram with metric_name label)
  - All no-op when OpenTelemetry is not installed
- Updated `shared/python/rag_config_common/observability/__init__.py` to export all utilities

### Dependencies

- `services/rag-service/requirements.txt`: added `langfuse>=2.0.0`
- `shared/python/pyproject.toml`: added `observability` optional deps group

## Verification

- **rag-service**: 401 tests passed (35 new evaluation tests + 366 existing)
- **config-service**: 35 passed — no regressions
- **gateway**: all packages passed
- `python -m compileall` clean on all new files

## Plan Checkpoint Comparison

| Checkpoint | Status |
|---|---|
| `POST /evaluate` returns RAGAS scores | DONE |
| `GET /evaluations/{config_id}/summary` returns aggregates | DONE |
| Langfuse dashboard shows LLM traces (if enabled) | DONE (optional profile) |
| OTel traces connect gateway -> service -> LLM call | DONE (via tracing.py + metrics.py) |
| Evaluation results persist in MongoDB `evaluations` collection | DONE |

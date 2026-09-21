# Jev-as-a-Judge vs LLM-as-Judge

Compare [TypeSafe Jev](https://docs.typesafe.ai/introduction) (a System One decision model) with the existing LLM-as-judge path on **fixed Naive RAG traces** from this product.

This is an observational harness for rag-configurator. It is **not** a safety certification, ASIL claim, or a general ranking of models.

## Why this exists

LangChain’s experiment [Jev-as-a-Judge for Agent Evals](https://www.langchain.com/blog/jev-agent-evals-langsmith) ([source](https://github.com/danielgshea/jev-as-a-judge)) showed that Jev can be faster, cheaper, and more repeatable than autoregressive LLM judges on frozen agent traces.

RAG Configurator already has:

- RAGAS-style metrics and an LLM rubric judge (`POST /api/v1/evaluation/evaluate`)
- Sandbox Evaluation dashboard

This work **extends** that surface: the same `(question, retrieved_chunks, answer)` state is scored by:

| Judge | Output |
| --- | --- |
| **Jev** | One `/v1/systemone` call with parallel `Score` (quality 1–5) + `Noul` (`does_pass`, groundedness) |
| **LLM baseline** | One structured JSON call with the **same rubric**: quality 1–5 + `does_pass` boolean |

Both run on the same committed fixtures, repeated K times, so only the judge can introduce variance.

## Fixtures

Committed dataset (7 Naive RAG cases with human `oracle_pass` / `oracle_quality`):

`services/rag-service/tests/fixtures/rag_eval_cases.json`

Recorded Jev HTTP payloads used for offline replay:

`services/rag-service/tests/fixtures/jev_recorded_responses.json`

Optional export from sandbox evaluation history (MongoDB):

```bash
python scripts/export_rag_eval_traces.py --out artifacts/jev-eval/exported_traces.json
```

Fill `oracle_pass` / `oracle_quality` on exported traces before using them as a labeled compare set.

## How to run

```bash
# Offline mock/demo — no API keys, CI-safe
make jev-eval-compare

# Equivalent
PYTHONPATH=services/rag-service python scripts/jev_eval_compare.py --mock
```

Writes:

- `artifacts/jev-eval/COMPARE_REPORT.md`
- `artifacts/jev-eval/results.csv`
- `artifacts/jev-eval/latest.json`

### Live compare (optional)

Requires `TYPESAFE_API_KEY` and either `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. Hard-stops when the USD **cost proxy** hits the cap (default `$2.00`).

```bash
export TYPESAFE_API_KEY=...
export OPENAI_API_KEY=...
export JEV_EVAL_LIVE=1
export JEV_EVAL_REPEATS=10          # default 10
export JEV_EVAL_USD_CAP=2.0         # default 2.0
make jev-eval-compare-live
```

If keys are missing, the script falls back to mock/demo and labels the report accordingly.

## Metrics

| Metric | Definition |
| --- | --- |
| **Agreement** | Fraction of binary `does_pass` decisions matching `oracle_pass` (or LLM majority if a case has no oracle) |
| **Repeatability** | P(two independent calls on the same frozen trace agree on `does_pass`), averaged over cases |
| **Signal value** | `agreement × repeatability` |
| **Mean quality variance** | Unbiased sample variance of the 1–5 quality score within each case, then averaged |
| **Latency p50 / p95** | End-to-end judge call time |
| **USD cost proxy** | Jev: billed input tokens at `$0.35 / 1M` (or `$0.00035/call` fallback from the LangChain experiment). LLM: published-ish input/output rates. Not an invoice. |

## Integration with rag-service

`POST /api/v1/evaluation/evaluate` accepts `evaluator_type`:

| Value | Behavior |
| --- | --- |
| `ragas` | Existing RAGAS-style metrics (default) |
| `judge` | Existing multi-rubric LLM judge (0–1 scores) |
| `quality` | New 1–5 + `does_pass` LLM judge (same rubric as Jev) |
| `jev` | TypeSafe Jev System One judge |

`GET /api/v1/evaluation/jev-compare/latest` returns the last compare summary from `artifacts/jev-eval/latest.json` (no provider calls). The gateway proxies `/api/v1/evaluation/*` to rag-service.

## Dependency

Jev is called over HTTP:

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer $TYPESAFE_API_KEY
```

Default model: `jev-latest`. `httpx` is the transport (already a rag-service dependency). The official [`typesafe-sdk`](https://pypi.org/project/typesafe-sdk/) package is **optional** and is not required for tests or the mock harness.

Never commit API keys. Set them in `.env` (see `.env.example`).

## Tests

```bash
cd services/rag-service && python -m pytest tests/test_jev_eval.py tests/test_evaluation.py -v
```

Live provider calls are not made in CI.

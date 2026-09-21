# Jev vs LLM-as-judge — RAG Configurator

Side-by-side comparison of TypeSafe Jev (System One) and an LLM-as-judge baseline on **fixed Naive RAG traces**. Inspired by LangChain’s [Jev-as-a-Judge for Agent Evals](https://www.langchain.com/blog/jev-agent-evals-langsmith) ([experiment repo](https://github.com/danielgshea/jev-as-a-judge)).

- **Mode:** `mock/demo`
- **Generated at:** 2026-09-21T08:17:33.923390+00:00
- **Cases:** 7
- **Repeats requested:** 10
- **USD cap:** $2.00
- **Observed cost (proxy):** $0.184888

> This report is a **mock/demo** replay. Jev responses come from recorded `/v1/systemone` fixtures (in-process; latency is a stand-in); the LLM baseline is a seeded simulator that still goes through the real JSON parser. It is illustrative of the harness, not a live TypeSafe/OpenAI measurement.

Numbers below are observational for this fixture set. They are **not** a general ranking of judges, a safety certification, or an ASIL claim.

## Metrics

| Judge | Model | Agreement | Repeatability | Signal value | Mean quality var | Latency p50 (ms) | Latency p95 (ms) | Cost USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jev | `jev-1.13.0` | 1.000 | 1.000 | 1.000 | 0.00000000 | 18.0 | 18.0 | $0.009887 |
| llm | `gpt-4o-mini-sim` | 0.814 | 0.831 | 0.677 | 0.08231143 | 277.0 | 332.4 | $0.175000 |

### What the columns mean

- **Agreement** — fraction of binary `does_pass` decisions that match the human `oracle_pass` label (or the LLM majority vote when a case has no oracle).
- **Repeatability** — chance that two independent calls on the same frozen trace return the same `does_pass` verdict, averaged over cases.
- **Signal value** — `agreement × repeatability`. Rewards judges that are both accurate and stable.
- **Mean quality var** — unbiased sample variance of the 1–5 quality score within each case, then averaged. Lower is more repeatable.
- **Cost USD** — proxy from token usage / published per-call figures, not a billing statement.

## Jev vs LLM on this product

- Quality-score variance: Jev variance was 0 on this run (identical repeats); LLM variance was 0.08231143.
- Mean latency: LLM was 15.5× Jev (278.9 ms vs 18.0 ms).
- Cost proxy: LLM was 17.7× Jev ($0.175000 vs $0.009887).
- Binary agreement: Jev 1.000, LLM 0.814.
- Signal value: Jev 1.000, LLM 0.677.

## Fixtures

| ID | Oracle pass | Oracle quality | Question |
| --- | --- | ---: | --- |
| `pto-allowance-grounded` | True | 5.0 | How many PTO days does a TechCorp employee with 1 year of tenure receive? |
| `pto-hallucinated-unlimited` | False | 1.0 | How many PTO days does a TechCorp employee with 1 year of tenure receive? |
| `remote-internet-partial` | False | 3.0 | What internet speed and stipend does TechCorp require for remote work? |
| `hmo-premium-grounded` | True | 5.0 | What is the employee monthly premium for the HMO medical plan? |
| `wrong-retrieval-architecture` | False | 1.0 | How many weeks of paid leave does a birth parent get at TechCorp? |
| `empty-context-fabricated` | False | 1.0 | What is TechCorp's parental leave for a birth parent? |
| `parental-leave-grounded` | True | 5.0 | What is TechCorp's parental leave for a birth parent? |

## How to re-run

```bash
# Offline mock/demo (no API keys)
make jev-eval-compare

# Live (requires TYPESAFE_API_KEY + OLLAMA_API_KEY for Ollama Cloud)
JEV_EVAL_LIVE=1 JEV_EVAL_USD_CAP=2.0 make jev-eval-compare-live
```

See [docs/jev-eval.md](../../docs/jev-eval.md) for details.

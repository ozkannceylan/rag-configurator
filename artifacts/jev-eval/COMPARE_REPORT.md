# Jev vs LLM-as-judge — RAG Configurator

Side-by-side comparison of TypeSafe Jev (System One) and an LLM-as-judge baseline on **fixed Naive RAG traces**. Inspired by LangChain’s [Jev-as-a-Judge for Agent Evals](https://www.langchain.com/blog/jev-agent-evals-langsmith) ([experiment repo](https://github.com/danielgshea/jev-as-a-judge)).

- **Mode:** `live`
- **Generated at:** 2026-09-21T18:35:16.620179+00:00
- **Cases:** 7
- **Repeats requested:** 10
- **USD cap:** $1.00
- **Observed cost (proxy):** $0.032100

Numbers below are observational for this fixture set. They are **not** a general ranking of judges, a safety certification, or an ASIL claim.

## Metrics

| Judge | Model | Valid calls | Error rate | Agreement | Repeatability | Signal value | Mean quality var | Latency p50 (ms) | Latency p95 (ms) | Cost USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jev | `jev-1.13.0` | 70/70 | 0.0% | 1.000 | 1.000 | 1.000 | 0.00020016 | 194.1 | 489.9 | $0.019197 |
| llm | `deepseek-v4-flash:0731` | 70/70 | 0.0% | 1.000 | 1.000 | 1.000 | 0.00000000 | 4357.3 | 8092.5 | $0.012903 |

### Quality axis vs the human labels

Ordinal accuracy and scale-fair repeatability. Raw variance is kept in the table above for continuity, but it is not comparable across judges that emit at different resolutions: a judge returning 4.98 and 4.87 shows variance where a judge constrained to integers shows none, for identical underlying stability. Read `Quantized var` and `Exact match` instead; both quantize to a common integer grid first.

| Judge | Labelled cases | MAE vs human | Spearman | Quantized var | Exact match |
| --- | ---: | ---: | ---: | ---: | ---: |
| jev | 7 | 0.255 | 0.926 | 0.000000 | 1.000 |
| llm | 7 | 0.143 | 1.000 | 0.000000 | 1.000 |

### Calibration of the pass probability

A probability is only useful for routing if it means what it says. Brier is the mean squared error against the truth: 0.25 is what you get by always guessing 0.5, so a judge that does not beat 0.25 is emitting a number with no information in it. ECE is the weighted gap between stated confidence and observed frequency. These decide whether a cascade can route its uncertain middle band on this signal, or whether the pass threshold is an arbitrary line.

| Judge | Brier (lower better) | ECE | Reliability bins |
| --- | ---: | ---: | ---: |
| jev | 0.0006 | 0.0211 | 2 |
| llm | 0.0000 | 0.0000 | 2 |

### What the columns mean

- **Valid calls / Error rate** — calls that produced a judgement rather than a failure. Errored calls are excluded from every metric below. A judge that is unavailable is not a judge that agrees.
- **Agreement** — fraction of binary `does_pass` decisions that match the human `oracle_pass` label (or the LLM majority vote when a case has no oracle).
- **Repeatability** — chance that two independent calls on the same frozen trace return the same `does_pass` verdict, averaged over cases.
- **Signal value** — `agreement × repeatability`. Rewards judges that are both accurate and stable.
- **Mean quality var** — unbiased sample variance of the 1–5 quality score within each case, then averaged. Lower is more repeatable.
- **Cost USD** — proxy from token usage / published per-call figures, not a billing statement.

## Jev vs LLM on this product

- Quality-score variance: LLM had 0.0× the Jev variance.
- Mean latency: LLM was 17.5× Jev (4742.4 ms vs 270.6 ms).
- Cost proxy: LLM was 0.7× Jev ($0.012903 vs $0.019197).
- Binary agreement: Jev 1.000, LLM 1.000.
- Signal value: Jev 1.000, LLM 1.000.

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

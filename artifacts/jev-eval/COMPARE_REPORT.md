# Jev vs LLM-as-judge — RAG Configurator

> ## ⚠️ These figures are withdrawn
>
> Recomputing this run from its own `results.csv` shows the headline
> comparison is an artifact of a bug, not a measurement.
>
> **6 of the LLM judge's 70 calls failed** with `json_decode` and were clamped
> to `quality=1.0` by the parse-failure fallback, then scored as judgements.
> All six landed on one case, `remote-internet-partial`, which is the *only*
> case contributing any LLM variance: its 0.266667 divided across 7 cases is
> exactly the 0.03809524 reported below.
>
> Excluding the failed calls, the four that succeeded all returned `2.0`:
>
> | Judge | Valid calls | Mean quality variance |
> | --- | ---: | ---: |
> | Jev | 70 / 70 | 0.00022429 |
> | LLM | 64 / 70 | **0.00000000** |
>
> So the LLM judge was perfectly repeatable on every call that succeeded,
> while Jev jittered on four of seven cases. **The claimed 169.9x variance
> advantage reverses.** The 1.000 agreement and repeatability figures come
> from the same mechanism: the case is `oracle_pass: False` and the failure
> fallback returns `does_pass=False`, so six API failures scored as six
> correct answers, deterministically.
>
> The likely trigger is `max_tokens=256` in the compare harness against a
> reasoning-style model, where the service's own API path uses 1024.
>
> **Fixed since:** errored calls are now excluded from every statistic and the
> report carries `Valid calls` and `Error rate` columns, so a failure rate can
> no longer hide. The comparison must be re-run with the baseline given
> structured output, a seed and a realistic token budget before any ratio is
> quoted again. See `tasks/JEV_JUDGE_V2_PLAN.md`.
>
> The original report is kept below unchanged, for the record.

---


Side-by-side comparison of TypeSafe Jev (System One) and an LLM-as-judge baseline on **fixed Naive RAG traces**. Inspired by LangChain’s [Jev-as-a-Judge for Agent Evals](https://www.langchain.com/blog/jev-agent-evals-langsmith) ([experiment repo](https://github.com/danielgshea/jev-as-a-judge)).

- **Mode:** `live`
- **Generated at:** 2026-09-21T08:20:23.712563+00:00
- **Cases:** 7
- **Repeats requested:** 10
- **USD cap:** $2.00
- **Observed cost (proxy):** $0.025792

Numbers below are observational for this fixture set. They are **not** a general ranking of judges, a safety certification, or an ASIL claim.

## Metrics

| Judge | Model | Agreement | Repeatability | Signal value | Mean quality var | Latency p50 (ms) | Latency p95 (ms) | Cost USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jev | `jev-1.13.0` | 1.000 | 1.000 | 1.000 | 0.00022429 | 226.5 | 556.9 | $0.016086 |
| llm | `deepseek-v4-flash:0731` | 1.000 | 1.000 | 1.000 | 0.03809524 | 4180.0 | 6728.7 | $0.009706 |

### What the columns mean

- **Agreement** — fraction of binary `does_pass` decisions that match the human `oracle_pass` label (or the LLM majority vote when a case has no oracle).
- **Repeatability** — chance that two independent calls on the same frozen trace return the same `does_pass` verdict, averaged over cases.
- **Signal value** — `agreement × repeatability`. Rewards judges that are both accurate and stable.
- **Mean quality var** — unbiased sample variance of the 1–5 quality score within each case, then averaged. Lower is more repeatable.
- **Cost USD** — proxy from token usage / published per-call figures, not a billing statement.

## Jev vs LLM on this product

- Quality-score variance: LLM had 169.9× the Jev variance.
- Mean latency: LLM was 15.3× Jev (4472.3 ms vs 293.2 ms).
- Cost proxy: LLM was 0.6× Jev ($0.009706 vs $0.016086).
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

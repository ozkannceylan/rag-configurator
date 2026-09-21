# Jev live re-run — handoff

Everything needed for an honest re-measurement is committed. This environment
has no Jev key, so the live run has not been executed. Run it where the key
is available and paste the three artifacts back.

Background: `tasks/JEV_JUDGE_V2_PLAN.md`. The short version is that the first
published comparison was wrong, the harness has been corrected, and the point
of this run is to find out what is actually true.

## What changed since the numbers you have

| Was | Now |
| --- | --- |
| Failed calls scored as verdicts | Excluded from every statistic, reported as `error_rate` |
| `max_tokens=256` | `1024`, matching the service's own API path |
| No structured output | `response_format: json_object`, with graceful fallback |
| No seed | `seed=7` by default, plumbed through the client |
| `finish_reason` discarded | Recorded on every verdict |
| No retry on a parse failure | One retry before it counts as an error |
| Unlabelled case scored against the LLM's own majority | Excluded from agreement |
| USD cap fired after overspending, mid-case | Stops before, at case granularity |
| Mock overwrote the live artifacts | Mock writes to `artifacts/jev-eval/mock/` |
| `--live` without keys fell through to mock, exit 0 | Exits 2, writes nothing |
| Raw variance only | Plus quantized variance, exact match, MAE and Spearman vs human labels, Brier, ECE, reliability bins |
| Rubric conflated omission with contradiction | Explicit precedence rule, contradiction caps quality at 2 |

## Run it

```bash
pip install -e shared/python
pip install -r services/rag-service/requirements.txt

export TYPESAFE_API_KEY=...        # never commit this
export OLLAMA_API_KEY=...          # Ollama Cloud, OpenAI-compatible

# Sanity check first: costs one call per judge, proves the wiring works.
JEV_EVAL_LIVE=1 JEV_EVAL_REPEATS=1 JEV_EVAL_USD_CAP=0.10 \
  make jev-eval-compare-live

# Full run. The previous live run cost $0.026, so this cap is generous.
JEV_EVAL_LIVE=1 JEV_EVAL_REPEATS=10 JEV_EVAL_USD_CAP=1.00 \
  make jev-eval-compare-live
```

Artifacts land in `artifacts/jev-eval/`: `COMPARE_REPORT.md`, `results.csv`,
`latest.json`. Send back all three. `results.csv` matters most, because every
claim in the report can be recomputed from it, which is how the original bug
was found.

## Check these before trusting the output

1. **`Error rate` is 0.0% for both judges.** This is the whole point of the
   structured-output and token-budget changes. If the LLM still fails, read
   `finish_reason` in `results.csv`. `"length"` means raise `max_tokens`
   further. Anything else means the provider rejected `response_format`, and
   the log will say the judge degraded to plain prompting.
2. **The report header says `Mode: live`.** If it says mock, the keys were not
   picked up and the run should have exited 2. Report that as a bug.
3. **`Valid calls` is `70/70` for both.**
4. **Nothing landed in `artifacts/jev-eval/mock/`.**

## What the run is actually asking

Read these four, in this order. The first two are where Jev's case stands or
falls; the ratio that used to be the headline is now the least interesting.

- **`Error rate` and `Valid calls`.** A typed judge cannot return "unparseable".
  The baseline can. This is the honest, structural advantage and it does not
  depend on how anyone configured anything.
- **Brier and ECE on the pass probability.** Brier must beat 0.25 or the Noul
  carries no information and the cascade in the plan cannot be built on it.
  If it beats 0.25, read the reliability bins in `latest.json` to find where
  the judge is genuinely unsure, and set `JevRelevanceGrader(uncertainty_band=...)`
  from that, not from a guess.
- **MAE and Spearman vs the human labels.** On the old run Jev scored 0.304
  against the baseline's 0.143, which is a real weakness. The rubric now has a
  contradiction precedence rule, so this is the number that says whether the
  rubric was the problem. Expect Jev to improve. If it does not, the rubric is
  not the explanation and the plan's section on fixture quality is next.
- **Quantized variance and exact match, not raw variance.** Raw variance
  punishes Jev for emitting at finer resolution than the integer rubric the
  baseline is held to. On the committed data both judges are at 0.0 and 1.000
  once quantized. Repeatability is a tie; do not re-publish it as a win.

## One case needs a human, not a judge

`remote-internet-partial` is flagged `oracle_quality_disputed` in the fixture.
The answer says `$100` where the chunk says `$50`, and "without receipts"
where the chunk requires one. That is a contradiction, not an omission, so the
human label of 3 conflicts with the rubric's own wording. Two annotators should
re-adjudicate it against the current rubric before it is used to score anyone
on the 1-5 axis. `oracle_pass=False` is undisputed and every judge agrees.

Do not adjust that label to make a judge look better. The whole reason the
first result was wrong is that nobody checked the numbers against the data.

## After the run

- If the error rate is 0.0%, replace the withdrawal notice at the top of
  `COMPARE_REPORT.md` with the corrected figures and say plainly what changed
  and why. The story that the baseline was failing 8.6% of calls, silently, is
  a better engineering result than the original claim and it survives scrutiny.
- If Brier beats 0.25, set the grader's uncertainty band and the cascade in
  `tasks/JEV_JUDGE_V2_PLAN.md` Part 3 becomes buildable.
- Either way the fixture set is still saturated at 7 cases, both judges scored
  1.000 on the binary axis, and no comparative claim should outrun that.

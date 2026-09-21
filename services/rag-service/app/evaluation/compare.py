"""Compare Jev vs LLM judges on a frozen RAG eval dataset."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.evaluation.verdict import JudgeVerdict

JudgeFn = Callable[[str, list[str], str], Awaitable[JudgeVerdict]]


@dataclass
class EvalCase:
    """One frozen RAG trace."""

    id: str
    question: str
    retrieved_chunks: list[str]
    answer: str
    oracle_pass: bool | None = None
    oracle_quality: float | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "retrieved_chunks": self.retrieved_chunks,
            "answer": self.answer,
            "oracle_pass": self.oracle_pass,
            "oracle_quality": self.oracle_quality,
            "notes": self.notes,
        }


@dataclass
class RepeatRecord:
    case_id: str
    repeat: int
    verdict: JudgeVerdict


@dataclass
class JudgeSummary:
    judge: str
    model: str
    n_calls: int
    n_valid: int
    error_rate: float
    agreement: float
    mean_quality_variance: float
    binary_repeatability: float
    signal_value: float
    latency_p50_ms: float
    latency_p95_ms: float
    mean_latency_ms: float
    total_cost_usd: float
    mean_cost_usd: float
    mean_quality: float
    pass_rate: float
    notes: str = ""


@dataclass
class CompareResult:
    mode: str
    repeats: int
    generated_at: str
    cases: list[EvalCase]
    records: dict[str, list[RepeatRecord]] = field(default_factory=dict)
    summaries: dict[str, JudgeSummary] = field(default_factory=dict)
    stopped_reason: str | None = None
    usd_cap: float = 2.0
    total_cost_usd: float = 0.0

    def to_latest_json(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "repeats": self.repeats,
            "generated_at": self.generated_at,
            "usd_cap": self.usd_cap,
            "total_cost_usd": self.total_cost_usd,
            "stopped_reason": self.stopped_reason,
            "case_ids": [c.id for c in self.cases],
            "summaries": {
                name: summary.__dict__ for name, summary in self.summaries.items()
            },
        }


def load_eval_cases(path: Path) -> list[EvalCase]:
    """Load the committed JSON fixture file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_cases = data["cases"] if isinstance(data, dict) else data
    cases: list[EvalCase] = []
    for item in raw_cases:
        chunks = item.get("retrieved_chunks") or item.get("contexts") or []
        if isinstance(chunks, str):
            chunks = [chunks]
        oracle_pass = item.get("oracle_pass")
        if oracle_pass is not None:
            oracle_pass = bool(oracle_pass)
        oracle_quality = item.get("oracle_quality")
        if oracle_quality is not None:
            oracle_quality = float(oracle_quality)
        cases.append(
            EvalCase(
                id=str(item["id"]),
                question=str(item["question"]),
                retrieved_chunks=[str(c) for c in chunks],
                answer=str(item["answer"]),
                oracle_pass=oracle_pass,
                oracle_quality=oracle_quality,
                notes=str(item.get("notes") or ""),
            )
        )
    if len(cases) < 1:
        raise ValueError(f"No eval cases found in {path}")
    return cases


def default_cases_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "rag_eval_cases.json"
    )


def percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def sample_variance(values: Sequence[float]) -> float:
    nums = [float(v) for v in values]
    if len(nums) < 2:
        return 0.0
    return statistics.variance(nums)


def pairwise_repeatability(flags: Sequence[bool]) -> float:
    """P(two independent draws on this case return the same verdict)."""
    if not flags:
        return 0.0
    p = sum(1 for f in flags if f) / len(flags)
    return p * p + (1.0 - p) * (1.0 - p)


def majority_bool(flags: Sequence[bool]) -> bool:
    if not flags:
        return False
    return sum(1 for f in flags if f) >= math.ceil(len(flags) / 2)


def _oracle_or_reference(
    cases: Sequence[EvalCase],
    records_by_judge: dict[str, list[RepeatRecord]],
    llm_judge: str = "llm",
) -> dict[str, bool]:
    """Per-case binary reference: human oracle, else LLM majority."""
    llm_records = records_by_judge.get(llm_judge, [])
    llm_by_case: dict[str, list[bool]] = {}
    for rec in llm_records:
        llm_by_case.setdefault(rec.case_id, []).append(rec.verdict.does_pass)

    reference: dict[str, bool] = {}
    for case in cases:
        if case.oracle_pass is not None:
            reference[case.id] = bool(case.oracle_pass)
        elif case.id in llm_by_case:
            reference[case.id] = majority_bool(llm_by_case[case.id])
        else:
            # Fall back to majority across all judges if LLM is missing.
            flags: list[bool] = []
            for recs in records_by_judge.values():
                flags.extend(r.verdict.does_pass for r in recs if r.case_id == case.id)
            reference[case.id] = majority_bool(flags)
    return reference


def summarize_judge(
    judge: str,
    records: Sequence[RepeatRecord],
    cases: Sequence[EvalCase],
    reference: dict[str, bool],
) -> JudgeSummary:
    by_case: dict[str, list[RepeatRecord]] = {}
    for rec in records:
        by_case.setdefault(rec.case_id, []).append(rec)

    qualities: list[float] = []
    latencies: list[float] = []
    costs: list[float] = []
    pass_flags: list[bool] = []
    agreements: list[float] = []
    variances: list[float] = []
    repeatabilities: list[float] = []
    models: list[str] = []

    n_valid = 0
    n_skipped_cases = 0

    for case in cases:
        all_recs = by_case.get(case.id, [])
        # A call that errored is not a judgement. Scoring it as one is how a
        # parse failure or a timeout becomes a confident verdict: the failure
        # fallback returns does_pass=False, which is "correct" on every
        # fail-labelled case, and it is deterministic, which reads as perfect
        # repeatability. Exclude invalid records from every statistic and
        # report the error rate separately instead.
        case_recs = [r for r in all_recs if r.verdict.is_valid]
        n_valid += len(case_recs)
        if not case_recs:
            n_skipped_cases += 1
            continue

        case_quality = [r.verdict.quality for r in case_recs]
        case_pass = [r.verdict.does_pass for r in case_recs]
        qualities.extend(case_quality)
        pass_flags.extend(case_pass)
        latencies.extend(r.verdict.latency_ms for r in case_recs)
        costs.extend(r.verdict.cost_usd for r in case_recs)
        models.extend(r.verdict.model for r in case_recs if r.verdict.model)
        # Variance and repeatability are undefined for a single observation.
        # Averaging a placeholder 0.0 in would understate both.
        if len(case_recs) >= 2:
            variances.append(sample_variance(case_quality))
            repeatabilities.append(pairwise_repeatability(case_pass))
        else:
            n_skipped_cases += 1
        expected = reference.get(case.id)
        if expected is None:
            continue
        agreements.extend(1.0 if flag == expected else 0.0 for flag in case_pass)

    model = Counter(models).most_common(1)[0][0] if models else judge
    agreement = statistics.mean(agreements) if agreements else 0.0
    mean_var = statistics.mean(variances) if variances else 0.0
    binary_rep = statistics.mean(repeatabilities) if repeatabilities else 0.0
    return JudgeSummary(
        judge=judge,
        model=model,
        n_calls=len(records),
        n_valid=n_valid,
        error_rate=(1.0 - n_valid / len(records)) if records else 0.0,
        agreement=agreement,
        mean_quality_variance=mean_var,
        binary_repeatability=binary_rep,
        signal_value=agreement * binary_rep,
        latency_p50_ms=percentile(latencies, 0.50),
        latency_p95_ms=percentile(latencies, 0.95),
        mean_latency_ms=statistics.mean(latencies) if latencies else 0.0,
        total_cost_usd=sum(costs),
        mean_cost_usd=statistics.mean(costs) if costs else 0.0,
        mean_quality=statistics.mean(qualities) if qualities else 0.0,
        pass_rate=(
            sum(1 for f in pass_flags if f) / len(pass_flags) if pass_flags else 0.0
        ),
        notes=(
            f"{n_skipped_cases} case(s) excluded from variance/repeatability "
            "for having fewer than 2 valid calls"
            if n_skipped_cases
            else ""
        ),
    )


async def run_compare(
    cases: Sequence[EvalCase],
    judges: dict[str, JudgeFn],
    *,
    repeats: int = 10,
    usd_cap: float = 2.0,
    mode: str = "live",
) -> CompareResult:
    """Run each judge on every case ``repeats`` times. Stops if USD cap is hit."""
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    result = CompareResult(
        mode=mode,
        repeats=repeats,
        generated_at=datetime.now(UTC).isoformat(),
        cases=list(cases),
        usd_cap=usd_cap,
    )
    spent = 0.0
    stopped = False
    for repeat in range(1, repeats + 1):
        if stopped:
            break
        for case in cases:
            if stopped:
                break
            for name, judge_fn in judges.items():
                if spent >= usd_cap:
                    result.stopped_reason = (
                        f"USD cap {usd_cap:.2f} reached after ${spent:.4f}"
                    )
                    stopped = True
                    break
                verdict = await judge_fn(
                    case.question, case.retrieved_chunks, case.answer
                )
                spent += float(verdict.cost_usd or 0.0)
                result.records.setdefault(name, []).append(
                    RepeatRecord(case_id=case.id, repeat=repeat, verdict=verdict)
                )
    result.total_cost_usd = spent
    llm_name = "llm" if "llm" in result.records else next(iter(result.records), "llm")
    reference = _oracle_or_reference(cases, result.records, llm_judge=llm_name)
    for name, recs in result.records.items():
        result.summaries[name] = summarize_judge(name, recs, cases, reference)
    return result


def write_results_csv(result: CompareResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "judge",
        "case_id",
        "repeat",
        "quality",
        "does_pass",
        "groundedness",
        "latency_ms",
        "cost_usd",
        "model",
        "does_pass_probability",
        "oracle_pass",
        "valid",
        "error",
    ]
    oracle_by_case = {c.id: c.oracle_pass for c in result.cases}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for name, recs in result.records.items():
            for rec in recs:
                row = rec.verdict.as_row()
                writer.writerow(
                    {
                        "judge": name,
                        "case_id": rec.case_id,
                        "repeat": rec.repeat,
                        "quality": f"{row['quality']:.6f}",
                        "does_pass": row["does_pass"],
                        "groundedness": f"{row['groundedness']:.6f}",
                        "latency_ms": f"{row['latency_ms']:.3f}",
                        "cost_usd": f"{row['cost_usd']:.8f}",
                        "model": row["model"],
                        "does_pass_probability": row["does_pass_probability"],
                        "oracle_pass": oracle_by_case.get(rec.case_id, ""),
                        "valid": int(rec.verdict.is_valid),
                        "error": row["error"] or "",
                    }
                )


def render_compare_report(result: CompareResult) -> str:
    """Markdown report for artifacts/jev-eval/COMPARE_REPORT.md."""
    lines: list[str] = []
    lines.append("# Jev vs LLM-as-judge — RAG Configurator")
    lines.append("")
    lines.append(
        "Side-by-side comparison of TypeSafe Jev (System One) and an LLM-as-judge "
        "baseline on **fixed Naive RAG traces**. Inspired by LangChain’s "
        "[Jev-as-a-Judge for Agent Evals](https://www.langchain.com/blog/jev-agent-evals-langsmith) "
        "([experiment repo](https://github.com/danielgshea/jev-as-a-judge))."
    )
    lines.append("")
    lines.append(f"- **Mode:** `{result.mode}`")
    lines.append(f"- **Generated at:** {result.generated_at}")
    lines.append(f"- **Cases:** {len(result.cases)}")
    lines.append(f"- **Repeats requested:** {result.repeats}")
    lines.append(f"- **USD cap:** ${result.usd_cap:.2f}")
    lines.append(f"- **Observed cost (proxy):** ${result.total_cost_usd:.6f}")
    if result.stopped_reason:
        lines.append(f"- **Stopped early:** {result.stopped_reason}")
    lines.append("")
    if result.mode.startswith("mock"):
        lines.append(
            "> This report is a **mock/demo** replay. Jev responses come from "
            "recorded `/v1/systemone` fixtures (in-process; latency is a stand-in); "
            "the LLM baseline is a seeded simulator that still goes through the "
            "real JSON parser. It is illustrative of the harness, not a live "
            "TypeSafe/OpenAI measurement."
        )
        lines.append("")
    lines.append(
        "Numbers below are observational for this fixture set. They are **not** "
        "a general ranking of judges, a safety certification, or an ASIL claim."
    )
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append(
        "| Judge | Model | Valid calls | Error rate | Agreement | Repeatability | "
        "Signal value | Mean quality var | Latency p50 (ms) | Latency p95 (ms) | "
        "Cost USD |"
    )
    lines.append(
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for name in sorted(result.summaries):
        s = result.summaries[name]
        lines.append(
            f"| {name} | `{s.model}` | {s.n_valid}/{s.n_calls} | "
            f"{s.error_rate:.1%} | {s.agreement:.3f} | "
            f"{s.binary_repeatability:.3f} | {s.signal_value:.3f} | "
            f"{s.mean_quality_variance:.8f} | {s.latency_p50_ms:.1f} | "
            f"{s.latency_p95_ms:.1f} | ${s.total_cost_usd:.6f} |"
        )
    lines.append("")
    lines.append("### What the columns mean")
    lines.append("")
    lines.append(
        "- **Valid calls / Error rate** — calls that produced a judgement "
        "rather than a failure. Errored calls are excluded from every metric "
        "below. A judge that is unavailable is not a judge that agrees.\n"
        "- **Agreement** — fraction of binary `does_pass` decisions that match "
        "the human `oracle_pass` label (or the LLM majority vote when a case "
        "has no oracle)."
    )
    lines.append(
        "- **Repeatability** — chance that two independent calls on the same "
        "frozen trace return the same `does_pass` verdict, averaged over cases."
    )
    lines.append(
        "- **Signal value** — `agreement × repeatability`. Rewards judges that "
        "are both accurate and stable."
    )
    lines.append(
        "- **Mean quality var** — unbiased sample variance of the 1–5 quality "
        "score within each case, then averaged. Lower is more repeatable."
    )
    lines.append(
        "- **Cost USD** — proxy from token usage / published per-call figures, "
        "not a billing statement."
    )
    lines.append("")
    if "jev" in result.summaries and "llm" in result.summaries:
        jev = result.summaries["jev"]
        llm = result.summaries["llm"]
        lines.append("## Jev vs LLM on this product")
        lines.append("")
        if jev.mean_quality_variance > 0:
            ratio = llm.mean_quality_variance / jev.mean_quality_variance
            lines.append(
                f"- Quality-score variance: LLM had {ratio:.1f}× the Jev variance."
            )
        else:
            lines.append(
                "- Quality-score variance: Jev variance was 0 on this run "
                f"(identical repeats); LLM variance was {llm.mean_quality_variance:.8f}."
            )
        if jev.mean_latency_ms > 1.0:
            lat_ratio = llm.mean_latency_ms / jev.mean_latency_ms
            lines.append(
                f"- Mean latency: LLM was {lat_ratio:.1f}× Jev "
                f"({llm.mean_latency_ms:.1f} ms vs {jev.mean_latency_ms:.1f} ms)."
            )
        else:
            lines.append(
                f"- Mean latency: Jev {jev.mean_latency_ms:.1f} ms, "
                f"LLM {llm.mean_latency_ms:.1f} ms."
            )
        if jev.total_cost_usd > 0:
            cost_ratio = llm.total_cost_usd / jev.total_cost_usd
            lines.append(
                f"- Cost proxy: LLM was {cost_ratio:.1f}× Jev "
                f"(${llm.total_cost_usd:.6f} vs ${jev.total_cost_usd:.6f})."
            )
        lines.append(
            f"- Binary agreement: Jev {jev.agreement:.3f}, LLM {llm.agreement:.3f}."
        )
        lines.append(
            f"- Signal value: Jev {jev.signal_value:.3f}, LLM {llm.signal_value:.3f}."
        )
        lines.append("")
    lines.append("## Fixtures")
    lines.append("")
    lines.append("| ID | Oracle pass | Oracle quality | Question |")
    lines.append("| --- | --- | ---: | --- |")
    for case in result.cases:
        oracle = "—" if case.oracle_pass is None else str(case.oracle_pass)
        oq = "—" if case.oracle_quality is None else f"{case.oracle_quality:.1f}"
        q = case.question.replace("|", "/").replace("\n", " ")
        if len(q) > 80:
            q = q[:77] + "..."
        lines.append(f"| `{case.id}` | {oracle} | {oq} | {q} |")
    lines.append("")
    lines.append("## How to re-run")
    lines.append("")
    lines.append("```bash")
    lines.append("# Offline mock/demo (no API keys)")
    lines.append("make jev-eval-compare")
    lines.append("")
    lines.append("# Live (requires TYPESAFE_API_KEY + OLLAMA_API_KEY for Ollama Cloud)")
    lines.append("JEV_EVAL_LIVE=1 JEV_EVAL_USD_CAP=2.0 make jev-eval-compare-live")
    lines.append("```")
    lines.append("")
    lines.append("See [docs/jev-eval.md](../../docs/jev-eval.md) for details.")
    lines.append("")
    return "\n".join(lines)


def write_artifacts(result: CompareResult, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "COMPARE_REPORT.md"
    csv_path = out_dir / "results.csv"
    latest_path = out_dir / "latest.json"
    report_path.write_text(render_compare_report(result), encoding="utf-8")
    write_results_csv(result, csv_path)
    latest_path.write_text(
        json.dumps(result.to_latest_json(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"report": report_path, "csv": csv_path, "latest": latest_path}

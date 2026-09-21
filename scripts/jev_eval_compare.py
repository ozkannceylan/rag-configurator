#!/usr/bin/env python3
"""Compare TypeSafe Jev vs an LLM-as-judge baseline on frozen RAG traces.

Default is a CI-safe mock/demo using recorded Jev fixtures. Live calls require
JEV_EVAL_LIVE=1 plus API keys, and stop at JEV_EVAL_USD_CAP (default 2.0).

Examples:
  PYTHONPATH=services/rag-service python scripts/jev_eval_compare.py --mock
  JEV_EVAL_LIVE=1 PYTHONPATH=services/rag-service python scripts/jev_eval_compare.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAG_SERVICE = ROOT / "services" / "rag-service"
if str(RAG_SERVICE) not in sys.path:
    sys.path.insert(0, str(RAG_SERVICE))

from app.evaluation.compare import (  # noqa: E402
    default_cases_path,
    load_eval_cases,
    run_compare,
    write_artifacts,
)
from app.evaluation.mock_judges import (
    SimulatedLLMJudge,
    recorded_jev_judge,
)  # noqa: E402


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _build_live_llm_judge():
    """LLM baseline for live compare: Ollama Cloud OpenAI-compat, not OpenAI/Anthropic."""
    from app.evaluation.ollama_cloud import build_ollama_cloud_quality_judge

    return build_ollama_cloud_quality_judge()


def _build_live_jev_judge():
    from app.evaluation.jev_judge import JevJudge

    if not os.environ.get("TYPESAFE_API_KEY"):
        return None
    return JevJudge()


async def _main_async(args: argparse.Namespace) -> int:
    cases_path = Path(args.cases) if args.cases else default_cases_path()
    cases = load_eval_cases(cases_path)
    live = bool(args.live) or _env_flag("JEV_EVAL_LIVE")
    repeats = args.repeats or _env_int("JEV_EVAL_REPEATS", 10)
    usd_cap = (
        args.usd_cap
        if args.usd_cap is not None
        else _env_float("JEV_EVAL_USD_CAP", 2.0)
    )
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "artifacts" / "jev-eval"

    judges = {}
    mode = "mock/demo"
    if live and not args.mock:
        jev = _build_live_jev_judge()
        llm = _build_live_llm_judge()
        missing = []
        if jev is None:
            missing.append("TYPESAFE_API_KEY")
        if llm is None:
            missing.append("OLLAMA_API_KEY (Ollama Cloud OpenAI-compat)")
        if missing:
            # Never silently downgrade a live run to a simulation. This used to
            # fall through to mock and exit 0, which in a scripted release
            # would overwrite the published artifacts with synthetic numbers.
            print(
                "ERROR: live compare requested but missing: "
                + ", ".join(missing)
                + ".\nRefusing to fall back to mock, because that would write "
                "simulated numbers where real ones are expected.\n"
                "Export the keys, or run explicitly with --mock.",
                file=sys.stderr,
            )
            return 2
        else:
            judges = {
                "jev": jev.judge_trace,
                "llm": llm.judge_trace,
            }
            mode = "live"

    if not live or args.mock:
        jev = recorded_jev_judge(cases, reported_latency_ms=18.0)
        llm = SimulatedLLMJudge(cases)
        judges = {"jev": jev.judge_trace, "llm": llm.judge_trace}
        mode = "mock/demo"

    result = await run_compare(
        cases,
        judges,
        repeats=repeats,
        usd_cap=usd_cap,
        mode=mode,
    )
    # A mock run must never overwrite a live one. The published report and
    # latest.json disagreed by three minutes for exactly this reason: a mock
    # run landed on top of a live one and the API then served the mock.
    if not str(result.mode).startswith("live"):
        out_dir = out_dir / "mock"
    paths = write_artifacts(result, out_dir)
    print(
        f"mode={result.mode} cases={len(cases)} repeats={repeats} cost=${result.total_cost_usd:.6f}"
    )
    for name, summary in result.summaries.items():
        print(
            f"{name}: agreement={summary.agreement:.3f} "
            f"repeatability={summary.binary_repeatability:.3f} "
            f"signal={summary.signal_value:.3f} "
            f"var={summary.mean_quality_variance:.8f} "
            f"p50={summary.latency_p50_ms:.1f}ms "
            f"cost=${summary.total_cost_usd:.6f}"
        )
    print(f"wrote {paths['report']}")
    print(f"wrote {paths['csv']}")
    print(f"wrote {paths['latest']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        help="Path to rag_eval_cases.json (default: rag-service test fixtures)",
    )
    parser.add_argument(
        "--repeats", type=int, default=None, help="K repeats (default 10)"
    )
    parser.add_argument(
        "--usd-cap", type=float, default=None, help="Hard USD cost proxy cap"
    )
    parser.add_argument(
        "--out-dir",
        help="Artifact directory (default: artifacts/jev-eval)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force recorded/mock judges even if live keys are present",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call TypeSafe + LLM providers (same as JEV_EVAL_LIVE=1)",
    )
    args = parser.parse_args()
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())

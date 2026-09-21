#!/usr/bin/env python3
"""Export persisted sandbox/RAG evaluation traces to a Jev compare fixture.

Reads the MongoDB ``evaluations`` collection (written by POST /evaluation/evaluate)
and writes a JSON file with question, retrieved_chunks, answer, and optional
oracle fields left blank for human labeling.

    python scripts/export_rag_eval_traces.py --out services/rag-service/tests/fixtures/exported_traces.json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _extract_case(doc: dict, index: int) -> dict:
    results = doc.get("results") or {}
    metadata = results.get("metadata") or {}
    case_id = str(doc.get("id") or doc.get("_id") or f"eval-{index}")
    return {
        "id": case_id,
        "question": doc.get("query") or "",
        "retrieved_chunks": list(doc.get("contexts") or []),
        "answer": doc.get("answer") or "",
        "oracle_pass": None,
        "oracle_quality": None,
        "notes": f"exported from evaluations; evaluator={metadata.get('evaluator', 'unknown')}",
        "source": {
            "config_id": doc.get("config_id"),
            "created_at": str(doc.get("created_at") or ""),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mongodb-uri",
        default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("MONGODB_DATABASE", "rag_configurator"),
    )
    parser.add_argument("--config-id", default=None, help="Optional config_id filter")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument(
        "--out",
        default="artifacts/jev-eval/exported_traces.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise SystemExit(
            "pymongo is required for trace export. Install rag-service requirements."
        ) from exc

    client = MongoClient(args.mongodb_uri, serverSelectionTimeoutMS=4000)
    try:
        client.admin.command("ping")
    except Exception as exc:
        raise SystemExit(f"MongoDB is not reachable at {args.mongodb_uri}: {exc}") from exc

    coll = client[args.database]["evaluations"]
    query = {}
    if args.config_id:
        query["config_id"] = args.config_id
    cursor = coll.find(query).sort("created_at", -1).limit(args.limit)
    cases = [_extract_case(doc, i) for i, doc in enumerate(cursor, start=1)]
    payload = {
        "version": 1,
        "description": "Exported RAG evaluation traces. Fill oracle_pass / oracle_quality before compare.",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(cases),
        "cases": cases,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"exported {len(cases)} traces -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

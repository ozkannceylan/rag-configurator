#!/usr/bin/env python
"""Backfill v2 config defaults into existing MongoDB pipeline configs."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from pymongo import MongoClient

from rag_config_common.models.config import (
    CacheConfig,
    ChunkingConfig,
    EvaluationConfig,
    GuardrailsConfig,
    RBACConfig,
)


def build_updates(config: dict) -> dict:
    """Return the v2 defaults missing from a legacy config document."""
    updates: dict[str, object] = {}

    if "version" not in config or str(config.get("version", "")).startswith("1."):
        updates["version"] = "2.0.0"
    if "rbac" not in config:
        updates["rbac"] = RBACConfig().model_dump()
    if "guardrails" not in config:
        updates["guardrails"] = GuardrailsConfig().model_dump()
    if "chunking" not in config:
        updates["chunking"] = ChunkingConfig().model_dump()
    if "evaluation" not in config:
        updates["evaluation"] = EvaluationConfig().model_dump()
    if "cache" not in config:
        updates["cache"] = CacheConfig().model_dump()

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)

    return updates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mongodb-uri",
        default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
        help="MongoDB connection string",
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("MONGODB_DATABASE", "rag_configurator"),
        help="MongoDB database name",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned updates without writing them",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = MongoClient(args.mongodb_uri)
    collection = client[args.database]["configs"]

    migrated = 0
    examined = 0

    try:
        for config in collection.find({}):
            examined += 1
            updates = build_updates(config)
            if not updates:
                continue

            migrated += 1
            config_id = str(config.get("_id"))
            if args.dry_run:
                print(f"[dry-run] would update {config_id}: {sorted(updates.keys())}")
                continue

            collection.update_one({"_id": config["_id"]}, {"$set": updates})
            print(f"updated {config_id}: {sorted(updates.keys())}")
    finally:
        client.close()

    print(f"examined={examined} migrated={migrated} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

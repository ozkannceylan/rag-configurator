# Lessons

Project-specific lessons and recurring correction patterns belong here.

## Active Lessons

- No project-specific lessons have been captured yet.

## Update Rule

- After a user correction, add the mistake pattern and the rule that should prevent it next time.

---

## 2026-09-21 — Lint autofix vs. re-export shims

**Never run `ruff check --fix` with F401 enabled across a codebase that uses
re-export shim modules.** Ruff judges an import unused from inside one file. It
cannot see that `app/core/auth.py` exists precisely so the API layer can import
`get_authenticated_user_id` from one stable local path instead of reaching into
`rag_config_common`. The autofix deleted the module's entire reason for
existing in all three services at once, and nothing failed until import time.

Two guards:

1. Declare `__all__` in any module whose job is to re-export. It satisfies
   ruff, documents the public surface, and survives future autofixes.
   `# noqa: F401` is the weaker fallback; a blanket per-file ignore on a
   non-`__init__` module is the wrong tool.
2. After any bulk lint autofix, run `python -c "import app.main"` per service
   **before** running the tests. The import check catches breakage in a module
   no test happens to reach.

**A green linter says nothing about whether the code runs.** `ruff check` and
`black --check` both reported clean while all three services failed to import.

## 2026-09-21 — Establish the baseline before touching anything

"457 tests pass" only means something if you know it was 457 before. Five
ingestion-service failures looked alarming until a pristine `git worktree` at
the parent commit reproduced all five: three need NLTK corpora the proxy
blocks, two need a Celery broker. Use a worktree rather than `git stash` when
other agents share the working tree.

## 2026-09-21 — Never use an in-range value as a failure sentinel

The Jev judge harness returned `quality=1.0` when an API call failed. On a 1-5
scale, 1.0 is a legitimate score, so no downstream consumer could distinguish a
judgement from a casualty. Six parse failures were scored as six correct
answers, and because failures are deterministic they read as perfect
repeatability. A failed call must be structurally distinguishable, not merely
annotated, and every statistic must exclude it and report the error rate
separately.

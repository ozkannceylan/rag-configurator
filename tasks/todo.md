# Task Ledger

## Active Task

Integrate TypeSafe Jev as a judge into rag-configurator and compare it to an LLM-as-judge baseline on the same fixed RAG traces.

## Current Plan

- [x] Discover existing eval APIs (`app/evaluation/*`, `EvaluationView.vue`) and Jev HTTP/SDK contract
- [x] Add fixed RAG eval fixtures (≥5 Naive RAG traces with optional oracle labels)
- [x] Add Jev judge (System One Score + Noul via `/v1/systemone`) and LLM quality judge (1–5 + does_pass)
- [x] Add compare harness `scripts/jev_eval_compare.py` with K repeats, metrics, USD cap
- [x] Extend rag-service `evaluator_type=jev` and gateway evaluation proxy
- [x] Offline mock tests (CI-safe) + mock/demo COMPARE_REPORT
- [x] Docs (`docs/jev-eval.md`, README highlight, `.env.example`)
- [x] Verify tests, commit, push, open PR

## Notes

- No Obsidian vault found in this environment; proceeding from the repo.
- Do not rewrite agent architectures. LangSmith is optional and not required.
- Live TypeSafe/OpenAI keys may be unavailable; ship mock path + recorded fixtures.
- Claims are observational for this RAG fixture set — no ASIL/safety overclaims.

## Review

- Offline `tests/test_jev_eval.py` + existing `tests/test_evaluation.py`: 63 passed.
- Mock compare: Jev agreement 1.000 / signal 1.000 vs LLM 0.814 / 0.677 on 7 frozen Naive RAG cases × 10 repeats.
- Graphify rebuild skipped (`graphify` not installed in this environment).

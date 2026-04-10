# Task Ledger

This file is the working checklist for the current task.

## Active Task

- [x] Implement Phase 1 from `tasks/v2-plan.md` without changing `docs/ARCHITECTURE.md`

## Current Plan

- [x] Re-read `docs/ARCHITECTURE.md`, `tasks/v2-plan.md`, and `tasks/phase0-implementation-report.md`
- [x] Create shared Python auth and observability foundations in `shared/python/rag_config_common/`
- [x] Add gateway HMAC signing, circuit breaker protection, and OpenTelemetry wiring
- [x] Apply shared HMAC verification and tracing startup to config-service, ingestion-service, and rag-service
- [x] Add ingestion job idempotency with `idempotency_key` tracking
- [x] Add config-service audit logging for user/config state changes
- [x] Update Mongo init script, v2 shared config models, shared TypeScript types, and environment wiring
- [x] Add the v1->v2 config migration script
- [x] Run targeted verification for gateway and the three Python services
- [x] Write `tasks/phase1-implementation-report.md`

## Notes

- Repo-level guidance is in `CLAUDE.md`.
- `docs/ARCHITECTURE.md` remains fixed and was not edited.
- Phase 1 builds on the already-completed Phase 0 security work.
- The Phase 0 review feedback about duplicated auth helpers was addressed by introducing the shared auth package.

## Review

- Phase 1 implementation completed with shared auth/tracing foundations, gateway transport hardening, ingestion idempotency, audit logging, v2 model updates, and migration/runtime wiring.
- Targeted verification passed for config-service, ingestion-service, rag-service, and gateway package tests after syncing the new Go dependencies into `gateway/go.sum`.

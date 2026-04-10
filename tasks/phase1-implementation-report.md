# Phase 1 Implementation Report

Date: 2026-04-08
Plan source: `tasks/v2-plan.md`
Architecture constraint: `docs/ARCHITECTURE.md` was treated as fixed and was not modified.

## Summary

Phase 1 architecture foundation has been implemented across the shared Python package, gateway, config-service, ingestion-service, rag-service, MongoDB bootstrap, and local runtime configuration. The work stayed inside the gateway -> service -> shared-library boundaries defined in `docs/ARCHITECTURE.md` and turned the Phase 0 service-local security work into reusable platform primitives.

## Implemented Deliverables

### 1.1 Shared auth library

- Added `shared/python/rag_config_common/auth/` with:
  - `jwt_utils.py`
  - `hmac_verify.py`
  - `token_blacklist.py`
  - `middleware.py`
- Added shared exports in:
  - `shared/python/rag_config_common/__init__.py`
  - `shared/python/rag_config_common/auth/__init__.py`
- Updated `shared/python/pyproject.toml` optional deps for `auth` and `observability`.
- Rewired config-service token blacklist usage to the shared token blacklist implementation.
- Rewired ingestion-service and rag-service trusted-user extraction to the shared middleware helper.

### 1.2 HMAC inter-service signing

- Added `gateway/internal/middleware/hmac.go` to sign proxied requests with:
  - `X-Service-Signature`
  - `X-Service-Timestamp`
- Gateway now signs proxied requests after path rewriting and before dispatch.
- Added shared verification in `rag_config_common.auth.middleware.ServiceAuthMiddleware`.
- Applied HMAC verification middleware to:
  - `services/config-service/app/main.py`
  - `services/ingestion-service/app/main.py`
  - `services/rag-service/app/main.py`
- Added focused tests so unsigned API requests now return `403` in all three Python services.

### 1.3 Circuit breaker for gateway

- Added `gateway/internal/middleware/circuitbreaker.go`.
- Integrated per-service breakers into `gateway/internal/proxy/proxy.go` for config, ingestion, and rag backends.
- Breaker behavior matches the plan:
  - 5 failures in 30 seconds open the circuit
  - open state lasts 60 seconds
  - half-open probing closes on success and reopens on failure
- Added gateway proxy tests covering circuit-open behavior.

### 1.4 OpenTelemetry distributed tracing

- Added shared tracing setup in `shared/python/rag_config_common/observability/tracing.py`.
- Added gateway tracing setup in `gateway/internal/observability/tracing.go`.
- Added gateway Gin tracing middleware wrapper in `gateway/internal/middleware/tracing.go`.
- Wired tracing into:
  - gateway startup and router middleware
  - config-service startup
  - ingestion-service startup
  - rag-service startup
- Gateway outbound transport now uses `otelhttp`, so `traceparent` propagation follows the gateway span context.
- Added collector runtime support:
  - `infrastructure/otel/otel-collector-config.yaml`
  - `docker-compose.yml` service wiring
- Added env/compose wiring for `OTEL_EXPORTER_OTLP_ENDPOINT` and service names.

### 1.5 Celery task idempotency

- Added `idempotency_key` and `data_source_hash` to `services/ingestion-service/app/storage/models.py`.
- Switched ingestion job persistence to the architecture-aligned `ingestion_jobs` collection via `VectorStore`.
- Added idempotency-key indexing in `VectorStore.initialize_indexes()` and `infrastructure/mongo/init-db.js`.
- Added stable data-source hashing and duplicate-job collapse in `services/ingestion-service/app/api/v1/ingest.py`.
- Duplicate start requests now return the existing job instead of creating parallel work.
- Retry flow now reuses the latest pending/running retry job when the same idempotency key is already active.

### 1.6 Audit logging foundation

- Added:
  - `services/config-service/app/core/audit.py`
  - `services/config-service/app/db/repositories/audit_repo.py`
- Logged state-changing config-service operations:
  - `user.create`
  - `user.update`
  - `user.delete`
  - `config.create`
  - `config.update`
  - `config.delete`
  - `config.duplicate`
- Added audit-log tests for auth, config CRUD, and user state changes.

### 1.7 MongoDB init script update

- Rebuilt `infrastructure/mongo/init-db.js` to provision the Phase 1 collections and indexes:
  - `ingestion_jobs`
  - `evaluations`
  - `audit_logs`
  - `templates`
- Added indexes for:
  - audit logs (`user_id`, `action`, `created_at`)
  - evaluations (`config_id`, `created_at`)
  - templates (`category`, `created_by`)
  - ingestion job idempotency (`idempotency_key`, unique sparse)
- Important implementation note:
  - The plan text called for a unique `(config_id, file_path)` index on `chunks`, but chunks are one-to-many per file. I applied the file-level uniqueness to `documents (config_id, file_path)` and added a correct chunk uniqueness index on `(config_id, document_id, chunk_index)`. This is an inference from the data model in `docs/ARCHITECTURE.md`.

### 1.8 Shared config models for v2

- Updated shared Python config models in `shared/python/rag_config_common/models/config.py`:
  - added `GuardrailsConfig`
  - added `EvaluationConfig`
  - added `CacheConfig`
  - added `truncate_dimensions` to `EmbeddingConfig`
  - updated `RAGPipelineConfig` defaults and v2 fields
- Updated shared enums in Python and TypeScript for v2 values:
  - new embedding providers: `cohere`, `voyage`, `jina`
  - new agent templates: `adaptive_rag`, `agentic_rag`, `graph_rag`
  - new chunking strategies: `late`, `raptor`
- Updated:
  - `shared/typescript/src/config.ts`
  - `shared/typescript/src/enums.ts`
  - `shared/schemas/config.schema.json`
- Updated config-service schemas and business logic so legacy configs get v2 defaults applied on read and new configs persist with v2 fields.

### 1.9 v1->v2 migration script

- Added `scripts/migrate-v1-to-v2.py`.
- Script behavior:
  - connects to MongoDB using env vars or CLI args
  - backfills missing v2 config fields
  - upgrades `version` from v1 to `2.0.0`
  - supports `--dry-run`

## Verification

The following targeted verification commands were run successfully:

- `shared/python` and Python service syntax:
  - `python -m compileall shared/python services/config-service/app services/ingestion-service/app services/rag-service/app scripts/migrate-v1-to-v2.py`
- `services/config-service`:
  - `python -m pytest tests/test_security.py tests/test_auth.py tests/test_configs.py tests/test_users.py -q -p no:cacheprovider`
- `services/ingestion-service`:
  - `python -m pytest tests/test_api.py tests/test_ingestion_task.py tests/test_main.py -q -p no:cacheprovider`
- `services/rag-service`:
  - `python -m pytest tests/test_main.py tests/test_api_security.py tests/test_llm.py -q -p no:cacheprovider`
- `gateway`:
  - `go mod tidy`
  - `go test ./internal/config ./internal/middleware ./internal/proxy ./internal/router`

Observed results:

- `config-service`: 16 passed, 17 skipped
- `ingestion-service`: 60 passed, 3 skipped
- `rag-service`: 63 passed
- `gateway`: targeted package tests passed after syncing new OpenTelemetry modules into `gateway/go.sum`

## Notes

- The Python tracing helper degrades to a no-op when OpenTelemetry packages are not installed, which keeps local test environments usable while still enabling tracing in the configured runtime.
- `go mod tidy` was required in this session because the new gateway tracing dependencies added fresh module entries.
- The migration script was syntax-checked but not executed against a live MongoDB instance in this workspace session.
- Full-stack `make test`, live collector inspection, and kill/restart manual circuit-breaker exercises were not run here; the verification focused on the changed packages and API surfaces.

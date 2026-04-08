# RAG Configurator v2 - Implementation Plan

**Created:** 2026-04-08
**Base document:** [tasks/v2-review-report.md](v2-review-report.md)
**Architecture:** [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)

---

## Phase Overview

```
Phase 0: Security Hardening ──────────────────────── [BLOCKER for all]
    │
    ▼
Phase 1: Architecture Foundation ─────────────────── [shared auth, tracing, cleanup]
    │
    ├──> Phase 2: Core RAG Upgrades ──────────────── [new agents, chunkers, reranking]
    │        │
    │        ├──> Phase 3: Evaluation & Observability [RAGAS, Langfuse]
    │        │
    │        ├──> Phase 4: Advanced RAG ──────────── [GraphRAG, RAPTOR, guardrails]
    │        │
    │        └──> Phase 5: UX Improvements ───────── [comparison, debugger, templates]
    │
    └──> Phase 6: Performance ────────────────────── [caching, streaming, batching]
```

**Phases 2-5 can run in parallel after Phase 1.**
**Phase 6 can start after Phase 1 (independent of Phases 2-5).**

---

## Phase 0: Security Hardening

**Priority:** CRITICAL — blocks all other work
**Branch:** `fix/security-hardening`
**Depends on:** Nothing
**Estimated effort:** 2 weeks

### Deliverables

| # | Task | Size | Files |
|---|------|------|-------|
| 0.1 | Remove `.env` from git history | S | Run `git filter-repo` or BFG. Verify `.gitignore` covers all `.env` patterns. |
| 0.2 | Add auth to RAG service endpoints | M | Create `services/rag-service/app/core/auth.py`. Modify `api/v1/query.py`, `chat.py`, `stream.py` — add `X-User-ID` header extraction + config ownership check. |
| 0.3 | Add auth to Ingestion service endpoints | M | Create `services/ingestion-service/app/core/auth.py`. Modify `api/v1/ingest.py` — verify `config.created_by == user_id` on start/cancel/retry. |
| 0.4 | Implement JWT token revocation | M | Add `jti` (UUID) claim to `services/config-service/app/core/security.py`. Create Redis blacklist: on logout, `SET token_blacklist:{jti} EX remaining_ttl`. Modify `gateway/internal/middleware/auth.go` to check blacklist (requires adding Redis connection to gateway). |
| 0.5 | Fix JWT secret synchronization | S | Document that `JWT_SECRET_KEY` must match across gateway + config-service. Add gateway startup validation: decode a test token to verify compatibility. |
| 0.6 | Fix rate limiter memory leak | S | `gateway/internal/middleware/ratelimit.go` — add `lastSeen` map + cleanup goroutine (every 5 min, evict entries unseen for 10 min). |
| 0.7 | Fix WebSocket origin validation | S | `gateway/internal/handlers/websocket.go` — replace `return true` in `CheckOrigin` with CORS origin whitelist check. |
| 0.8 | Add query length validation | S | `services/rag-service/app/api/v1/query.py` — add `max_length=10000` to `QueryRequest.query` Field. Same for `StreamRequest`. |
| 0.9 | Fix Celery retry backoff | S | `services/ingestion-service/app/tasks/ingestion_task.py` — change from fixed 60s delay to `countdown=60 * (2 ** self.request.retries)` with jitter. |
| 0.10 | Fix frontend token refresh race | S | `apps/configurator-ui/src/api/client.ts` and `apps/sandbox-ui/src/api/client.ts` — add shared promise lock to prevent concurrent refresh calls. |
| 0.11 | Add SSE streaming timeout | S | `services/rag-service/app/api/v1/stream.py` — wrap generator in `asyncio.wait_for(timeout=120)`. |
| 0.12 | Add LLM provider error handling | M | Create `services/rag-service/app/llm/exceptions.py` with `LLMRateLimitError`, `LLMAuthError`, `LLMConnectionError`. Add try/except in all 4 provider files. Return 503 with clear message on provider failure. |

### Checkpoint: Phase 0 Complete

- [ ] No `.env` files in `git log --all -p -- '*.env'`
- [ ] RAG service returns 403 when user queries config they don't own
- [ ] Ingestion service returns 403 when user starts ingestion for config they don't own
- [ ] Logout invalidates token: subsequent requests with that token return 401
- [ ] Rate limiter memory stable under 10K unique IPs (load test with Locust)
- [ ] `python -m pytest tests/e2e/ -v` passes with all auth changes
- [ ] Each service's unit tests pass: `make test`

---

## Phase 1: Architecture Foundation

**Priority:** HIGH — enables all v2 features
**Branch:** `feat/arch-foundation`
**Depends on:** Phase 0
**Estimated effort:** 2-3 weeks

### Deliverables

| # | Task | Size | Files |
|---|------|------|-------|
| 1.1 | Shared auth library | M | Create `shared/python/rag_config_common/auth/` with `jwt_utils.py`, `hmac_verify.py`, `token_blacklist.py`, `middleware.py`. Update `pyproject.toml` with `[auth]` optional deps. |
| 1.2 | HMAC inter-service signing | M | Gateway: create `gateway/internal/middleware/hmac.go` — sign requests with `INTER_SERVICE_SECRET`. Python services: use `rag_config_common.auth.hmac_verify` as FastAPI middleware. |
| 1.3 | Circuit breaker for gateway | M | Create `gateway/internal/middleware/circuitbreaker.go` — per-service (config/ingestion/rag) state machine. Thresholds: 5 failures in 30s -> open 60s. Integrate into proxy.go. |
| 1.4 | OpenTelemetry distributed tracing | L | Create `shared/python/rag_config_common/observability/tracing.py`. Add OTel SDK to all Python services. Add Go OTel middleware to gateway. Add OTel collector to `docker-compose.yml`. Propagate `traceparent` header. |
| 1.5 | Celery task idempotency | M | Add `idempotency_key` (config_id + data_source_hash) to ingestion_jobs. Before dispatching Celery task, check if key already exists with status != FAILED. Modify `ingestion_task.py` and `ingest.py`. |
| 1.6 | Audit logging foundation | M | Create `services/config-service/app/core/audit.py` and `app/db/repositories/audit_repo.py`. Log all CRUD operations on configs and users. Add `audit_logs` collection + indexes to `infrastructure/mongo/init-db.js`. |
| 1.7 | Update MongoDB init script | S | Add new collections: `evaluations`, `audit_logs`, `templates`. Add indexes. Add unique constraint on `(config_id, file_path)` for chunks. |
| 1.8 | Update shared config models for v2 | M | Add `GuardrailsConfig`, `EvaluationConfig`, `CacheConfig` to `shared/python/rag_config_common/models/config.py`. Add new enum values. Update TypeScript types in `shared/typescript/`. |
| 1.9 | v1->v2 config migration script | S | Create `scripts/migrate-v1-to-v2.py` — adds default values for new fields to existing configs in MongoDB. |

### Checkpoint: Phase 1 Complete

- [ ] HMAC signature verified in all 3 Python services — requests without valid signature return 403
- [ ] Circuit breaker tested: kill config-service -> gateway returns 503 -> restart -> requests resume
- [ ] OTel traces visible in collector output (or console exporter in dev)
- [ ] Duplicate ingestion start requests return existing job instead of creating new
- [ ] Audit logs written for config create/update/delete operations
- [ ] Migration script successfully adds v2 fields to existing configs without breaking them
- [ ] All tests pass: `make test`

---

## Phase 2: Core RAG Upgrades

**Priority:** HIGH — the main v2 value proposition
**Branch:** `feat/rag-v2-core`
**Depends on:** Phase 1
**Estimated effort:** 4-5 weeks

### Deliverables

| # | Task | Size | Files |
|---|------|------|-------|
| 2.1 | Contextual Retrieval preprocessor | L | Create `services/ingestion-service/app/chunkers/contextual.py`. After chunking, call LLM to generate 1-2 sentence context prefix per chunk. Store as `contextual_prefix` field. Modify ingestion pipeline to insert this step. Update chunk schema. |
| 2.2 | New embedding providers (Cohere, Voyage, Jina) | M | Create 3 files in `services/ingestion-service/app/embedders/`. Each follows `BaseEmbedder` interface. Register in `factory.py`. Add to `EmbeddingProvider` enum. |
| 2.3 | ColBERT reranking (RAGatouille) | M | Create `services/rag-service/app/retrieval/reranker.py` (abstract base) and `colbert.py` (RAGatouille wrapper). Insert reranking step after retrieval, before agent. Modify `factory.py`. |
| 2.4 | Cohere reranking | S | Add Cohere reranker in `reranker.py` as alternative to ColBERT. |
| 2.5 | Adaptive RAG agent | L | Create `services/rag-service/app/agents/adaptive.py`. Query classification (factual/analytical/creative/multi-hop) -> route to best existing agent. Register in factory. |
| 2.6 | Agentic RAG agent | M | Create `services/rag-service/app/agents/agentic.py`. Wrap retrievers as LangGraph tools. LLM decides when/how to call retrieval dynamically. Register in factory. |
| 2.7 | Matryoshka dimension truncation | S | Add `truncate_dimensions` field to `EmbeddingConfig`. Modify embedders to truncate output vectors when set. |
| 2.8 | True token-level streaming | M | Replace word-split simulation in `stream.py` with actual LLM streaming. Add `stream()` method to `services/rag-service/app/llm/base.py`. Implement in all 4 provider files. |
| 2.9 | LangGraph upgrade + checkpointing | M | Upgrade `langgraph` to latest. Add MongoDB-backed checkpointer for conversation persistence. Use subgraphs for Adaptive RAG router composition. |

### Checkpoint: Phase 2 Complete

- [ ] Contextual Retrieval: chunks in DB have `contextual_prefix` field populated
- [ ] New embedders: test ingestion with Cohere/Voyage/Jina on sample docs -> chunks stored with correct dimensions
- [ ] Reranking: query with reranking enabled returns demonstrably better-ordered results than without
- [ ] Adaptive RAG: submit factual question -> routes to Naive/Multi-Query; submit analytical question -> routes to Plan-Solve/ReAct
- [ ] True streaming: tokens appear one-by-one in SSE stream (not word-by-word bursts)
- [ ] All existing v1 agent tests still pass
- [ ] New unit tests for each new component pass

---

## Phase 3: Evaluation & Observability

**Priority:** HIGH — quality measurement + debugging
**Branch:** `feat/eval-observability`
**Depends on:** Phase 2 (needs agents + retrieval working)
**Estimated effort:** 2-3 weeks

### Deliverables

| # | Task | Size | Files |
|---|------|------|-------|
| 3.1 | RAGAS evaluation framework | L | Create `services/rag-service/app/evaluation/base.py`, `ragas_eval.py`, `models.py`. Implement faithfulness, answer_relevancy, context_precision, context_recall metrics. Store results in `evaluations` collection. |
| 3.2 | LLM-as-judge evaluator | M | Create `services/rag-service/app/evaluation/judge.py`. Configurable judge LLM (can differ from generation LLM). Rubric-based scoring. |
| 3.3 | Evaluation API endpoints | M | Create `services/rag-service/app/api/v1/evaluation.py`. `POST /evaluate` (run evaluation), `GET /evaluations/{config_id}` (history), `GET /evaluations/{config_id}/summary` (aggregates). Register in router. |
| 3.4 | Langfuse integration | M | Create `shared/python/rag_config_common/observability/langfuse.py`. Instrument LLM calls in rag-service. Add Langfuse as optional service in `docker-compose.yml`. |
| 3.5 | OTel metrics (Prometheus format) | M | Add custom metrics: query latency, retrieval latency, LLM tokens, error rates, cache hits. Export via OTel collector or `/metrics` endpoint. |

### Checkpoint: Phase 3 Complete

- [ ] `POST /evaluate` returns RAGAS scores (faithfulness, relevance) for a test query
- [ ] `GET /evaluations/{config_id}/summary` returns aggregate metrics over multiple evaluations
- [ ] Langfuse dashboard shows LLM traces with token counts and latencies (if Langfuse enabled)
- [ ] OTel traces connect gateway -> service -> LLM call in a single trace
- [ ] Evaluation results persist in MongoDB `evaluations` collection

---

## Phase 4: Advanced RAG Features

**Priority:** MEDIUM — differentiating features
**Branch:** `feat/advanced-rag`
**Depends on:** Phase 2 (core RAG infrastructure)
**Estimated effort:** 4-6 weeks

### Deliverables

| # | Task | Size | Files |
|---|------|------|-------|
| 4.1 | Microsoft GraphRAG (community summaries) | XL | Create `services/rag-service/app/agents/graph_rag.py`. Create `services/ingestion-service/app/graph/community.py` (Leiden community detection). Create `services/ingestion-service/app/graph/summarizer.py` (community-level LLM summaries). Add `community_summaries` collection. |
| 4.2 | RAPTOR hierarchical indexing | L | Create `services/ingestion-service/app/chunkers/raptor.py`. Recursive: embed chunks -> cluster (k-means/HDBSCAN) -> summarize -> create parent chunks -> repeat. Store with `parent_chunk_id` and `tree_level` fields. |
| 4.3 | Late Chunking (Jina) | M | Create `services/ingestion-service/app/chunkers/late_chunking.py`. Embed entire document first through long-context model, then split preserving per-token embeddings. Requires Jina embedder. |
| 4.4 | LLM Guard guardrails | M | Create `services/rag-service/app/guardrails/base.py`, `llm_guard.py`, `factory.py`. Pre-query: prompt injection + PII scan. Post-response: toxicity + PII scan. Configurable per pipeline via `GuardrailsConfig`. |
| 4.5 | Data lineage tracking | M | Enrich `AgentResponse.sources` with full lineage (source file -> chunk -> retrieval score -> usage in generation). Create `services/rag-service/app/api/v1/lineage.py` endpoint. |
| 4.6 | Activate Docling for structured PDF | S | Uncomment `docling` in `services/ingestion-service/requirements.txt`. Wire `DocumentProcessingConfig.use_docling` flag to PDF processor. Table-aware chunking: serialize detected tables as Markdown. |

### Checkpoint: Phase 4 Complete

- [ ] GraphRAG: community summaries generated for test corpus. Global question returns answer synthesized from community summaries.
- [ ] RAPTOR: chunks DB shows multi-level hierarchy (`tree_level` 0, 1, 2+)
- [ ] Late Chunking: embeddings reflect full-document context (qualitative comparison vs standard chunking)
- [ ] Guardrails: known prompt injection test case gets blocked. PII in query gets flagged.
- [ ] Lineage API: given a query_id, returns complete source chain from answer -> chunks -> files
- [ ] Docling: complex PDF with tables ingested -> tables appear as Markdown in chunk content

---

## Phase 5: UX Improvements

**Priority:** MEDIUM — user-facing polish
**Branch:** `feat/ux-v2`
**Depends on:** Phase 2 (RAG features to display), Phase 3 (evaluation data for dashboard)
**Estimated effort:** 3-4 weeks

### Deliverables

| # | Task | Size | Files |
|---|------|------|-------|
| 5.1 | Side-by-side config comparison | M | Create `apps/sandbox-ui/src/views/ComparisonView.vue`. Send same query to two configs, display responses side by side. Add route. |
| 5.2 | Retrieval debugger | M | Create `apps/sandbox-ui/src/components/sidebar/RetrievalDebugger.vue`. Show retrieved chunks with scores, reranking deltas, agent decision steps. Use existing `include_debug` parameter. |
| 5.3 | Config templates marketplace | L | Create `apps/configurator-ui/src/views/TemplatesView.vue`. Browse, preview, clone templates. Backend: `services/config-service/app/api/v1/templates.py`. |
| 5.4 | One-click evaluation dashboard | M | Create `apps/sandbox-ui/src/views/EvaluationView.vue`. Display RAGAS scores over time, per-query breakdowns, aggregate metrics. Calls evaluation API from Phase 3. |
| 5.5 | Wizard v2 updates | M | Update wizard step components to include: guardrails config step, evaluation toggle, cache toggle, new chunking strategies, new embedding providers. |
| 5.6 | Update shared TypeScript types | S | Update `shared/typescript/src/config.ts` and `enums.ts` with all v2 types. |

### Checkpoint: Phase 5 Complete

- [ ] Comparison view: enter query -> two configs produce side-by-side responses in UI
- [ ] Retrieval debugger: click a response -> see ranked chunks with scores and agent reasoning steps
- [ ] Templates: create template -> appears in marketplace -> another user clones it -> gets working config
- [ ] Evaluation dashboard: shows RAGAS score charts for a config over time
- [ ] Wizard: all v2 config options selectable (guardrails, new chunkers, new embedders, etc.)

---

## Phase 6: Performance

**Priority:** MEDIUM — latency and cost optimization
**Branch:** `feat/performance`
**Depends on:** Phase 1 (Redis cache infrastructure)
**Estimated effort:** 2-3 weeks
**Can run in parallel with Phases 2-5.**

### Deliverables

| # | Task | Size | Files |
|---|------|------|-------|
| 6.1 | Embedding cache (Redis) | M | Create `shared/python/rag_config_common/cache/embedding_cache.py`. Hash text -> check Redis -> return cached vector or compute + cache. Use in ingestion-service embedders. |
| 6.2 | Semantic query cache | M | Create `shared/python/rag_config_common/cache/query_cache.py`. Key: `(config_id, query_sha256)` -> cached RAG response. TTL configurable per config. Use in rag-service query/stream endpoints. |
| 6.3 | Connection pool optimization | S | Review MongoDB connection pools in each service. Set `maxPoolSize=50, minPoolSize=5` in Motor clients. |
| 6.4 | Batch embedding optimization | M | Verify batch sizes in ingestion pipeline are optimal. Add configurable batch size to `EmbeddingConfig`. Test OpenAI batch API for bulk ingestion (50% cost reduction). |
| 6.5 | Vector index optimization | S | Update `infrastructure/mongo/init-db.js` with proper `createSearchIndex` commands. Set correct dimensions and similarity metrics per embedding model. |

### Checkpoint: Phase 6 Complete

- [ ] Embedding cache: re-ingest same document -> >80% cache hit rate (verify with Redis MONITOR)
- [ ] Query cache: repeat same query -> response time <50ms (vs >500ms uncached)
- [ ] Locust load test: 100 concurrent users -> p99 latency under 5s for cached queries
- [ ] Ingestion throughput: >30% improvement with batch optimization (benchmark before/after)

---

## Cross-Cutting Requirements (All Phases)

### Testing
- Every new file gets a corresponding test file
- Maintain >70% coverage on new code
- Run `make test` before every PR merge

### Documentation
- New API endpoints documented in `docs/API.md`
- Architecture decisions logged in `docs/ARCHITECTURE.md` ADR section
- CLAUDE.md updated when build/test/run commands change

### Type Safety
- Python: all new code passes `ruff check` + `black --check`
- Go: all new code passes `golangci-lint run`
- TypeScript: `npm run lint` clean

### Backward Compatibility
- v2 config models must deserialize v1 configs (default values for new fields)
- All v1 API endpoints continue to work unchanged
- Migration script (`scripts/migrate-v1-to-v2.py`) handles DB schema evolution

### Branch Strategy
- Each phase gets its own feature branch off `main`
- PR required for merge with passing CI
- Phase 0 merges to `main` first (security fixes)
- Subsequent phases can branch from updated `main`

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| RAGAS API breaking changes (v0.1 -> v0.2) | Phase 3 delay | Pin version, test before upgrading |
| LangGraph major version change | Phase 2 refactor | Check latest version before starting Phase 2 |
| ColBERT/RAGatouille model download size | CI/CD slow | Cache models in Docker layer, use smaller models in CI |
| MongoDB Atlas Vector Search limitations vs dedicated VDB | Phase 4 (GraphRAG multi-vector) | Keep Qdrant as contingency backend |
| Docling system dependency conflicts | Phase 4.6 | Test in Docker first, may need separate container |
| Celery Redis broker scaling under high ingestion load | Phase 6 load test | Monitor Redis memory, consider RabbitMQ if needed |

---

## Definition of Done: v2.0.0 Release

- [ ] All Phase 0 items complete (security hardened)
- [ ] All Phase 1 items complete (architecture foundation)
- [ ] Phase 2 core items complete (contextual retrieval, adaptive RAG, reranking, true streaming)
- [ ] Phase 3 evaluation items complete (RAGAS, evaluation API)
- [ ] Phase 6 caching items complete (embedding + query cache)
- [ ] E2E tests pass with all new features
- [ ] Load test passes: 100 concurrent users, p99 < 5s
- [ ] ARCHITECTURE.md reflects actual v2 implementation
- [ ] Demo data updated with v2 config examples
- [ ] CHANGELOG.md updated

**Phases 4 and 5 are stretch goals for v2.0.0.** They can ship in v2.1.0 if timeline is tight.

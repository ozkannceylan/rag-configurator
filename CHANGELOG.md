# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] — 2026-04-08

### Phase 0: Security Hardening
- **HMAC inter-service authentication** — Gateway signs requests, backend services verify signatures via shared secret
- **Token blacklist** — Redis-backed JWT blacklist with in-memory fallback for logout support
- **JWT improvements** — Token type validation, JTI extraction, bearer token parsing utilities
- **Service auth middleware** — Shared middleware in `rag_config_common` for consistent auth across services

### Phase 1: Architecture Foundation
- **OpenTelemetry tracing** — Distributed tracing with OTLP exporter across all services
- **Custom observability metrics** — Query duration, retrieval time, LLM tokens, cache hits, evaluation scores
- **Idempotent ingestion** — DuplicateKeyError handling in vector store for safe retries
- **Celery OTel integration** — Tracing environment variables for Celery workers

### Phase 3: Evaluation & Observability
- **RAGAS evaluation engine** — Faithfulness, answer relevancy, context precision, context recall metrics
- **Evaluation API** — REST endpoints for triggering and retrieving evaluation results
- **Evaluation repository** — MongoDB storage for evaluation history with per-config queries
- **Langfuse integration** — Optional LLM observability via Langfuse (Docker profile: `observability`)

### Phase 4: Advanced RAG (Stretch)
- **GraphRAG agent** — Community-based summarization using Leiden algorithm for global/local queries
- **Graph retrieval** — Node/edge traversal with configurable depth and scoring
- **Graph extraction** — LLM-based entity and relationship extraction during ingestion
- **RAPTOR chunker** — Hierarchical tree-based chunking with recursive abstraction
- **Late interaction chunker** — ColBERT-style chunking for fine-grained retrieval
- **Query lineage tracking** — Full audit trail of query execution steps

### Phase 5: UI Enhancements (Stretch)
- **Comparison view** — Side-by-side RAG response comparison for two configs
- **Retrieval debugger** — Chunk scores and agent reasoning step visualization
- **Evaluation dashboard** — RAGAS score charts over time per config
- **Pipeline templates** — Template marketplace for quick-start configurations
- **Advanced wizard step** — Guardrails, evaluation, and cache configuration in wizard
- **New agent types in UI** — Adaptive RAG, Agentic RAG, GraphRAG selectable
- **New embedding providers** — Cohere, Voyage, Jina options in model selection
- **New chunking strategies** — RAPTOR and Late Interaction in retrieval config

### Phase 6: Performance
- **Embedding cache** — Redis-backed cache with batch get/set using pipelines, SHA256-keyed
- **Query response cache** — Per-config Redis cache with configurable TTL and SCAN-based invalidation
- **Connection pool optimization** — Standardized `maxPoolSize=50, minPoolSize=5` across all services
- **Batch embedding** — Configurable batch sizes for embedding API calls
- **Vector index optimization** — MongoDB Atlas Search vector indexes and compound content_hash indexes

### Infrastructure
- **Langfuse stack** — Optional Langfuse + PostgreSQL via Docker Compose `observability` profile
- **MongoDB v2 collections** — graph_nodes, graph_edges, community_summaries, query_lineage, evaluations
- **ARCHITECTURE.md** — Full system architecture documentation

## [1.0.0] — 2026-03-15

### Initial Release
- Config Service with user auth and CRUD
- Ingestion Service with Celery workers (PDF, DOCX, TXT, MD, HTML, OCR)
- RAG Service with 6 agent types (Naive, ReAct, CRAG, Self-RAG, Multi-Query, Plan-Solve)
- Go Gateway with JWT validation and reverse proxy
- Configurator UI wizard (7 steps)
- Sandbox UI chat interface with SSE streaming
- MongoDB vector storage
- Redis for Celery broker

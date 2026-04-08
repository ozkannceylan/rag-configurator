# RAG Configurator v2 - Architecture Documentation

This document describes the system architecture, data flows, security model, and key design decisions for RAG Configurator v2.

---

## 1. Executive Summary

RAG Configurator is a low-code platform for building and deploying custom RAG pipelines. Four Python/Go microservices behind a reverse proxy gateway, two Vue 3 frontends, MongoDB + Redis infrastructure.

### What Changed: v1 to v2

| Area | v1 | v2 |
|------|----|----|
| **Auth** | JWT at gateway only, no revocation | Token blacklist (Redis), HMAC inter-service signing, ownership enforcement in all services |
| **Retrieval** | Vector, keyword, graph, hybrid | + Reranking (ColBERT/Cohere), contextual retrieval, adaptive routing |
| **Agents** | 6 templates (Naive, ReAct, CRAG, Self-RAG, Multi-Query, Plan-Solve) | + Adaptive RAG, Agentic RAG, GraphRAG |
| **Chunking** | Recursive, semantic, document | + Late chunking, contextual enrichment, RAPTOR hierarchical |
| **Embeddings** | OpenAI, Ollama, HuggingFace | + Cohere, Voyage, Jina, Matryoshka dimension support |
| **Evaluation** | Manual (judge prompts) | RAGAS framework, LLM-as-judge, evaluation API + dashboard |
| **Observability** | Structured logging only | OpenTelemetry distributed tracing, Langfuse LLM observability |
| **Security** | JWT + bcrypt + rate limiting | + Guardrails (PII, prompt injection, toxicity), audit logging, token revocation |
| **Performance** | None | Embedding cache, semantic query cache, true token-level streaming |

---

## 2. System Overview

### 2.1 Component Diagram

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                     │
│                                                                               │
│   ┌───────────────────────┐             ┌───────────────────────┐            │
│   │   Configurator UI     │             │     Sandbox UI        │            │
│   │   (Vue 3, :5173)      │             │   (Vue 3, :3001)      │            │
│   │                       │             │                       │            │
│   │  Pipeline wizard      │             │  Chat interface       │            │
│   │  Template marketplace │             │  Side-by-side compare │            │
│   │  Evaluation dashboard │             │  Retrieval debugger   │            │
│   │  Ingestion monitor    │             │  Source citations      │            │
│   └───────────┬───────────┘             └───────────┬───────────┘            │
└───────────────┼─────────────────────────────────────┼────────────────────────┘
                │              HTTPS / SSE             │
                ▼                                      ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        GO API GATEWAY (:8000)                                 │
│                                                                               │
│  Request Flow:                                                                │
│  ┌────────┐ ┌────────┐ ┌───────────┐ ┌──────────┐ ┌───────┐ ┌────────────┐  │
│  │Recovery│→│Logging │→│Rate Limit │→│Auth(JWT) │→│ HMAC  │→│Circuit     │  │
│  │        │ │+ Trace │ │(IP+User)  │ │+Blacklist│ │ Sign  │ │Breaker     │  │
│  └────────┘ └────────┘ └───────────┘ └──────────┘ └───────┘ └─────┬──────┘  │
│                                                                     │         │
│  Router: /auth/* → Config (public)  /configs/* → Config             │         │
│          /users/* → Config          /folders/* → Config             │         │
│          /ingest/* → Ingestion      /query/*,/chat/*,/stream/* → RAG│         │
│          /evaluate/* → RAG          /health → local                 │         │
└─────────────────────────────┬───────────────────┬───────────────────┘
                              │                   │
           ┌──────────────────┼───────────────────┼──────────────────┐
           ▼                  ▼                   ▼                  │
┌──────────────────┐ ┌────────────────────┐ ┌────────────────────┐  │
│  Config Service  │ │ Ingestion Service  │ │   RAG Service      │  │
│  (FastAPI :8001) │ │ (FastAPI+Celery    │ │ (FastAPI+LangGraph │  │
│                  │ │  :8002)            │ │  :8003)            │  │
│  Auth & JWT      │ │                    │ │                    │  │
│  Config CRUD     │ │  Processors        │ │  ┌──────────────┐ │  │
│  Folder browsing │ │  Chunkers          │ │  │ Guardrails   │ │  │
│  YAML export     │ │  Context enricher  │ │  │ (pre-query)  │ │  │
│  Templates       │ │  Embedders         │ │  └──────┬───────┘ │  │
│  Audit logging   │ │  Graph builder     │ │         ▼         │  │
│  User management │ │  Vector store      │ │  Retrievers       │  │
│                  │ │                    │ │  Rerankers         │  │
│  [HMAC verify]   │ │  Celery workers:  │ │  9 Agent templates │  │
│  [Token blacklist│ │   Process→Chunk→  │ │  4 LLM providers   │  │
│   via Redis]     │ │   Enrich→Embed→   │ │  Evaluation(RAGAS) │  │
│                  │ │   Store           │ │  Prompt manager     │  │
│                  │ │                    │ │  RBAC enforcement   │  │
│                  │ │  [HMAC verify]     │ │  ┌──────────────┐ │  │
│                  │ │  [Ownership check] │ │  │ Guardrails   │ │  │
│                  │ │                    │ │  │ (post-resp)  │ │  │
│                  │ │                    │ │  └──────────────┘ │  │
└────────┬─────────┘ └────────┬───────────┘ └────────┬───────────┘  │
         │                    │                      │              │
         └────────────────────┼──────────────────────┘              │
                              ▼                                     │
┌───────────────────────────────────────────────────────────────────┘
│                         DATA & QUEUE LAYER
│
│  ┌──────────────────────────┐   ┌───────────────────────────────┐
│  │     MongoDB (:27017)     │   │       Redis (:6379)           │
│  │                          │   │                               │
│  │  users                   │   │  Celery broker + results      │
│  │  configs                 │   │  Token blacklist (JTI → TTL)  │
│  │  documents               │   │  Embedding cache              │
│  │  chunks (+ vectors)      │   │  Semantic query cache         │
│  │  graph_nodes, graph_edges│   │  Rate limit state             │
│  │  ingestion_jobs          │   │                               │
│  │  conversations           │   │                               │
│  │  evaluations (v2)        │   │                               │
│  │  audit_logs (v2)         │   │                               │
│  │  templates (v2)          │   │                               │
│  └──────────────────────────┘   └───────────────────────────────┘
│
│  ┌──────────────────────────┐   ┌───────────────────────────────┐
│  │  Langfuse (optional)     │   │  OTel Collector (optional)    │
│  │  LLM observability       │   │  Distributed tracing          │
│  └──────────────────────────┘   └───────────────────────────────┘
```

### 2.2 Service Registry

| Service | Port | Tech | Purpose |
|---------|------|------|---------|
| Gateway | 8000 | Go 1.24, Gin | Auth, routing, rate limiting, circuit breaker, HMAC signing |
| Config Service | 8001 | Python 3.11, FastAPI | Users, auth, configs, folders, templates, audit |
| Ingestion Service | 8002 | Python 3.11, FastAPI, Celery | Document processing pipeline |
| RAG Service | 8003 | Python 3.11, FastAPI, LangGraph | Retrieval, generation, evaluation, guardrails |
| Configurator UI | 5173 | Vue 3, TypeScript, Vite | Pipeline configuration wizard |
| Sandbox UI | 3001 | Vue 3, TypeScript, Vite | Chat testing + evaluation |
| MongoDB | 27017 | MongoDB 7.0 | Primary data store + vector search |
| Redis | 6379 | Redis 7 | Celery broker, caching, token blacklist |
| Mongo Express | 8081 | Web UI | Database browser (dev only) |
| Redis Commander | 8082 | Web UI | Queue inspector (dev only) |

---

## 3. Service Architecture

### 3.1 Gateway (Go/Gin)

The single entry point for all client requests. Stateless, horizontally scalable.

**Middleware Chain** (executed in order):
1. **Recovery** — Panic recovery, returns JSON error
2. **Logging + Tracing** — Structured JSON (zerolog), OpenTelemetry span creation
3. **Rate Limiting** — Token bucket per IP AND per user (from JWT). Periodic cleanup of stale entries (5-min TTL).
4. **Authentication** — JWT validation + Redis blacklist check. Public routes (`/auth/*`) skip this.
5. **HMAC Signing** — Signs outgoing proxied requests with `X-Service-Signature` header using `INTER_SERVICE_SECRET`
6. **Circuit Breaker** — Per-backend-service state (closed/open/half-open). 5 failures in 30s triggers open state for 60s.

**Key files:**
```
gateway/
├── cmd/server/main.go                  # Entry point, graceful shutdown
├── internal/
│   ├── config/config.go                # Environment-based config (caarlos0/env)
│   ├── middleware/
│   │   ├── auth.go                     # JWT + blacklist check
│   │   ├── cors.go                     # Configurable CORS
│   │   ├── ratelimit.go                # IP + user rate limiting
│   │   ├── logging.go                  # Structured logging
│   │   ├── recovery.go                 # Panic recovery
│   │   ├── circuitbreaker.go           # v2: Per-service circuit breakers
│   │   ├── hmac.go                     # v2: Request signing
│   │   └── tracing.go                  # v2: OTel middleware
│   ├── proxy/proxy.go                  # httputil.ReverseProxy, FlushInterval=-1 for SSE
│   ├── router/router.go                # Route definitions
│   └── handlers/
│       ├── health.go                   # /health, /health/detailed
│       └── websocket.go                # WebSocket upgrade + origin validation
└── pkg/jwt/jwt.go                      # JWT decode, claim extraction
```

**Headers forwarded to backend services:**
- `X-Forwarded-For`, `X-Real-IP`, `X-Forwarded-Host`, `X-Forwarded-Proto` (standard proxy)
- `X-User-ID` (from JWT `sub` claim, set by auth middleware)
- `X-Service-Signature` (HMAC of request, set by signing middleware)
- `X-Request-ID` (for tracing correlation)

### 3.2 Config Service (FastAPI)

Manages users, authentication, pipeline configurations, and administrative functions.

**Auth flow:**
- Registration: validate email uniqueness -> bcrypt hash password -> insert user -> generate JWT pair
- Login: find user by email -> verify password -> generate access token (30m) + refresh token (7d)
- Refresh: validate refresh token -> check blacklist -> issue new token pair -> blacklist old refresh token
- Logout: add access + refresh JTI to Redis blacklist with TTL = remaining lifetime

**Key files:**
```
services/config-service/app/
├── main.py                             # FastAPI app, lifespan, CORS
├── api/v1/
│   ├── auth.py                         # register, login, refresh, logout
│   ├── users.py                        # GET/PUT/DELETE /me
│   ├── configs.py                      # CRUD + duplicate + pagination
│   ├── folders.py                      # browse, scan
│   ├── export.py                       # YAML export/import
│   ├── templates.py                    # v2: template marketplace CRUD
│   └── audit.py                        # v2: audit log query endpoint
├── core/
│   ├── settings.py                     # Pydantic settings from env
│   ├── security.py                     # JWT creation (with JTI), bcrypt
│   ├── exceptions.py                   # Custom exception classes
│   └── audit.py                        # v2: audit event writer
├── db/
│   ├── mongodb.py                      # Motor client, health check
│   └── repositories/
│       ├── base.py                     # Generic BaseRepository[T]
│       ├── user_repo.py                # User CRUD
│       ├── config_repo.py              # Config CRUD
│       ├── template_repo.py            # v2: template CRUD
│       └── audit_repo.py              # v2: audit log storage
├── services/
│   ├── auth_service.py                 # Auth business logic
│   ├── config_service.py               # Config business logic
│   ├── folder_service.py               # Directory traversal
│   ├── export_service.py               # YAML serialization
│   └── user_service.py                 # User management
└── schemas/                            # Pydantic request/response models
```

### 3.3 Ingestion Service (FastAPI + Celery)

Processes documents through a configurable pipeline: parse -> chunk -> (enrich) -> embed -> store.

**v2 Pipeline (extended):**
```
┌────────┐   ┌───────────┐   ┌─────────┐   ┌───────────────┐   ┌──────────┐   ┌───────────┐
│  File  │──>│ Processor │──>│ Chunker │──>│  Context      │──>│ Embedder │──>│  Storage  │
│        │   │           │   │         │   │  Enrichment   │   │          │   │           │
│ PDF    │   │ text.py   │   │recursive│   │ (v2 optional) │   │ OpenAI   │   │ MongoDB   │
│ DOCX   │   │ pdf.py    │   │semantic │   │               │   │ Ollama   │   │ chunks    │
│ TXT    │   │ docx.py   │   │document │   │ Contextual    │   │ HuggingF │   │ vectors   │
│ MD     │   │ image.py  │   │late (v2)│   │ preamble via  │   │ Cohere   │   │           │
│ HTML   │   │           │   │RAPTOR   │   │ LLM call      │   │ Voyage   │   │           │
│ Image  │   │           │   │(v2)     │   │               │   │ Jina     │   │           │
└────────┘   └───────────┘   └─────────┘   └───────────────┘   └──────────┘   └─────┬─────┘
                                                                                      │
                                                                               ┌──────▼──────┐
                                                                               │ Graph Store │
                                                                               │ (optional)  │
                                                                               │ entities +  │
                                                                               │ relations   │
                                                                               │ communities │
                                                                               │ (v2)        │
                                                                               └─────────────┘
```

**Celery configuration:**
- Broker: Redis (same instance, DB 0)
- Task acks: late (after completion, not on receive)
- Retry: exponential backoff with jitter (v2 fix)
- Idempotency: dedup key = `config_id + data_source_hash` (v2)
- Concurrency: configurable (default 2)
- Timeouts: soft 3600s, hard 3900s

**Key files:**
```
services/ingestion-service/app/
├── processors/         # Base + factory + pdf/docx/text/image
├── chunkers/           # Base + factory + recursive/semantic/document
│   ├── contextual.py   # v2: Anthropic-style context enrichment
│   ├── late_chunking.py # v2: Jina-style embed-then-split
│   └── raptor.py       # v2: Hierarchical tree indexing
├── embedders/          # Base + factory + openai/ollama/huggingface
│   ├── cohere.py       # v2
│   ├── voyage.py       # v2
│   └── jina.py         # v2
├── graph/              # extractor.py + builder.py
│   └── community.py    # v2: Leiden community detection
├── storage/            # vector_store.py + graph_store.py
├── tasks/              # ingestion_task.py (867-line orchestrator)
├── core/
│   ├── celery_app.py   # Celery config
│   ├── settings.py     # Service settings
│   └── auth.py         # v2: X-User-ID + ownership verification
└── api/v1/ingest.py    # start, status, cancel, retry, logs, stats
```

### 3.4 RAG Service (FastAPI + LangGraph)

Handles query processing, retrieval, generation, evaluation, and guardrails.

**v2 Query Pipeline:**
```
Query → [Guardrails Pre-Check] → [Cache Check] → Retriever → [Reranker] → Agent → LLM → [Guardrails Post-Check] → Response
                                       ↓                                                         ↓
                                  Cache Hit → Return                                    [Evaluation (async)]
```

**Agent Templates (v2: 9 total):**

| Agent | Pattern | v1/v2 |
|-------|---------|-------|
| Naive RAG | Retrieve -> Generate | v1 |
| ReAct | Reasoning + Acting loop with tools | v1 |
| CRAG | Corrective RAG with relevance grading | v1 |
| Self-RAG | Self-reflection, critique, refine | v1 |
| Multi-Query | Query expansion, parallel retrieval | v1 |
| Plan-Solve | Decompose into sub-tasks, solve step by step | v1 |
| **Adaptive RAG** | **Classify query -> route to best agent** | **v2** |
| **Agentic RAG** | **Retrieval as an LLM tool (dynamic invocation)** | **v2** |
| **GraphRAG** | **Community summaries for global queries** | **v2** |

**Retrieval Strategies (v2: 5 + reranking):**
- Vector (MongoDB Atlas HNSW, cosine similarity fallback)
- Keyword (Atlas Search / fuzzy matching)
- Graph (entity-relationship traversal)
- Hybrid (Reciprocal Rank Fusion of vector + keyword + graph)
- ColBERT reranking (via RAGatouille, applied post-retrieval)

**LLM Providers:** OpenAI, Anthropic, Ollama, vLLM

**Key files:**
```
services/rag-service/app/
├── agents/             # Base + factory + 6 v1 agents
│   ├── adaptive.py     # v2: Query routing
│   ├── agentic.py      # v2: Retrieval as tool
│   └── graph_rag.py    # v2: Microsoft GraphRAG
├── retrieval/          # Base + factory + vector/keyword/graph/hybrid
│   ├── reranker.py     # v2: Abstract reranker
│   └── colbert.py      # v2: RAGatouille integration
├── llm/                # Base + factory + openai/anthropic/ollama/vllm
│   └── exceptions.py   # v2: LLMRateLimitError, LLMAuthError, etc.
├── guardrails/         # v2: entire directory
│   ├── base.py         # Abstract guardrail interface
│   ├── llm_guard.py    # LLM Guard integration
│   └── factory.py      # Build guardrail chain from config
├── evaluation/         # v2: replace .gitkeep placeholders
│   ├── base.py         # Abstract evaluator
│   ├── ragas_eval.py   # RAGAS metrics
│   ├── judge.py        # LLM-as-judge
│   └── models.py       # EvaluationResult models
├── prompts/            # manager.py + templates/ (YAML)
├── rbac/               # enforcer.py (role-based folder filtering)
├── core/
│   ├── settings.py
│   └── auth.py         # v2: X-User-ID + ownership verification
└── api/v1/
    ├── query.py        # POST /query
    ├── chat.py         # POST /chat
    ├── stream.py       # GET /stream (SSE)
    ├── evaluation.py   # v2: POST /evaluate, GET /evaluations
    └── lineage.py      # v2: GET /lineage/:query_id
```

### 3.5 Shared Libraries

```
shared/python/rag_config_common/
├── models/
│   ├── config.py       # RAGPipelineConfig + all sub-models (GuardrailsConfig, EvaluationConfig, CacheConfig in v2)
│   ├── enums.py        # All enums (AgentTemplate, ChunkingStrategy, EmbeddingProvider, etc.)
│   └── user.py         # UserBase, UserCreate, UserResponse
├── auth/               # v2: shared auth utilities
│   ├── jwt_utils.py    # Decode/verify JWT (shared logic for all Python services)
│   ├── hmac_verify.py  # Verify inter-service HMAC signature
│   ├── token_blacklist.py  # Redis-based blacklist client
│   └── middleware.py   # FastAPI dependency: verify_request_auth()
├── cache/              # v2: shared caching
│   ├── redis_cache.py  # Generic Redis cache client
│   ├── embedding_cache.py  # text_hash -> vector
│   └── query_cache.py  # (config_id, query_hash) -> response
├── observability/      # v2: shared tracing/metrics
│   ├── tracing.py      # OpenTelemetry setup
│   ├── langfuse.py     # Langfuse client wrapper
│   └── metrics.py      # Common metric definitions
└── utils/              # Shared utilities
```

---

## 4. Data Flow Diagrams

### 4.1 Authentication Flow (v2)

```
┌────────┐     ┌──────────┐     ┌────────────┐     ┌───────┐
│ Client │────>│ Gateway  │────>│  Config    │────>│MongoDB│
│        │     │          │     │  Service   │     │       │
│ Login  │     │ (public  │     │            │     │ users │
│ POST   │     │  route)  │     │ Verify pwd │     │       │
└────────┘     └──────────┘     │ Create JWT │     └───────┘
                                │ (with JTI) │
                                └─────┬──────┘
                                      │
     ┌────────────────────────────────┘
     ▼
┌──────────┐
│  Redis   │
│          │
│ (no-op   │     On logout: SET token_blacklist:{jti} EX {remaining_ttl}
│  at login│     On refresh: blacklist old refresh JTI, issue new pair
│  time)   │     On every request: gateway checks GET token_blacklist:{jti}
└──────────┘
```

### 4.2 Ingestion Flow (v2)

```
Client ──> Gateway ──> Ingestion Service ──> Celery Worker
           (auth)      (ownership check)     │
                                             ├─ 1. Parse file (processor)
                                             ├─ 2. Chunk text (chunker)
                                             ├─ 3. Enrich chunks (contextual preamble via LLM) [v2]
                                             ├─ 4. Generate embeddings (embedder)
                                             │     └─ Check embedding cache first [v2]
                                             ├─ 5. Store chunks + vectors (MongoDB)
                                             ├─ 6. Extract graph entities (optional)
                                             ├─ 7. Build graph edges (optional)
                                             └─ 8. Detect communities (optional) [v2]

Progress: Celery state updates -> polled via GET /ingest/:config_id/status
```

### 4.3 Query Flow (v2)

```
Client ──> Gateway ──> RAG Service
           (auth,      │
            HMAC sign,  ├─ 1. Verify ownership (config.created_by == user_id)
            circuit     ├─ 2. Guardrails pre-check (PII, injection scan) [v2]
            breaker)    ├─ 3. Check semantic query cache [v2]
                        ├─ 4. Load retriever from config
                        ├─ 5. Retrieve chunks (vector/keyword/graph/hybrid)
                        ├─ 6. Rerank results (ColBERT/Cohere) [v2]
                        ├─ 7. RBAC filter (remove unauthorized chunks)
                        ├─ 8. Agent processes (Naive/ReAct/CRAG/Adaptive/...)
                        ├─ 9. LLM generates response
                        ├─ 10. Guardrails post-check (toxicity, PII in output) [v2]
                        ├─ 11. Cache response [v2]
                        ├─ 12. Async: evaluate with RAGAS [v2]
                        └─ 13. Return {answer, sources, steps, metadata}
```

### 4.4 Streaming Flow (v2)

```
Client                    Gateway                    RAG Service              LLM
  │                          │                          │                      │
  │ GET /stream?token=...    │                          │                      │
  │─────────────────────────>│                          │                      │
  │                          │ Validate JWT from query  │                      │
  │                          │ param (SSE can't set     │                      │
  │                          │ headers)                 │                      │
  │                          │─────────────────────────>│                      │
  │                          │                          │ Retrieve + rerank    │
  │                          │                          │─────────────────────>│
  │                          │                          │                      │
  │  SSE: {type:"source"}    │                          │<─ token ─────────── │
  │<─────────────────────────│<─────────────────────────│                      │
  │  SSE: {type:"token"}     │                          │<─ token ─────────── │
  │<─────────────────────────│<─────────────────────────│                      │
  │  SSE: {type:"token"}     │   (FlushInterval=-1      │<─ token ─────────── │
  │<─────────────────────────│    enables immediate     │                      │
  │         ...              │    SSE forwarding)       │      ...             │
  │  SSE: {type:"done"}      │                          │<─ finish ─────────  │
  │<─────────────────────────│<─────────────────────────│                      │

Timeout: asyncio.wait_for(generator, timeout=120s) [v2]
True token-level streaming from LLM provider (not word-split simulation) [v2]
```

### 4.5 Evaluation Flow (v2)

```
POST /evaluate {query, config_id, expected_answer?}
  │
  ├─ Run query through RAG pipeline (full trace)
  │
  ├─ RAGAS metrics:
  │   ├─ Faithfulness: Is answer grounded in retrieved context?
  │   ├─ Answer Relevancy: Does answer address the question?
  │   ├─ Context Precision: Are retrieved docs relevant?
  │   └─ Context Recall: Are all needed docs retrieved?
  │
  ├─ LLM-as-Judge (optional):
  │   └─ Configurable rubric scoring
  │
  ├─ Store in MongoDB: evaluations collection
  │
  └─ Log to Langfuse trace (if enabled)
```

---

## 5. Database Schema

### 5.1 MongoDB Collections

| Collection | Purpose | Key Indexes |
|------------|---------|-------------|
| `users` | User accounts | unique: `email` |
| `configs` | RAG pipeline configurations | `created_by`, `status`, `created_at` |
| `documents` | Ingested document metadata | `config_id` |
| `chunks` | Text chunks with embeddings | `config_id`, `document_id`, vector index |
| `graph_nodes` | Knowledge graph entities | `(config_id, node_type)`, `(config_id, name)` |
| `graph_edges` | Knowledge graph relations | `(config_id, source_node)`, `(config_id, relation_type)` |
| `ingestion_jobs` | Ingestion task tracking | `config_id`, unique: `idempotency_key` (v2) |
| `conversations` | Chat history | `(config_id, user_id)` |
| `evaluations` | RAGAS evaluation results (v2) | `config_id`, `created_at` |
| `audit_logs` | State-change audit trail (v2) | `user_id`, `action`, `created_at` |
| `templates` | Config template marketplace (v2) | `category`, `created_by` |

**v2 Schema additions to `chunks` collection:**
```json
{
  "contextual_prefix": "This chunk is from the 'Security Architecture' section of the deployment guide...",
  "tree_level": 0,
  "parent_chunk_id": null
}
```

### 5.2 Redis Key Schema

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `token_blacklist:{jti}` | Revoked JWT tracking | Remaining token lifetime |
| `rate_limit:{ip}:{window}` | IP-based rate limit state | Window duration |
| `rate_limit:user:{user_id}:{window}` | User-based rate limit (v2) | Window duration |
| `embed_cache:{model}:{text_sha256}` | Cached embedding vector | Configurable (default 24h) |
| `query_cache:{config_id}:{query_sha256}` | Cached RAG response | Configurable (default 1h) |
| `celery` (broker queues) | Task queue, results | Celery managed |

---

## 6. Security Architecture

### 6.1 Authentication

```
Layer 1: Transport        HTTPS/WSS in production (Nginx TLS termination)
Layer 2: Gateway          Rate limiting (IP + user), JWT validation, token blacklist check
Layer 3: Inter-Service    HMAC request signing (gateway -> services)
Layer 4: Service-Level    Ownership verification (config.created_by == X-User-ID)
Layer 5: RBAC             Per-config role-based folder access filtering
Layer 6: Guardrails       PII detection, prompt injection scanning, toxicity check (v2)
Layer 7: Data             Input validation (Pydantic), query length limits, file type validation
Layer 8: Audit            All state changes logged with user_id, action, timestamp (v2)
```

### 6.2 JWT Token Lifecycle (v2)

- Access tokens: 30 min, contain `{sub: user_id, type: "access", jti: uuid, exp, iat}`
- Refresh tokens: 7 days, contain `{sub: user_id, type: "refresh", jti: uuid, exp, iat}`
- On refresh: old refresh token JTI added to Redis blacklist, new pair issued
- On logout: both access and refresh JTI added to blacklist
- Gateway checks `GET token_blacklist:{jti}` on every authenticated request

### 6.3 Inter-Service Trust

Gateway signs all proxied requests with:
```
X-Service-Signature: HMAC-SHA256(INTER_SERVICE_SECRET, method + path + timestamp + body_hash)
X-Service-Timestamp: unix_epoch
```

Backend services verify the signature and reject requests where:
- Signature doesn't match
- Timestamp is older than 30 seconds (replay protection)

---

## 7. Observability

### 7.1 Distributed Tracing (OpenTelemetry)

```
Client Request
  └─ Gateway Span (trace_id generated)
       ├─ Auth Middleware Span
       ├─ Rate Limit Span
       └─ Proxy Span
            └─ Service Span (trace_id propagated via headers)
                 ├─ Retrieval Span
                 │    ├─ Vector Search Span
                 │    └─ Rerank Span
                 ├─ Agent Span
                 │    └─ LLM Call Span (tokens, model, latency)
                 └─ Guardrails Span
```

Trace context propagated via `traceparent` header (W3C Trace Context).

### 7.2 Langfuse Integration

- Traces every LLM call (prompt, response, tokens, model, latency, cost)
- Links to RAGAS evaluation scores per trace
- Dashboard for quality monitoring over time
- Self-hostable via Docker Compose (optional service)

### 7.3 Key Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `rag_query_duration_seconds` | Histogram | config_id, agent_type |
| `rag_retrieval_duration_seconds` | Histogram | method, config_id |
| `rag_llm_tokens_total` | Counter | provider, model, type (prompt/completion) |
| `rag_ingestion_files_total` | Counter | config_id, status |
| `rag_guardrails_blocked_total` | Counter | reason (pii/injection/toxicity) |
| `rag_cache_hits_total` | Counter | cache_type (embedding/query) |

---

## 8. Deployment

### 8.1 Development (Docker Compose)

```bash
docker compose up -d                    # Full stack (11 containers)
docker compose up -d mongodb redis      # Infrastructure only (for local dev)
```

All services share `rag-network` bridge. MongoDB uses volume `mongodb_data`, Redis uses `redis_data`.

### 8.2 Production Considerations

- Nginx in front of gateway for TLS termination
- MongoDB Atlas or replica set for HA + vector search indexes
- Redis Sentinel or Cluster for HA
- Separate Celery worker scaling (independent of API)
- Environment-specific `.env` (never committed)
- Health check endpoints: `GET /health` (liveness), `GET /health/detailed` (readiness)

---

## 9. Architecture Decision Records (ADR)

### ADR-001: Shared Auth Library vs Per-Service Auth

**Context:** v1 had JWT creation in config-service and validation in gateway only. Ingestion and RAG services had zero auth awareness.

**Decision:** Create `shared/python/rag_config_common/auth/` with JWT decode, HMAC verification, and token blacklist client. All Python services use it.

**Rationale:** Defense in depth. Even if gateway is bypassed (misconfigured Docker network), services independently verify request authenticity.

### ADR-002: Redis for Token Blacklist vs MongoDB

**Decision:** Redis with TTL-based key expiry.

**Rationale:** Token blacklist is checked on every request. Redis SET/GET is O(1) and sub-millisecond. MongoDB would add unnecessary query latency to the hot path. TTL-based expiry means automatic cleanup — no maintenance jobs needed.

### ADR-003: Guardrails as Middleware vs Separate Service

**Decision:** Guardrails as a module within RAG service, not a separate microservice.

**Rationale:** Guardrails need access to query context, retrieved chunks, and generated responses. Running them in-process avoids an extra network hop per query. If guardrails become a bottleneck, they can be extracted later.

### ADR-004: RAGAS Inline vs Async Evaluation

**Decision:** Evaluation is async by default (non-blocking to query response). Synchronous evaluation available via dedicated `/evaluate` endpoint.

**Rationale:** RAGAS evaluation requires additional LLM calls (for faithfulness, relevance scoring). Adding 2-5s to every query response is unacceptable. Async evaluation logs results for later analysis without impacting UX.

### ADR-005: LangGraph over CrewAI/AutoGen

**Decision:** Stay with LangGraph as the agent framework for v2.

**Rationale:** LangGraph has the strongest ecosystem for custom RAG agents, supports subgraphs for composing the Adaptive RAG router, and offers built-in checkpointing for conversation memory. CrewAI/AutoGen are better for multi-agent chat but worse for structured RAG pipelines.

### ADR-006: MongoDB as Unified Store vs Dedicated Vector DB

**Decision:** Keep MongoDB as the primary store (documents + vectors + graph). Add Qdrant as an optional high-performance backend in a future release.

**Rationale:** MongoDB Atlas Vector Search is adequate for most workloads and eliminates operational complexity of a separate vector DB. For ColBERT multi-vector support or >1M vector scale, Qdrant would be added as a `VectorStoreProvider` option.

---

For deployment details, see [DEPLOYMENT.md](DEPLOYMENT.md).
For API documentation, see [API.md](API.md).
For the v2 implementation plan, see [tasks/v2-plan.md](../tasks/v2-plan.md).

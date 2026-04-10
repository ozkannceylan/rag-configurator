# Architecture — RAG Configurator v2

Low-code platform for building and deploying custom RAG pipelines. Four microservices behind a Go reverse proxy gateway, two Vue 3 frontends, MongoDB + Redis infrastructure.

## System Overview

```
                       +------------------+
                       |   Configurator   |
                       |    UI (:5173)    |
                       +--------+---------+
                                |
        +----------+    +-------v--------+    +-----------+
        | Sandbox  +--->+   Go Gateway   +<---+  External |
        | UI(:3001)|    |    (:8000)     |    |  Clients  |
        +----------+    +---+----+---+---+    +-----------+
                            |    |   |
              +-------------+    |   +-------------+
              |                  |                  |
     +--------v------+  +-------v-------+  +-------v-------+
     | Config Service |  |  Ingestion    |  |  RAG Service  |
     | (FastAPI:8001) |  |  Service      |  | (FastAPI:8003)|
     |                |  | (FastAPI:8002)|  |               |
     | - Auth (JWT)   |  | - Celery      |  | - 7 Agents    |
     | - Config CRUD  |  | - Processors  |  | - 4 Retrievers|
     | - Templates    |  | - Chunkers    |  | - 4 LLM       |
     | - YAML export  |  | - Embedders   |  |   Providers   |
     +-------+--------+  +---+---+-------+  | - RAGAS Eval  |
             |                |   |          | - Query Cache |
             |                |   |          +---+---+-------+
             |                |   |              |   |
             +-------+--------+---+--------------+   |
                     |                               |
               +-----v------+                  +-----v------+
               |  MongoDB    |                  |   Redis    |
               |  (:27017)   |                  |  (:6379)   |
               |             |                  |            |
               | - configs   |                  | - Celery   |
               | - users     |                  |   broker   |
               | - vectors   |                  | - Embedding|
               | - graphs    |                  |   cache    |
               | - evals     |                  | - Query    |
               +-------------+                  |   cache    |
                                                +------------+
```

## Service Details

### Gateway (Go/Gin — :8000)

- JWT validation (HS256, shared secret with Config Service)
- CORS handling with configurable origins
- Rate limiting per IP
- Reverse proxy to all backend services
- SSE/WebSocket passthrough for streaming
- Auth endpoints (`/api/v1/auth/*`) bypass JWT validation
- Sets `X-User-ID` header from JWT `sub` claim before proxying
- HMAC inter-service signing for backend-to-backend trust

### Config Service (FastAPI — :8001)

- User authentication: register, login, JWT refresh, logout with token blacklist
- RAG pipeline configuration CRUD
- Folder browsing and file scanning
- YAML/JSON config export/import
- Pipeline templates marketplace
- MongoDB repository pattern for data access

### Ingestion Service (FastAPI + Celery — :8002)

- Async document processing pipeline via Celery workers
- **Processors:** PDF (with Docling), DOCX, TXT, MD, HTML, Images (OCR)
- **Chunkers:** Recursive, Sentence, Semantic, RAPTOR (hierarchical), Late Interaction
- **Embedders:** OpenAI, Ollama, Cohere, Voyage, Jina
- Embedding cache (Redis) for deduplication
- Batch embedding with configurable batch sizes
- MongoDB vector storage with Atlas Search indexes
- Graph extraction (nodes + edges) for GraphRAG

### RAG Service (FastAPI — :8003)

- **7 Agent Types:**
  - Naive RAG — single retrieval + generation
  - ReAct — iterative reasoning and action
  - CRAG (Corrective RAG) — retrieval quality validation
  - Self-RAG — self-reflective generation with critique
  - Multi-Query — query expansion for broader retrieval
  - Plan-Solve — decompose complex queries into sub-tasks
  - GraphRAG — community-based summarization (Leiden algorithm)

- **4 Retrieval Strategies:** Vector, Keyword (Atlas Search), Graph, Hybrid

- **4 LLM Providers:** OpenAI, Anthropic, Ollama, vLLM

- SSE streaming via sse-starlette
- RAGAS evaluation (faithfulness, relevancy, precision, recall)
- Query response caching (Redis)
- Query lineage tracking

## Frontend Apps

### Configurator UI (Vue 3 + Tailwind + Headless UI — :5173)

9-step wizard for pipeline configuration:
1. Data Source
2. Folder Selection
3. RBAC
4. Models (LLM + Embedding)
5. Retrieval Strategy
6. Agent Type
7. Prompts
8. Advanced (Guardrails, Evaluation, Cache)
9. Review & Deploy

Pipeline templates marketplace for quick-start configs.

### Sandbox UI (Vue 3 + Tailwind + Naive UI — :3001)

- Chat interface for testing RAG pipelines
- SSE streaming with real-time token display
- Side-by-side comparison view (two configs, same query)
- Retrieval debugger (chunk scores, agent reasoning steps)
- Evaluation dashboard (RAGAS metrics over time)

## Cross-Cutting Concerns

### Security
- JWT authentication (HS256) with access/refresh tokens
- Token blacklist (Redis-backed with in-memory fallback)
- HMAC inter-service signing (gateway signs, services verify)
- RBAC per folder with configurable roles

### Observability
- OpenTelemetry distributed tracing (OTLP exporter)
- Langfuse LLM observability (optional, via `--profile observability`)
- Custom metrics: query duration, retrieval time, LLM tokens, cache hits, evaluation scores
- Structured logging across all services

### Caching (Redis)
- **Embedding cache:** `emb_cache:{sha256(text)}` — avoids recomputing embeddings for duplicate content
- **Query cache:** `query_cache:{config_id}:{sha256(query)}` — caches full RAG responses with configurable TTL
- Graceful degradation — cache failures never block the pipeline

### Data Storage (MongoDB)
- **Collections:** users, configs, documents, chunks, graph_nodes, graph_edges, community_summaries, ingestion_jobs, evaluations, query_lineage
- Vector search via Atlas Search indexes
- Connection pools: `maxPoolSize=50, minPoolSize=5` across all services

## Shared Packages

### `rag_config_common` (Python — `shared/python/`)
- **Models:** Pydantic models for configs, users, enums
- **Auth:** HMAC verification, JWT utilities, token blacklist, service auth middleware
- **Observability:** OTel tracing setup, Langfuse integration, custom metrics
- **Cache:** Embedding cache, query cache

### `shared/typescript/` 
- TypeScript interfaces mirroring Python models
- Enum definitions for frontend type safety

## Key Patterns

- **Factory pattern:** Processors, chunkers, embedders, retrievers, LLM clients, agents
- **Repository pattern:** MongoDB access through `app/db/repositories/`
- **API response envelope:** `{"success": bool, "data": ..., "error": ..., "meta": ...}`
- **Shared models:** Always import from `rag_config_common`, never redefine

## Ports

| Service | Port |
|---------|------|
| Gateway | 8000 |
| Config Service | 8001 |
| Ingestion Service | 8002 |
| RAG Service | 8003 |
| Configurator UI | 5173 |
| Sandbox UI | 3001 |
| MongoDB | 27017 |
| Redis | 6379 |
| Langfuse (optional) | 3003 |
| Mongo Express (dev) | 8081 |
| Redis Commander (dev) | 8082 |

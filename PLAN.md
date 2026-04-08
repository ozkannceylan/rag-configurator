# RAG Configurator - Complete Project Plan & Architecture

## Executive Summary

RAG Configurator is a full-stack application for creating, managing, and testing Retrieval-Augmented Generation (RAG) pipelines through a visual interface. Users configure data sources, retrieval strategies, LLM models, and agent behaviors without writing code, then test their configurations in a sandbox chat environment.

**Timeline**: 14 weeks  
**Team**: Solo developer with AI assistance (Claude Code)

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Data Models](#data-models)
5. [API Reference](#api-reference)
6. [Phase Breakdown](#phase-breakdown)
7. [Implementation Checklist](#implementation-checklist)

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                  │
├─────────────────────────────────┬───────────────────────────────────────────┤
│     Configurator UI (3000)      │         Sandbox UI (3001)                 │
│     Vue 3 + TypeScript          │         Vue 3 + TypeScript                │
│     - Config Wizard             │         - Chat Interface                  │
│     - Dashboard                 │         - Source Viewer                   │
│     - Ingestion Monitor         │         - Debug Panel                     │
└─────────────────────────────────┴───────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY (8000)                                │
│                              Go + Gin                                        │
│     - JWT Authentication        - Rate Limiting                             │
│     - Dynamic Routing           - CORS Handling                             │
│     - WebSocket Proxy           - Request Logging                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌───────────────────────┐ ┌───────────────────┐ ┌───────────────────────────┐
│  Config Service (8001)│ │Ingestion Svc(8002)│ │    RAG Service (8003)     │
│  FastAPI + MongoDB    │ │ FastAPI + Celery  │ │   FastAPI + LangGraph     │
│                       │ │                   │ │                           │
│  - User Management    │ │  - Doc Processing │ │  - Vector Retrieval       │
│  - Config CRUD        │ │  - Chunking       │ │  - Keyword Retrieval      │
│  - YAML Export/Import │ │  - Embedding      │ │  - Graph Retrieval        │
│  - Folder Scanning    │ │  - Graph Building │ │  - Hybrid Fusion          │
│                       │ │                   │ │  - 6 Agent Templates      │
│                       │ │                   │ │  - Streaming Responses    │
└───────────────────────┘ └───────────────────┘ └───────────────────────────┘
          │                       │                         │
          └───────────────────────┼─────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                        │
├─────────────────────────────────┬───────────────────────────────────────────┤
│         MongoDB (27017)         │           Redis (6379)                    │
│  - users                        │  - Celery Broker                          │
│  - configs                      │  - Session Cache                          │
│  - documents                    │  - Rate Limit State                       │
│  - chunks (+ vectors)           │                                           │
│  - graph_nodes                  │                                           │
│  - graph_edges                  │                                           │
│  - ingestion_jobs               │                                           │
│  - conversations                │                                           │
└─────────────────────────────────┴───────────────────────────────────────────┘
```

### Request Flow

```
1. User Request
   Browser → Configurator UI / Sandbox UI

2. API Call
   UI → Gateway:8000 (JWT validation, rate limiting)

3. Service Routing
   Gateway → Config Service:8001  (config management)
           → Ingestion Service:8002 (document processing)
           → RAG Service:8003 (query processing)

4. Data Access
   Services → MongoDB (persistent data)
            → Redis (caching, task queue)

5. Response
   Service → Gateway → UI → User
```

### Ingestion Pipeline

```
┌──────────┐    ┌───────────┐    ┌─────────┐    ┌──────────┐    ┌─────────────┐
│  Files   │───▶│ Processor │───▶│ Chunker │───▶│ Embedder │───▶│ Vector Store│
│ PDF/DOCX │    │ Text Ext. │    │ Split   │    │ OpenAI/  │    │  MongoDB    │
│ TXT/MD   │    │ OCR       │    │ Overlap │    │ Ollama   │    │             │
└──────────┘    └───────────┘    └─────────┘    └──────────┘    └─────────────┘
                                                      │
                                                      ▼
                                               ┌─────────────┐
                                               │ Graph Store │ (optional)
                                               │  Entities   │
                                               │  Relations  │
                                               └─────────────┘
```

### RAG Query Flow

```
┌───────┐    ┌───────────┐    ┌───────────┐    ┌─────────┐    ┌──────────┐
│ Query │───▶│ Retriever │───▶│   Agent   │───▶│   LLM   │───▶│ Response │
└───────┘    │ Vector/   │    │ Naive/    │    │ OpenAI/ │    │ + Sources│
             │ Keyword/  │    │ ReAct/    │    │ Claude/ │    │          │
             │ Graph/    │    │ CRAG/     │    │ Ollama  │    │          │
             │ Hybrid    │    │ Self-RAG  │    │         │    │          │
             └───────────┘    └───────────┘    └─────────┘    └──────────┘
```

---

## Tech Stack

### Backend Services

| Component | Technology | Purpose |
|-----------|------------|---------|
| Gateway | Go 1.22, Gin | API routing, auth, rate limiting |
| Config Service | Python 3.11, FastAPI | User/config management |
| Ingestion Service | Python 3.11, FastAPI, Celery | Document processing |
| RAG Service | Python 3.11, FastAPI, LangGraph | Query processing |

### Frontend Applications

| Component | Technology | Purpose |
|-----------|------------|---------|
| Configurator UI | Vue 3, TypeScript, Vite | Config wizard |
| Sandbox UI | Vue 3, TypeScript, Vite | Chat testing |

### Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| Database | MongoDB 7 | Document storage, vector search |
| Cache/Queue | Redis 7 | Celery broker, caching |
| Reverse Proxy | Nginx | Production routing, SSL |
| Containers | Docker, Docker Compose | Deployment |

### Key Libraries

| Category | Libraries |
|----------|-----------|
| LLM | OpenAI, Anthropic, Ollama, vLLM |
| Embeddings | OpenAI, sentence-transformers |
| Document Processing | Docling, PyMuPDF, python-docx |
| Agent Framework | LangGraph, LangChain-core |
| Authentication | python-jose, golang-jwt |
| UI Components | Tailwind CSS, Headless UI |

---

## Project Structure

```
rag-configurator/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── cd.yml
│       └── release.yml
│
├── shared/
│   ├── schemas/
│   │   └── rag_config.yaml          # OpenAPI schema
│   ├── python/
│   │   └── rag_config_common/       # Shared Python package
│   │       ├── models/
│   │       │   ├── config.py        # Pydantic models
│   │       │   └── user.py
│   │       └── utils/
│   └── typescript/
│       └── src/
│           └── types.ts             # TypeScript interfaces
│
├── gateway/
│   ├── cmd/server/
│   │   └── main.go
│   ├── internal/
│   │   ├── config/
│   │   ├── middleware/
│   │   │   ├── auth.go
│   │   │   ├── cors.go
│   │   │   ├── ratelimit.go
│   │   │   ├── logging.go
│   │   │   └── recovery.go
│   │   ├── handlers/
│   │   │   ├── health.go
│   │   │   └── websocket.go
│   │   ├── router/
│   │   │   └── router.go
│   │   └── proxy/
│   │       └── proxy.go
│   ├── pkg/
│   │   └── jwt/
│   │       └── jwt.go
│   ├── go.mod
│   └── Dockerfile
│
├── services/
│   ├── config-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/v1/
│   │   │   │   ├── router.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── configs.py
│   │   │   │   └── folders.py
│   │   │   ├── core/
│   │   │   │   ├── settings.py
│   │   │   │   ├── security.py
│   │   │   │   └── database.py
│   │   │   ├── repositories/
│   │   │   │   ├── user.py
│   │   │   │   └── config.py
│   │   │   └── services/
│   │   │       ├── auth.py
│   │   │       └── folder_scanner.py
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── ingestion-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/v1/
│   │   │   │   └── ingest.py
│   │   │   ├── core/
│   │   │   │   ├── settings.py
│   │   │   │   └── celery_app.py
│   │   │   ├── tasks/
│   │   │   │   └── ingestion_task.py
│   │   │   ├── processors/
│   │   │   │   ├── base.py
│   │   │   │   ├── factory.py
│   │   │   │   ├── text.py
│   │   │   │   ├── pdf.py
│   │   │   │   ├── image.py
│   │   │   │   └── docx.py
│   │   │   ├── chunkers/
│   │   │   │   ├── base.py
│   │   │   │   ├── factory.py
│   │   │   │   ├── recursive.py
│   │   │   │   ├── semantic.py
│   │   │   │   └── document.py
│   │   │   ├── embedders/
│   │   │   │   ├── base.py
│   │   │   │   ├── factory.py
│   │   │   │   ├── openai.py
│   │   │   │   ├── ollama.py
│   │   │   │   └── huggingface.py
│   │   │   ├── graph/
│   │   │   │   ├── extractor.py
│   │   │   │   └── builder.py
│   │   │   └── storage/
│   │   │       ├── vector_store.py
│   │   │       └── graph_store.py
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── rag-service/
│       ├── app/
│       │   ├── main.py
│       │   ├── api/v1/
│       │   │   ├── query.py
│       │   │   ├── chat.py
│       │   │   └── stream.py
│       │   ├── core/
│       │   │   └── settings.py
│       │   ├── retrieval/
│       │   │   ├── base.py
│       │   │   ├── factory.py
│       │   │   ├── vector.py
│       │   │   ├── keyword.py
│       │   │   ├── graph.py
│       │   │   └── hybrid.py
│       │   ├── llm/
│       │   │   ├── base.py
│       │   │   ├── factory.py
│       │   │   ├── openai.py
│       │   │   ├── anthropic.py
│       │   │   ├── ollama.py
│       │   │   └── vllm.py
│       │   ├── agents/
│       │   │   ├── base.py
│       │   │   ├── factory.py
│       │   │   ├── naive.py
│       │   │   ├── react.py
│       │   │   ├── crag.py
│       │   │   ├── self_rag.py
│       │   │   ├── multi_query.py
│       │   │   └── plan_solve.py
│       │   ├── prompts/
│       │   │   ├── manager.py
│       │   │   └── templates/
│       │   └── rbac/
│       │       └── enforcer.py
│       ├── tests/
│       ├── requirements.txt
│       └── Dockerfile
│
├── apps/
│   ├── configurator-ui/
│   │   ├── src/
│   │   │   ├── main.ts
│   │   │   ├── App.vue
│   │   │   ├── api/
│   │   │   ├── stores/
│   │   │   ├── router/
│   │   │   ├── views/
│   │   │   ├── components/
│   │   │   │   ├── common/
│   │   │   │   ├── wizard/
│   │   │   │   ├── pipeline/
│   │   │   │   └── ingestion/
│   │   │   ├── composables/
│   │   │   └── types/
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.js
│   │   └── package.json
│   │
│   └── sandbox-ui/
│       ├── src/
│       │   ├── main.ts
│       │   ├── App.vue
│       │   ├── api/
│       │   ├── stores/
│       │   ├── router/
│       │   ├── views/
│       │   ├── components/
│       │   │   ├── common/
│       │   │   ├── chat/
│       │   │   └── sidebar/
│       │   └── composables/
│       ├── index.html
│       ├── vite.config.ts
│       └── package.json
│
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
│       └── nginx.conf
│
├── docs/
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
│
├── demo/
│   ├── sample-docs/
│   ├── sample-configs/
│   └── scripts/
│
├── tests/
│   ├── e2e/
│   └── performance/
│
├── scripts/
│   ├── setup.sh
│   └── seed-demo.sh
│
├── CLAUDE.md
├── CHANGELOG.md
├── LICENSE
├── Makefile
└── README.md
```

---

## Data Models

### User

```python
class User:
    id: str                    # MongoDB ObjectId
    email: str                 # Unique, indexed
    name: str
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
```

### RAG Configuration

```python
class RAGConfig:
    id: str
    user_id: str               # Owner
    name: str
    description: str
    status: ConfigStatus       # draft, ready, processing, error
    
    data_source: DataSourceConfig
    rbac: RBACConfig
    models: ModelsConfig
    retrieval: RetrievalConfig
    chunking: ChunkingConfig
    agent: AgentConfig
    prompts: PromptConfig
    
    stats: ConfigStats         # After ingestion
    created_at: datetime
    updated_at: datetime

class DataSourceConfig:
    type: "local" | "s3"
    base_path: str
    file_types: List[str]      # ["pdf", "txt", "md", "docx"]
    recursive: bool = True
    # S3 specific
    bucket: str
    prefix: str
    region: str
    credentials: S3Credentials

class RBACConfig:
    enabled: bool = False
    roles: List[str]
    folder_permissions: Dict[str, List[str]]  # folder_path -> roles
    default_role: str

class ModelsConfig:
    llm: LLMConfig
    embedding: EmbeddingConfig

class LLMConfig:
    provider: "openai" | "anthropic" | "ollama" | "vllm"
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 2048
    base_url: str              # For Ollama/vLLM
    api_key: str               # Encrypted

class EmbeddingConfig:
    provider: "openai" | "ollama" | "huggingface"
    model_name: str
    dimensions: int
    base_url: str

class RetrievalConfig:
    method: "naive" | "keyword" | "hybrid" | "graph" | "hybrid_graph"
    vector: VectorSearchConfig
    keyword: KeywordSearchConfig
    graph: GraphSearchConfig

class VectorSearchConfig:
    top_k: int = 5
    score_threshold: float = 0.7

class KeywordSearchConfig:
    enabled: bool = False
    top_k: int = 5
    use_fuzzy: bool = True
    boost_factor: float = 1.0

class GraphSearchConfig:
    enabled: bool = False
    max_depth: int = 2
    schema: GraphSchema

class GraphSchema:
    auto_extract: bool = True
    nodes: List[NodeType]
    relations: List[RelationType]

class ChunkingConfig:
    strategy: "recursive" | "semantic" | "document"
    chunk_size: int = 512
    chunk_overlap: int = 50
    separators: List[str]

class AgentConfig:
    template: "naive_rag" | "react" | "crag" | "self_rag" | "multi_query" | "plan_solve"
    max_iterations: int = 5
    enable_streaming: bool = True

class PromptConfig:
    system_prompt: str
    rag_prompt_template: str   # Must contain {context} and {query}
```

### Document & Chunks

```python
class Document:
    id: str
    config_id: str
    file_path: str
    file_name: str
    file_type: str
    content_hash: str          # For deduplication
    processed_at: datetime
    metadata: dict

class Chunk:
    id: str
    config_id: str
    document_id: str
    content: str
    embedding: List[float]     # Vector
    chunk_index: int
    metadata: dict             # Includes folder_path for RBAC
```

### Graph Entities

```python
class GraphNode:
    id: str
    config_id: str
    node_type: str
    name: str
    properties: dict
    embedding: List[float]
    source_chunks: List[str]

class GraphEdge:
    id: str
    config_id: str
    relation_type: str
    source_node: str
    target_node: str
    properties: dict
```

### Ingestion Job

```python
class IngestionJob:
    id: str
    config_id: str
    task_id: str               # Celery task ID
    status: "pending" | "processing" | "completed" | "failed" | "cancelled"
    progress: int              # 0-100
    current_step: str
    error: str
    started_at: datetime
    completed_at: datetime
    stats: IngestionStats

class IngestionStats:
    total_files: int
    processed_files: int
    failed_files: int
    total_chunks: int
    total_embeddings: int
    graph_nodes: int
    graph_edges: int
    processing_time_seconds: float
```

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Register new user |
| POST | /api/v1/auth/login | Login, get tokens |
| POST | /api/v1/auth/refresh | Refresh access token |
| POST | /api/v1/auth/logout | Invalidate tokens |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/users/me | Get current user |
| PUT | /api/v1/users/me | Update current user |
| DELETE | /api/v1/users/me | Delete account |

### Configurations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/configs | List configs (paginated) |
| POST | /api/v1/configs | Create config |
| GET | /api/v1/configs/:id | Get config |
| PUT | /api/v1/configs/:id | Update config |
| DELETE | /api/v1/configs/:id | Delete config |
| POST | /api/v1/configs/:id/duplicate | Duplicate config |
| GET | /api/v1/configs/:id/export | Export as YAML |
| POST | /api/v1/configs/import | Import from YAML |

### Folders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/folders/scan | Scan folder structure |

### Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/ingest/:config_id/start | Start ingestion |
| GET | /api/v1/ingest/:config_id/status | Get status |
| POST | /api/v1/ingest/:config_id/cancel | Cancel job |
| POST | /api/v1/ingest/:config_id/retry | Retry failed job |
| GET | /api/v1/ingest/:config_id/logs | Get logs |
| GET | /api/v1/ingest/:config_id/stats | Get statistics |

### RAG Queries

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/query | Single query |
| POST | /api/v1/chat | Chat with history |
| GET | /api/v1/stream | SSE streaming |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Gateway health |
| GET | /health/detailed | All services health |

---

## Phase Breakdown

### Phase 0: Project Setup (Week 1)

| Task | Description |
|------|-------------|
| P0-1 | Repository setup, monorepo structure |
| P0-2 | Docker Compose for dev environment |
| P0-3 | Shared schemas (OpenAPI YAML) |
| P0-4 | Python package (rag_config_common) |
| P0-5 | TypeScript types generation |
| P0-6 | Makefile with common commands |

### Phase 1: Config Service (Weeks 2-3)

| Task | Description |
|------|-------------|
| P1-1 | FastAPI scaffold, settings |
| P1-2 | MongoDB connection with motor |
| P1-3 | User repository (CRUD) |
| P1-4 | Auth endpoints (register, login, refresh) |
| P1-5 | JWT middleware |
| P1-6 | Config repository |
| P1-7 | Config endpoints (CRUD) |
| P1-8 | Folder scanner service |
| P1-9 | Folder endpoints |
| P1-10 | YAML export/import |
| P1-11 | Unit and integration tests |

### Phase 2: Go Gateway (Week 4)

| Task | Description |
|------|-------------|
| P2-1 | Gateway scaffold, config loading |
| P2-2 | Router setup with route groups |
| P2-3 | JWT middleware (Phase 1 compatible) |
| P2-4 | Reverse proxy to backend services |
| P2-5 | CORS middleware |
| P2-6 | Rate limiter (per-IP) |
| P2-7 | Health endpoints |
| P2-8 | WebSocket handler |
| P2-9 | Integration tests |

### Phase 3: Ingestion Service (Weeks 5-6)

| Task | Description |
|------|-------------|
| P3-1 | Service scaffold, Celery setup |
| P3-2 | Document processors (PDF, DOCX, TXT) |
| P3-3 | Text chunkers (recursive, semantic) |
| P3-4 | Embedding providers (OpenAI, Ollama, HF) |
| P3-5 | Vector store (MongoDB) |
| P3-6 | Graph extractor and builder |
| P3-7 | Ingestion orchestration task |
| P3-8 | API endpoints |
| P3-9 | Tests |

### Phase 4: RAG Service (Weeks 7-8)

| Task | Description |
|------|-------------|
| P4-1 | Service scaffold |
| P4-2 | Vector retriever |
| P4-3 | Keyword retriever |
| P4-4 | Graph retriever |
| P4-5 | Hybrid retriever with RRF |
| P4-6 | LLM integrations (OpenAI, Anthropic, Ollama, vLLM) |
| P4-7 | Prompt manager |
| P4-8 | Naive RAG agent |
| P4-9 | ReAct agent |
| P4-10 | CRAG agent |
| P4-11 | Self-RAG agent |
| P4-12 | Multi-Query agent |
| P4-13 | Plan-Solve agent |
| P4-14 | RBAC enforcement |
| P4-15 | API endpoints (query, chat, stream) |
| P4-16 | Tests |

### Phase 5: Configurator UI (Weeks 9-11)

| Task | Description |
|------|-------------|
| P5-1 | Vue project setup |
| P5-2 | Pinia stores (auth, config, wizard) |
| P5-3 | API service layer |
| P5-4 | Router with auth guards |
| P5-5 | Login/register page |
| P5-6 | Dashboard with config list |
| P5-7 | Wizard container and navigation |
| P5-8 | Step 1: Data Source |
| P5-9 | Step 2: RBAC |
| P5-10 | Step 3: Models |
| P5-11 | Step 4: Retrieval |
| P5-12 | Step 4b: Graph Schema |
| P5-13 | Step 5: Agent |
| P5-14 | Step 6: Prompts |
| P5-15 | Step 7: Review |
| P5-16 | Pipeline preview visualization |
| P5-17 | Ingestion progress monitor |
| P5-18 | Component and E2E tests |

### Phase 6: Sandbox UI (Week 12)

| Task | Description |
|------|-------------|
| P6-1 | Vue project setup |
| P6-2 | Chat interface container |
| P6-3 | Message components with markdown |
| P6-4 | Sources panel |
| P6-5 | Debug panel |
| P6-6 | SSE streaming integration |
| P6-7 | Config selector |
| P6-8 | Tests |

### Phase 7: Integration & Polish (Weeks 13-14)

| Task | Description |
|------|-------------|
| P7-1 | End-to-end tests |
| P7-2 | Documentation |
| P7-3 | Production Docker setup |
| P7-4 | CI/CD pipeline (GitHub Actions) |
| P7-5 | Performance testing (Locust) |
| P7-6 | Security audit |
| P7-7 | Demo data and examples |
| P7-8 | v1.0.0 release |

---

## Implementation Checklist

### Phase 0: Project Setup

- [ ] P0-1 Repository Setup
- [ ] P0-2 Docker Compose
- [ ] P0-3 Shared Schemas
- [ ] P0-4 Python Package
- [ ] P0-5 TypeScript Types
- [ ] P0-6 Makefile

### Phase 1: Config Service

- [ ] P1-1 FastAPI Scaffold
- [ ] P1-2 MongoDB Connection
- [ ] P1-3 User Repository
- [ ] P1-4 Auth Endpoints
- [ ] P1-5 JWT Middleware
- [ ] P1-6 Config Repository
- [ ] P1-7 Config Endpoints
- [ ] P1-8 Folder Scanner
- [ ] P1-9 Folder Endpoints
- [ ] P1-10 YAML Export/Import
- [ ] P1-11 Tests

### Phase 2: Go Gateway

- [ ] P2-1 Gateway Scaffold
- [ ] P2-2 Router Setup
- [ ] P2-3 JWT Middleware
- [ ] P2-4 Reverse Proxy
- [ ] P2-5 CORS Middleware
- [ ] P2-6 Rate Limiter
- [ ] P2-7 Health Endpoints
- [ ] P2-8 WebSocket Handler
- [ ] P2-9 Tests

### Phase 3: Ingestion Service

- [ ] P3-1 Service Scaffold
- [ ] P3-2 Document Processors
- [ ] P3-3 Text Chunkers
- [ ] P3-4 Embedding Providers
- [ ] P3-5 Vector Store
- [ ] P3-6 Graph Extractor
- [ ] P3-7 Ingestion Task
- [ ] P3-8 API Endpoints
- [ ] P3-9 Tests

### Phase 4: RAG Service

- [ ] P4-1 Service Scaffold
- [ ] P4-2 Vector Retriever
- [ ] P4-3 Keyword Retriever
- [ ] P4-4 Graph Retriever
- [ ] P4-5 Hybrid Retriever
- [ ] P4-6 LLM Integrations
- [ ] P4-7 Prompt Manager
- [ ] P4-8 Naive RAG Agent
- [ ] P4-9 ReAct Agent
- [ ] P4-10 CRAG Agent
- [ ] P4-11 Self-RAG Agent
- [ ] P4-12 Multi-Query Agent
- [ ] P4-13 Plan-Solve Agent
- [ ] P4-14 RBAC Enforcement
- [ ] P4-15 API Endpoints
- [ ] P4-16 Tests

### Phase 5: Configurator UI

- [ ] P5-1 Vue Project Setup
- [ ] P5-2 Pinia Stores
- [ ] P5-3 API Service
- [ ] P5-4 Router & Auth
- [ ] P5-5 Login Page
- [ ] P5-6 Dashboard
- [ ] P5-7 Wizard Container
- [ ] P5-8 Step: Data Source
- [ ] P5-9 Step: RBAC
- [ ] P5-10 Step: Models
- [ ] P5-11 Step: Retrieval
- [ ] P5-12 Step: Graph
- [ ] P5-13 Step: Agent
- [ ] P5-14 Step: Prompts
- [ ] P5-15 Step: Review
- [ ] P5-16 Pipeline Preview
- [ ] P5-17 Ingestion Progress
- [ ] P5-18 Tests

### Phase 6: Sandbox UI

- [ ] P6-1 Vue Project Setup
- [ ] P6-2 Chat Interface
- [ ] P6-3 Message Components
- [ ] P6-4 Sources Panel
- [ ] P6-5 Debug Panel
- [ ] P6-6 SSE Streaming
- [ ] P6-7 Config Selector
- [ ] P6-8 Tests

### Phase 7: Integration & Polish

- [ ] P7-1 E2E Testing
- [ ] P7-2 Documentation
- [ ] P7-3 Production Docker
- [ ] P7-4 CI/CD Pipeline
- [ ] P7-5 Performance Testing
- [ ] P7-6 Security Audit
- [ ] P7-7 Demo Data
- [ ] P7-8 v1.0.0 Release

---

## Environment Variables

```bash
# ===================
# Gateway
# ===================
GATEWAY_PORT=8000
ENVIRONMENT=development
LOG_LEVEL=info
JWT_SECRET_KEY=your-256-bit-secret-key
JWT_ALGORITHM=HS256
CONFIG_SERVICE_URL=http://localhost:8001
INGESTION_SERVICE_URL=http://localhost:8002
RAG_SERVICE_URL=http://localhost:8003
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
RATE_LIMIT_RPS=100

# ===================
# Config Service
# ===================
CONFIG_SERVICE_PORT=8001
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=rag_configurator
JWT_SECRET_KEY=your-256-bit-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ===================
# Ingestion Service
# ===================
INGESTION_SERVICE_PORT=8002
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=rag_configurator
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434

# ===================
# RAG Service
# ===================
RAG_SERVICE_PORT=8003
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=rag_configurator
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434
VLLM_BASE_URL=http://localhost:8080

# ===================
# Frontend Apps
# ===================
VITE_API_URL=http://localhost:8000
```

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/your-org/rag-configurator.git
cd rag-configurator

# 2. Copy environment file
cp .env.example .env
# Edit .env with your API keys

# 3. Start all services
docker-compose up -d

# 4. Access applications
# Configurator UI: http://localhost:3000
# Sandbox UI: http://localhost:3001
# API Gateway: http://localhost:8000

# 5. Create your first config
# - Register at http://localhost:3000
# - Use the wizard to create a RAG config
# - Run ingestion
# - Test in sandbox

# 6. Run tests
make test
```

---

## License

MIT License - See LICENSE file for details.
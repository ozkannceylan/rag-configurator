# RAG Configurator

**A full-stack platform for building, configuring, and deploying custom RAG (Retrieval-Augmented Generation) pipelines through a visual interface — no code required.**

Design your retrieval strategy, pick your LLM, ingest documents, and chat with your knowledge base — all from the browser.

---

## Highlights

- **Visual Pipeline Builder** — Step-by-step wizard to configure chunking, embedding, retrieval, and generation
- **6 Agent Architectures** — Naive RAG, ReAct, Corrective RAG, Self-RAG, Multi-Query, Plan-and-Solve
- **4 LLM Providers** — OpenAI, Anthropic, Ollama (local GPU), vLLM (self-hosted)
- **Hybrid Retrieval** — Vector, keyword, graph, and hybrid search with re-ranking
- **Real-time Chat** — SSE streaming responses with source citations
- **Local File Browsing** — Mount and browse host folders directly from the UI for document ingestion
- **Async Ingestion** — Celery workers process documents in the background with live progress tracking
- **Multi-tenant Auth** — JWT authentication with role-based access control

---

## Architecture

```
                        ┌──────────────────────────────────┐
                        │         Client Layer              │
                        │  Configurator UI  │  Sandbox UI   │
                        │    (Vue 3)        │   (Vue 3)     │
                        └────────┬─────────────┬────────────┘
                                 │             │
                        ┌────────▼─────────────▼────────────┐
                        │     API Gateway (Go + Gin)         │
                        │  JWT Auth · Rate Limiting · CORS   │
                        │  Reverse Proxy · SSE Streaming     │
                        └──┬──────────┬──────────┬──────────┘
                           │          │          │
              ┌────────────▼┐  ┌──────▼───────┐  ┌▼────────────────┐
              │ Config       │  │ Ingestion    │  │ RAG Service     │
              │ Service      │  │ Service      │  │ (LangGraph)     │
              │ (FastAPI)    │  │ (FastAPI)    │  │ (FastAPI)       │
              │              │  │              │  │                 │
              │ • Users/Auth │  │ • Processors │  │ • Retrievers    │
              │ • Config CRUD│  │ • Chunkers   │  │ • LLM Clients   │
              │ • Folder API │  │ • Embedders  │  │ • 6 Agent Types │
              │ • RBAC       │  │ • Celery     │  │ • SSE Streaming │
              └──────┬───────┘  └──────┬───────┘  └──────┬──────────┘
                     │                 │                  │
              ┌──────▼─────────────────▼──────────────────▼──────┐
              │                   Data Layer                      │
              │  MongoDB 7.0        │  Redis 7                   │
              │  • Configs & Users  │  • Celery Broker           │
              │  • Chunks & Vectors │  • Task Results            │
              │  • Ingestion State  │  • Session Cache           │
              └──────────────────────────────────────────────────┘
```

### Services

| Service | Tech | Port | Role |
|---------|------|------|------|
| **Gateway** | Go 1.24, Gin | 8000 | Auth, routing, rate-limiting, SSE proxy |
| **Config Service** | Python 3.11, FastAPI | 8001 | User management, pipeline configs, folder browsing |
| **Ingestion Service** | Python 3.11, FastAPI, Celery | 8002 | Document parsing, chunking, embedding |
| **RAG Service** | Python 3.11, FastAPI, LangGraph | 8003 | Retrieval, generation, agent orchestration |
| **Configurator UI** | Vue 3, TypeScript, Vite | 5173 | Pipeline configuration wizard |
| **Sandbox UI** | Vue 3, TypeScript, Vite | 3001 | Chat interface for testing pipelines |
| **MongoDB** | 7.0 | 27017 | Primary datastore + vector search |
| **Redis** | 7-alpine | 6379 | Task queue broker + caching |

---

## Tech Stack

### Backend

| | Technology | Purpose |
|---|---|---|
| **Language** | Go 1.24 | API Gateway |
| **Language** | Python 3.11 | All microservices |
| **Web Framework** | FastAPI 0.111 | REST APIs with async support |
| **Agent Framework** | LangGraph 0.2 | Stateful agent orchestration |
| **LLM Libraries** | LangChain, langchain-openai, langchain-anthropic | LLM provider abstraction |
| **Task Queue** | Celery 5.4 + Redis | Async document ingestion |
| **Database** | MongoDB 7.0 + Motor 3.4 | Async document store + vector index |
| **Auth** | JWT (python-jose, golang-jwt/v5) | Stateless authentication |
| **Validation** | Pydantic 2.x | Schema validation across all services |
| **HTTP Router** | Gin 1.10 | High-performance Go HTTP framework |
| **Doc Parsing** | Unstructured 0.14, PyMuPDF, python-docx | PDF, DOCX, HTML, TXT, MD |
| **OCR** | pytesseract + Pillow | Scanned document extraction |
| **Embeddings** | OpenAI, Ollama, sentence-transformers | Multiple embedding providers |
| **Streaming** | sse-starlette | Server-Sent Events for real-time chat |
| **Logging** | zerolog (Go), structlog (Python) | Structured JSON logging |

### Frontend

| | Technology | Purpose |
|---|---|---|
| **Framework** | Vue 3.4 (Composition API) | Reactive UI |
| **Language** | TypeScript 5.4 | Type-safe frontend code |
| **Build** | Vite 5.2 | Fast dev server + production builds |
| **State** | Pinia 2.1 | Centralized state management |
| **Styling** | Tailwind CSS 3.4 | Utility-first CSS |
| **Components** | Headless UI 1.7 | Accessible, unstyled primitives |
| **Icons** | Heroicons 2.1 | SVG icon set |
| **Validation** | vee-validate + zod | Form validation with schema inference |
| **Markdown** | marked + highlight.js | Chat message rendering with syntax highlighting |

### Infrastructure

| | Technology | Purpose |
|---|---|---|
| **Containers** | Docker + Docker Compose | Service orchestration |
| **Database** | MongoDB 7.0 | Document store with vector search indexes |
| **Cache/Queue** | Redis 7 | Celery broker + result backend |
| **Reverse Proxy** | Nginx | Production routing + TLS termination |

---

## RAG Capabilities

### Agent Architectures

| Agent | Description |
|-------|-------------|
| **Naive RAG** | Retrieve → Generate. Simple and fast baseline. |
| **ReAct** | Reasoning + Acting loop with tool use for complex queries |
| **Corrective RAG (CRAG)** | Evaluates retrieval quality, self-corrects with web fallback |
| **Self-RAG** | Iterative self-reflection — generates, critiques, and refines |
| **Multi-Query** | Expands user query into multiple perspectives, parallel retrieval |
| **Plan-and-Solve** | Decomposes complex questions into sub-tasks, solves step-by-step |

### Retrieval Methods

| Method | Description |
|--------|-------------|
| **Vector Search** | Semantic similarity via MongoDB Atlas vector index (HNSW) |
| **Keyword Search** | Full-text search with Atlas Search |
| **Hybrid Search** | Reciprocal Rank Fusion of vector + keyword results |
| **Graph Search** | Entity-relationship traversal for connected knowledge |

### Chunking Strategies

| Strategy | Description |
|----------|-------------|
| **Recursive** | Recursive character splitting with configurable overlap |
| **Semantic** | Embedding-based boundary detection for coherent chunks |
| **Document** | Preserves document structure as single chunks |

### Embedding Providers

| Provider | Models |
|----------|--------|
| **OpenAI** | text-embedding-3-small, text-embedding-3-large, ada-002 |
| **Ollama** | nomic-embed-text, all-minilm, mxbai-embed-large (local) |
| **HuggingFace** | Any sentence-transformers model (local) |

### LLM Providers

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4, GPT-3.5-turbo |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku |
| **Ollama** | Llama 3, Mistral, Qwen, Phi — any GGUF model (local, GPU) |
| **vLLM** | Any HuggingFace model via vLLM server |

---

## Quick Start

### Prerequisites

- **Docker Desktop** (with Docker Compose v2)
- **Ollama** (optional, for local LLM — [install here](https://ollama.com))

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/rag-configurator.git
cd rag-configurator
cp .env.example .env
```

Edit `.env` — at minimum set:

```env
# For local LLM (Ollama)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# To browse local folders from the UI
LOCAL_DATA_PATH=/path/to/your/documents
```

### 2. Pull Ollama models (if using local LLM)

```bash
ollama pull qwen3:4b          # or any chat model
ollama pull nomic-embed-text   # embedding model
```

### 3. Start all services

```bash
docker compose up -d
```

### 4. Create a demo user

```bash
# Linux/macOS
./demo/scripts/seed-demo.sh

# Windows PowerShell
./create_demo_user.ps1
```

### 5. Open the UI

| URL | Description |
|-----|-------------|
| http://localhost:5173 | **Configurator UI** — Create and manage RAG pipelines |
| http://localhost:3001 | **Sandbox UI** — Chat with your configured pipelines |
| http://localhost:8081 | **Mongo Express** — Browse database (dev) |
| http://localhost:8082 | **Redis Commander** — Inspect queues (dev) |

### First Steps

1. Log in at `http://localhost:5173`
2. Click **New Configuration** → follow the wizard
3. Set a data source path → **Browse** your local folders or use the included sample docs
4. Click **Scan** → select folders → **Start Ingestion**
5. Once ingestion completes, open `http://localhost:3001` → select your config → start chatting

---

## Project Structure

```
rag-configurator/
├── gateway/                        # Go API Gateway
│   ├── cmd/server/                 #   Entrypoint
│   ├── internal/
│   │   ├── middleware/             #   JWT auth, CORS, rate-limit
│   │   ├── router/                #   Route definitions
│   │   └── proxy/                 #   Reverse proxy + SSE support
│   └── go.mod
│
├── services/
│   ├── config-service/             # Python — Config & Auth
│   │   └── app/
│   │       ├── api/v1/             #   REST endpoints
│   │       ├── services/           #   Business logic
│   │       ├── schemas/            #   Pydantic models
│   │       └── db/                 #   MongoDB repositories
│   │
│   ├── ingestion-service/          # Python — Document Processing
│   │   └── app/
│   │       ├── processors/         #   PDF, DOCX, TXT, MD, HTML parsers
│   │       ├── chunkers/           #   Recursive, Semantic, Document
│   │       ├── embedders/          #   OpenAI, Ollama, HuggingFace
│   │       └── tasks/              #   Celery async tasks
│   │
│   └── rag-service/                # Python — RAG Runtime
│       └── app/
│           ├── agents/             #   Naive, ReAct, CRAG, Self-RAG, Multi-Query, Plan-Solve
│           ├── retrieval/          #   Vector, Keyword, Hybrid, Graph
│           ├── llm/                #   OpenAI, Anthropic, Ollama, vLLM clients
│           └── api/v1/             #   Query + SSE stream endpoints
│
├── apps/
│   ├── configurator-ui/            # Vue 3 — Pipeline Configuration Wizard
│   │   └── src/
│   │       ├── views/              #   Wizard steps, config detail
│   │       ├── components/         #   Reusable UI components
│   │       ├── stores/             #   Pinia state management
│   │       └── api/                #   API client layer
│   │
│   └── sandbox-ui/                 # Vue 3 — Chat Testing Interface
│       └── src/
│           ├── views/              #   Chat view with streaming
│           └── components/         #   Config selector, message list
│
├── shared/python/                  # Shared Pydantic models across services
├── demo/
│   ├── sample-docs/                # Example documents for testing
│   ├── sample-configs/             # Pre-built pipeline configurations
│   └── scripts/                    # Seeding and demo setup scripts
│
├── infrastructure/                 # MongoDB init scripts, Nginx config
├── docker-compose.yml              # Full development stack (11 containers)
└── .env.example                    # Environment variable template
```

---

## Development

### Local Setup (without Docker)

**Prerequisites**: Python 3.11+, Node.js 20+, Go 1.24+, MongoDB 7.0+, Redis 7+

```bash
# Backend services
pip install -e shared/python
pip install -r services/config-service/requirements.txt
pip install -r services/ingestion-service/requirements.txt
pip install -r services/rag-service/requirements.txt

# Gateway
cd gateway && go mod download && cd ..

# Frontend
cd apps/configurator-ui && npm install && cd ../..
cd apps/sandbox-ui && npm install && cd ../..

# Start infrastructure only
docker compose up -d mongodb redis

# Run services individually in separate terminals
uvicorn app.main:app --port 8001 --reload   # config-service
uvicorn app.main:app --port 8002 --reload   # ingestion-service
uvicorn app.main:app --port 8003 --reload   # rag-service
go run cmd/server/main.go                    # gateway
npm run dev                                  # each UI app
```

---

## Configuration

All settings are managed through `.env`. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama endpoint for local LLM |
| `LOCAL_DATA_PATH` | `.` | Host folder mounted into containers for browsing |
| `OPENAI_API_KEY` | — | OpenAI API key (if using OpenAI models) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (if using Claude) |
| `JWT_SECRET_KEY` | (dev default) | **Change in production** |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |

See [.env.example](.env.example) for the full list.

---

## API Overview

All endpoints are served through the gateway at `http://localhost:8000/api/v1/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register new user |
| `POST` | `/auth/login` | Login, returns JWT |
| `GET` | `/configs` | List pipeline configurations |
| `POST` | `/configs` | Create a new pipeline config |
| `GET` | `/configs/:id` | Get config details |
| `POST` | `/folders/browse` | Browse server-side folders |
| `POST` | `/folders/scan` | Scan folder for documents |
| `POST` | `/ingestion/start` | Start document ingestion |
| `GET` | `/ingestion/:id/status` | Get ingestion progress |
| `POST` | `/query` | Single-turn RAG query |
| `POST` | `/stream` | SSE streaming chat |

---

## License

[Apache License 2.0](LICENSE)

---

## Acknowledgments

Built with [FastAPI](https://fastapi.tiangolo.com), [LangGraph](https://github.com/langchain-ai/langgraph), [Vue 3](https://vuejs.org), [Gin](https://gin-gonic.com), [MongoDB](https://www.mongodb.com), and [Ollama](https://ollama.com).

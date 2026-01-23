# RAG Configurator - Master System Architecture

## PROJECT_PLAN.md

---

## 1. System Overview

### 1.1 Project Purpose

The **RAG Configurator** is an open-source, low-code platform that enables users to design, configure, and deploy custom Retrieval-Augmented Generation (RAG) pipelines through a visual interface. Instead of writing code for each RAG implementation, users configure their pipeline through a step-by-step wizard, and the system generates a production-ready API.

### 1.2 Core Value Proposition

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   USER CONFIGURES                        SYSTEM GENERATES                   │
│   ───────────────                        ────────────────                   │
│   • Data sources & folders         →     • Chunked & embedded vectors       │
│   • RBAC rules                     →     • Access-controlled queries        │
│   • Retrieval strategy             →     • Optimized retrieval pipeline     │
│   • Agent template                 →     • LangGraph workflow               │
│   • Prompts                        →     • Ready-to-use REST API            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Target Users

| User Type | Use Case |
|-----------|----------|
| ML Engineers | Rapid prototyping of RAG systems without boilerplate |
| Enterprises | Deploy secure, RBAC-controlled knowledge bases |
| Startups | Quick MVP for AI-powered search/chat products |
| Researchers | Experiment with different RAG architectures |

---

## 2. Tech Stack

### 2.1 Final Stack Decisions

| Layer | Technology | Version | Justification |
|-------|------------|---------|---------------|
| **Frontend** | Vue 3 + TypeScript | 3.4.x | Team familiarity, excellent DX |
| **UI Components** | Naive UI | 2.38.x | Clean design, Vue-native, MIT license |
| **State Management** | Pinia | 2.1.x | Official Vue state management |
| **API Gateway** | Go + Gin | 1.22.x / 1.9.x | Performance, team experience |
| **Python Services** | FastAPI | 0.111.x | Async, auto-docs, Pydantic |
| **Agent Framework** | LangGraph | 0.2.x | State machine agents, configurable |
| **Task Queue** | Celery + Redis | 5.4.x / 7.x | Async ingestion, proven at scale |
| **Database** | MongoDB Atlas | 7.x | Vector + Graph + Documents unified |
| **Search** | Atlas Search | - | Keyword search, part of MongoDB |
| **Auth** | Simple JWT | - | Lightweight, open-source friendly |
| **Prompt Tracking** | MLflow | 2.14.x | Open-source, self-hostable |
| **Containerization** | Docker + Compose | 24.x | Development and deployment |

### 2.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ┌─────────────────────────────────────────────────────────────────┐      │
│    │                        FRONTEND LAYER                           │      │
│    │  ┌───────────────────────┐    ┌───────────────────────┐         │      │
│    │  │   Vue 3 Configurator  │    │    Vue 3 Sandbox      │         │      │
│    │  │   (Config Wizard)     │    │    (Test Chat UI)     │         │      │
│    │  └───────────┬───────────┘    └───────────┬───────────┘         │      │
│    └──────────────┼────────────────────────────┼─────────────────────┘      │
│                   │                            │                            │
│                   └──────────┬─────────────────┘                            │
│                              ▼                                              │
│    ┌─────────────────────────────────────────────────────────────────┐      │
│    │                      GO API GATEWAY                             │      │
│    │  • JWT Authentication    • Rate Limiting    • Request Routing   │      │
│    │  • CORS Handling         • Logging          • Health Checks     │      │
│    └─────────────────────────────┬───────────────────────────────────┘      │
│                                  │                                          │
│              ┌───────────────────┼───────────────────┐                      │
│              ▼                   ▼                   ▼                      │
│    ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐           │
│    │  Config Service  │ │ Ingestion Service│ │   RAG Service    │           │
│    │    (FastAPI)     │ │ (FastAPI+Celery) │ │    (FastAPI)     │           │
│    │                  │ │                  │ │                  │           │
│    │ • Config CRUD    │ │ • File Processing│ │ • Query Handling │           │
│    │ • User Mgmt      │ │ • Chunking       │ │ • Retrieval      │           │
│    │ • Folder Scan    │ │ • Embedding      │ │ • Agent Exec     │           │
│    │ • YAML Export    │ │ • Graph Building │ │ • Streaming      │           │
│    └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘           │
│             │                    │                    │                     │
│             └────────────────────┼────────────────────┘                     │
│                                  ▼                                          │
│    ┌─────────────────────────────────────────────────────────────────┐      │
│    │                      DATA LAYER                                 │      │
│    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │      │
│    │  │   MongoDB   │  │   Redis     │  │   MLflow    │              │      │
│    │  │   Atlas     │  │             │  │             │              │      │
│    │  │             │  │ • Celery    │  │ • Prompts   │              │      │
│    │  │ • Configs   │  │   Broker    │  │ • Versions  │              │      │
│    │  │ • Users     │  │ • Cache     │  │ • Tracking  │              │      │
│    │  │ • Vectors   │  │ • Sessions  │  │             │              │      │
│    │  │ • Graphs    │  │             │  │             │              │      │
│    │  └─────────────┘  └─────────────┘  └─────────────┘              │      │
│    └─────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Configuration Flow (Sequential Dependency Chain)

This is the critical ordering that prevents circular dependencies:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION WIZARD FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 1: DATA SOURCE                                                 │    │
│  │ ─────────────────────                                               │    │
│  │ Input:  Path (local/cloud), credentials                             │    │
│  │ Action: System scans folders, detects file types                    │    │
│  │ Output: Folder tree with detected data types                        │    │
│  │                                                                     │    │
│  │ Unlocks: Nothing (this is the foundation)                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 2: RBAC (Optional)                                             │    │
│  │ ─────────────────────────                                           │    │
│  │ Depends: Step 1 (needs folder list)                                 │    │
│  │ Input:  Role definitions, folder-role mappings                      │    │
│  │ Output: RBAC configuration                                          │    │
│  │                                                                     │    │
│  │ Skip if: User doesn't need access control                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 3: MODEL SELECTION                                             │    │
│  │ ────────────────────────                                            │    │
│  │ Depends: Step 1 (data types determine if multimodal needed)         │    │
│  │ Input:  LLM provider, model, embedding model                        │    │
│  │ Output: LLM config, Embedding config                                │    │
│  │                                                                     │    │
│  │ Conditional UI:                                                     │    │
│  │   IF images/PDFs detected → Show "Enable Vision LLM" toggle         │    │
│  │   IF PDFs detected → Show "Enable Docling" toggle                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 4: RETRIEVAL STRATEGY                                          │    │
│  │ ───────────────────────────                                         │    │
│  │ Depends: Step 3 (embedding model affects vector search)             │    │
│  │ Input:  Method selection (naive/hybrid/graph/all)                   │    │
│  │ Output: Retrieval config                                            │    │
│  │                                                                     │    │
│  │ Conditional UI:                                                     │    │
│  │   IF "graph" selected → Show Graph Schema Editor (Step 4b)          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                          ┌────────┴────────┐                                │
│                          ▼                 ▼                                │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐         │
│  │ STEP 4b: GRAPH SCHEMA       │  │ (Skip if no graph selected)  │         │
│  │ ─────────────────────────── │  │                              │         │
│  │ Depends: Step 4 graph=true  │  │                              │         │
│  │ Input: Node types, Relations│  │                              │         │
│  │ Output: Graph schema config │  │                              │         │
│  │                             │  │                              │         │
│  │ Option: "Auto-extract"      │  │                              │         │
│  │ lets LLM determine schema   │  │                              │         │
│  └──────────────────────────────┘  └──────────────────────────────┘         │
│                          │                 │                                │
│                          └────────┬────────┘                                │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 5: AGENT TEMPLATE                                              │    │
│  │ ───────────────────────                                             │    │
│  │ Depends: Step 4 (retrieval method affects available agents)         │    │
│  │ Input:  Template selection from predefined list                     │    │
│  │ Output: Agent configuration                                         │    │
│  │                                                                     │    │
│  │ Templates:                                                          │    │
│  │   • Naive RAG (simple retrieve-and-generate)                        │    │
│  │   • ReAct (reasoning + acting loop)                                 │    │
│  │   • CRAG (corrective RAG with self-check)                           │    │
│  │   • Self-RAG (self-reflective retrieval)                            │    │
│  │   • Multi-Query (query expansion)                                   │    │
│  │   • Plan-and-Solve (complex reasoning)                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 6: PROMPTS                                                     │    │
│  │ ─────────────                                                       │    │
│  │ Depends: Step 5 (agent template has default prompts)                │    │
│  │ Input:  System prompt, RAG prompt, Judge prompts (optional)         │    │
│  │ Output: Prompt configuration                                        │    │
│  │                                                                     │    │
│  │ Features:                                                           │    │
│  │   • Pre-filled from template defaults                               │    │
│  │   • Variable highlighting ({context}, {query}, etc.)                │    │
│  │   • Prompt testing with sample query                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 7: REVIEW & DEPLOY                                             │    │
│  │ ────────────────────────                                            │    │
│  │ Depends: All previous steps                                         │    │
│  │ Input:  Final review of all settings                                │    │
│  │ Action: "Load Data & Start RAG API" button                          │    │
│  │ Output: Running RAG API endpoint                                    │    │
│  │                                                                     │    │
│  │ Process:                                                            │    │
│  │   1. Validate complete configuration                                │    │
│  │   2. Start async ingestion job                                      │    │
│  │   3. Show progress (chunking → embedding → indexing)                │    │
│  │   4. Expose API endpoint when ready                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. File Structure

```
rag-configurator/
│
├── README.md                           # Project overview, quick start
├── LICENSE                             # Apache 2.0 (recommended for self-branding)
├── CONTRIBUTING.md                     # Contribution guidelines
├── docker-compose.yml                  # Development environment
├── docker-compose.prod.yml             # Production environment
├── Makefile                            # Common commands
├── .env.example                        # Environment template
├── .gitignore
│
│
├── docs/                               # Documentation
│   ├── ARCHITECTURE.md                 # This document
│   ├── API_REFERENCE.md                # API documentation
│   ├── CONFIGURATION_SCHEMA.md         # Config schema docs
│   ├── DEPLOYMENT.md                   # Deployment guide
│   ├── DEVELOPMENT.md                  # Dev setup guide
│   └── assets/
│       └── diagrams/
│           ├── architecture.png
│           ├── config-flow.png
│           └── data-flow.png
│
│
├── gateway/                            # Go API Gateway
│   ├── cmd/
│   │   └── server/
│   │       └── main.go                 # Entry point
│   │
│   ├── internal/
│   │   ├── config/
│   │   │   └── config.go               # App configuration
│   │   │
│   │   ├── middleware/
│   │   │   ├── auth.go                 # JWT validation
│   │   │   ├── cors.go                 # CORS handling
│   │   │   ├── ratelimit.go            # Rate limiting
│   │   │   ├── logging.go              # Request logging
│   │   │   └── recovery.go             # Panic recovery
│   │   │
│   │   ├── handlers/
│   │   │   ├── health.go               # Health check endpoints
│   │   │   ├── auth.go                 # Login/register proxy
│   │   │   ├── config.go               # Config service proxy
│   │   │   ├── ingestion.go            # Ingestion service proxy
│   │   │   ├── rag.go                  # RAG service proxy
│   │   │   └── websocket.go            # WebSocket for streaming
│   │   │
│   │   ├── router/
│   │   │   └── router.go               # Route definitions
│   │   │
│   │   └── proxy/
│   │       └── proxy.go                # Reverse proxy logic
│   │
│   ├── pkg/
│   │   ├── jwt/
│   │   │   └── jwt.go                  # JWT utilities
│   │   └── response/
│   │       └── response.go             # Standard response format
│   │
│   ├── go.mod
│   ├── go.sum
│   └── Dockerfile
│
│
├── services/                           # Python Microservices
│   │
│   │
│   ├── config-service/                 # Configuration Management
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                 # FastAPI entry
│   │   │   │
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── deps.py             # Dependencies (DB, auth)
│   │   │   │   └── v1/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── router.py       # API router
│   │   │   │       ├── auth.py         # Auth endpoints
│   │   │   │       ├── users.py        # User management
│   │   │   │       ├── configs.py      # Config CRUD
│   │   │   │       ├── folders.py      # Folder scanning
│   │   │   │       └── export.py       # YAML export/import
│   │   │   │
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── settings.py         # Pydantic settings
│   │   │   │   ├── security.py         # Password hashing, JWT
│   │   │   │   └── exceptions.py       # Custom exceptions
│   │   │   │
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py             # User model
│   │   │   │   └── config.py           # Config model (references shared)
│   │   │   │
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py             # Login/register schemas
│   │   │   │   ├── user.py             # User request/response
│   │   │   │   ├── config.py           # Config request/response
│   │   │   │   └── folder.py           # Folder scan schemas
│   │   │   │
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth_service.py     # Auth logic
│   │   │   │   ├── user_service.py     # User CRUD
│   │   │   │   ├── config_service.py   # Config CRUD
│   │   │   │   ├── folder_service.py   # Folder scanning
│   │   │   │   └── export_service.py   # YAML export/import
│   │   │   │
│   │   │   └── db/
│   │   │       ├── __init__.py
│   │   │       ├── mongodb.py          # MongoDB connection
│   │   │       └── repositories/
│   │   │           ├── __init__.py
│   │   │           ├── base.py         # Base repository
│   │   │           ├── user_repo.py    # User repository
│   │   │           └── config_repo.py  # Config repository
│   │   │
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py             # Pytest fixtures
│   │   │   ├── test_auth.py
│   │   │   ├── test_configs.py
│   │   │   └── test_folders.py
│   │   │
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   │
│   ├── ingestion-service/              # Data Processing
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                 # FastAPI entry (trigger endpoints)
│   │   │   ├── worker.py               # Celery app definition
│   │   │   │
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── deps.py
│   │   │   │   └── v1/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── router.py
│   │   │   │       ├── ingest.py       # Trigger ingestion
│   │   │   │       └── status.py       # Job status
│   │   │   │
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── settings.py
│   │   │   │   └── celery_app.py       # Celery configuration
│   │   │   │
│   │   │   ├── tasks/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ingest_task.py      # Main orchestration task
│   │   │   │   ├── process_task.py     # File processing task
│   │   │   │   ├── chunk_task.py       # Chunking task
│   │   │   │   ├── embed_task.py       # Embedding task
│   │   │   │   ├── index_task.py       # Vector indexing task
│   │   │   │   └── graph_task.py       # Graph building task
│   │   │   │
│   │   │   ├── processors/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py             # Abstract processor
│   │   │   │   ├── factory.py          # Processor factory
│   │   │   │   ├── text.py             # Plain text processor
│   │   │   │   ├── pdf.py              # PDF processor
│   │   │   │   ├── docx.py             # Word doc processor
│   │   │   │   ├── image.py            # Image processor
│   │   │   │   └── multimodal.py       # Vision LLM processor
│   │   │   │
│   │   │   ├── chunkers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py             # Abstract chunker
│   │   │   │   ├── factory.py          # Chunker factory
│   │   │   │   ├── recursive.py        # Recursive text splitter
│   │   │   │   ├── semantic.py         # Semantic chunker
│   │   │   │   └── document.py         # Document-aware chunker
│   │   │   │
│   │   │   ├── embedders/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py             # Abstract embedder
│   │   │   │   ├── factory.py          # Embedder factory
│   │   │   │   ├── openai.py           # OpenAI embeddings
│   │   │   │   ├── ollama.py           # Ollama embeddings
│   │   │   │   └── huggingface.py      # HuggingFace embeddings
│   │   │   │
│   │   │   ├── graph/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── extractor.py        # Entity/relation extraction
│   │   │   │   ├── builder.py          # Graph construction
│   │   │   │   └── schemas.py          # Graph data models
│   │   │   │
│   │   │   ├── storage/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── vector_store.py     # MongoDB Vector operations
│   │   │   │   ├── graph_store.py      # MongoDB Graph operations
│   │   │   │   └── document_store.py   # Document metadata
│   │   │   │
│   │   │   └── db/
│   │   │       ├── __init__.py
│   │   │       └── mongodb.py
│   │   │
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py
│   │   │   ├── test_processors.py
│   │   │   ├── test_chunkers.py
│   │   │   └── test_embedders.py
│   │   │
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   │
│   └── rag-service/                    # RAG API Runtime
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py                 # FastAPI entry
│       │   │
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   ├── deps.py
│       │   │   └── v1/
│       │   │       ├── __init__.py
│       │   │       ├── router.py
│       │   │       ├── query.py        # Single query endpoint
│       │   │       ├── chat.py         # Chat with history
│       │   │       └── stream.py       # Streaming responses
│       │   │
│       │   ├── core/
│       │   │   ├── __init__.py
│       │   │   ├── settings.py
│       │   │   ├── rbac.py             # RBAC enforcement
│       │   │   └── context.py          # Request context (user, config)
│       │   │
│       │   ├── retrieval/
│       │   │   ├── __init__.py
│       │   │   ├── base.py             # Abstract retriever
│       │   │   ├── factory.py          # Retriever factory
│       │   │   ├── vector.py           # Vector search
│       │   │   ├── keyword.py          # Atlas Search
│       │   │   ├── graph.py            # Graph traversal
│       │   │   └── hybrid.py           # Combined retrieval
│       │   │
│       │   ├── agents/
│       │   │   ├── __init__.py
│       │   │   ├── base.py             # Abstract agent
│       │   │   ├── factory.py          # Agent factory
│       │   │   │
│       │   │   ├── templates/          # Predefined agent configs
│       │   │   │   ├── __init__.py
│       │   │   │   ├── naive_rag.py
│       │   │   │   ├── react.py
│       │   │   │   ├── crag.py
│       │   │   │   ├── self_rag.py
│       │   │   │   ├── multi_query.py
│       │   │   │   └── plan_solve.py
│       │   │   │
│       │   │   └── graphs/             # LangGraph implementations
│       │   │       ├── __init__.py
│       │   │       ├── naive.py        # Simple retrieve-generate
│       │   │       ├── react.py        # ReAct loop
│       │   │       ├── crag.py         # Corrective RAG
│       │   │       ├── self_rag.py     # Self-reflective RAG
│       │   │       ├── multi_query.py  # Query expansion
│       │   │       ├── plan_solve.py   # Plan and solve
│       │   │       └── nodes.py        # Shared graph nodes
│       │   │
│       │   ├── llm/
│       │   │   ├── __init__.py
│       │   │   ├── base.py             # Abstract LLM interface
│       │   │   ├── factory.py          # LLM factory
│       │   │   ├── openai.py
│       │   │   ├── ollama.py
│       │   │   ├── vllm.py
│       │   │   └── anthropic.py
│       │   │
│       │   ├── prompts/
│       │   │   ├── __init__.py
│       │   │   ├── manager.py          # Load prompts from config/MLflow
│       │   │   └── templates/
│       │   │       ├── __init__.py
│       │   │       ├── system.py
│       │   │       ├── rag.py
│       │   │       └── judge.py
│       │   │
│       │   ├── evaluation/
│       │   │   ├── __init__.py
│       │   │   ├── judge.py            # LLM-as-judge
│       │   │   └── metrics.py          # Evaluation metrics
│       │   │
│       │   └── db/
│       │       ├── __init__.py
│       │       └── mongodb.py
│       │
│       ├── tests/
│       │   ├── __init__.py
│       │   ├── conftest.py
│       │   ├── test_retrieval.py
│       │   ├── test_agents.py
│       │   └── test_query.py
│       │
│       ├── requirements.txt
│       ├── pyproject.toml
│       └── Dockerfile
│
│
├── ui/                                 # Vue 3 Frontend
│   │
│   ├── configurator/                   # Main Config UI
│   │   ├── src/
│   │   │   ├── main.ts                 # App entry
│   │   │   ├── App.vue                 # Root component
│   │   │   │
│   │   │   ├── assets/
│   │   │   │   ├── styles/
│   │   │   │   │   ├── main.css
│   │   │   │   │   └── variables.css
│   │   │   │   └── images/
│   │   │   │
│   │   │   ├── components/
│   │   │   │   ├── common/
│   │   │   │   │   ├── AppHeader.vue
│   │   │   │   │   ├── AppSidebar.vue
│   │   │   │   │   ├── AppFooter.vue
│   │   │   │   │   ├── LoadingOverlay.vue
│   │   │   │   │   ├── ErrorBoundary.vue
│   │   │   │   │   └── ConfirmDialog.vue
│   │   │   │   │
│   │   │   │   ├── wizard/
│   │   │   │   │   ├── WizardContainer.vue    # Step wizard wrapper
│   │   │   │   │   ├── WizardProgress.vue     # Progress indicator
│   │   │   │   │   ├── WizardNavigation.vue   # Next/Back buttons
│   │   │   │   │   └── StepIndicator.vue
│   │   │   │   │
│   │   │   │   ├── steps/
│   │   │   │   │   ├── Step1DataSource.vue
│   │   │   │   │   ├── Step2RBAC.vue
│   │   │   │   │   ├── Step3ModelSelection.vue
│   │   │   │   │   ├── Step4Retrieval.vue
│   │   │   │   │   ├── Step4bGraphSchema.vue
│   │   │   │   │   ├── Step5AgentTemplate.vue
│   │   │   │   │   ├── Step6Prompts.vue
│   │   │   │   │   └── Step7Review.vue
│   │   │   │   │
│   │   │   │   ├── forms/
│   │   │   │   │   ├── DataSourceForm.vue
│   │   │   │   │   ├── RoleForm.vue
│   │   │   │   │   ├── FolderPermissionForm.vue
│   │   │   │   │   ├── LLMConfigForm.vue
│   │   │   │   │   ├── EmbeddingConfigForm.vue
│   │   │   │   │   ├── RetrievalConfigForm.vue
│   │   │   │   │   ├── GraphNodeForm.vue
│   │   │   │   │   ├── GraphRelationForm.vue
│   │   │   │   │   └── PromptEditorForm.vue
│   │   │   │   │
│   │   │   │   └── visualizers/
│   │   │   │       ├── FolderTree.vue
│   │   │   │       ├── PipelinePreview.vue
│   │   │   │       ├── GraphSchemaPreview.vue
│   │   │   │       └── ConfigSummary.vue
│   │   │   │
│   │   │   ├── views/
│   │   │   │   ├── LoginView.vue
│   │   │   │   ├── RegisterView.vue
│   │   │   │   ├── DashboardView.vue         # List of configs
│   │   │   │   ├── ConfigWizardView.vue      # Wizard host
│   │   │   │   ├── ConfigDetailView.vue      # View/edit existing
│   │   │   │   └── SettingsView.vue
│   │   │   │
│   │   │   ├── stores/
│   │   │   │   ├── index.ts                  # Store exports
│   │   │   │   ├── auth.ts                   # Auth state
│   │   │   │   ├── config.ts                 # Current config being edited
│   │   │   │   ├── wizard.ts                 # Wizard step state
│   │   │   │   └── ui.ts                     # UI state (modals, etc.)
│   │   │   │
│   │   │   ├── composables/
│   │   │   │   ├── useAuth.ts
│   │   │   │   ├── useConfig.ts
│   │   │   │   ├── useWizard.ts
│   │   │   │   ├── useValidation.ts
│   │   │   │   └── useApi.ts
│   │   │   │
│   │   │   ├── services/
│   │   │   │   ├── api.ts                    # Axios instance
│   │   │   │   ├── authApi.ts
│   │   │   │   ├── configApi.ts
│   │   │   │   ├── folderApi.ts
│   │   │   │   └── ingestionApi.ts
│   │   │   │
│   │   │   ├── types/
│   │   │   │   ├── index.ts
│   │   │   │   ├── config.ts                 # Config types
│   │   │   │   ├── user.ts
│   │   │   │   ├── api.ts
│   │   │   │   └── wizard.ts
│   │   │   │
│   │   │   ├── utils/
│   │   │   │   ├── validation.ts
│   │   │   │   ├── formatters.ts
│   │   │   │   └── constants.ts
│   │   │   │
│   │   │   └── router/
│   │   │       └── index.ts
│   │   │
│   │   ├── public/
│   │   │   └── favicon.ico
│   │   │
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.js
│   │   └── Dockerfile
│   │
│   │
│   └── sandbox/                        # Test Chat UI
│       ├── src/
│       │   ├── main.ts
│       │   ├── App.vue
│       │   │
│       │   ├── components/
│       │   │   ├── ChatContainer.vue
│       │   │   ├── MessageList.vue
│       │   │   ├── MessageBubble.vue
│       │   │   ├── ChatInput.vue
│       │   │   ├── SourcesPanel.vue
│       │   │   ├── DebugPanel.vue
│       │   │   └── ConfigSelector.vue
│       │   │
│       │   ├── views/
│       │   │   ├── ChatView.vue
│       │   │   └── LoginView.vue
│       │   │
│       │   ├── stores/
│       │   │   ├── auth.ts
│       │   │   ├── chat.ts
│       │   │   └── config.ts
│       │   │
│       │   ├── services/
│       │   │   ├── api.ts
│       │   │   └── ragApi.ts
│       │   │
│       │   ├── types/
│       │   │   └── index.ts
│       │   │
│       │   └── router/
│       │       └── index.ts
│       │
│       ├── package.json
│       ├── vite.config.ts
│       └── Dockerfile
│
│
├── shared/                             # Shared Code
│   │
│   ├── schemas/                        # JSON Schemas (source of truth)
│   │   ├── config.schema.json
│   │   ├── user.schema.json
│   │   ├── rbac.schema.json
│   │   └── api-response.schema.json
│   │
│   ├── python/                         # Shared Python Package
│   │   ├── rag_config_common/
│   │   │   ├── __init__.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py           # Main config model
│   │   │   │   ├── user.py
│   │   │   │   ├── enums.py
│   │   │   │   └── rbac.py
│   │   │   ├── exceptions.py
│   │   │   └── utils.py
│   │   ├── setup.py
│   │   └── pyproject.toml
│   │
│   └── typescript/                     # Shared TypeScript Package
│       ├── src/
│       │   ├── index.ts
│       │   ├── config.ts
│       │   ├── user.ts
│       │   └── enums.ts
│       ├── package.json
│       └── tsconfig.json
│
│
├── prompts/                            # Prompt Templates
│   ├── agents/
│   │   ├── naive_rag.yaml
│   │   ├── react.yaml
│   │   ├── crag.yaml
│   │   ├── self_rag.yaml
│   │   ├── multi_query.yaml
│   │   └── plan_solve.yaml
│   │
│   ├── system/
│   │   └── default.yaml
│   │
│   └── judge/
│       ├── relevance.yaml
│       ├── faithfulness.yaml
│       └── answer_quality.yaml
│
│
├── scripts/                            # Utility Scripts
│   ├── setup.sh                        # Initial setup
│   ├── dev.sh                          # Start dev environment
│   ├── test.sh                         # Run all tests
│   ├── build.sh                        # Build all images
│   ├── lint.sh                         # Lint all code
│   ├── generate-types.py               # Generate types from JSON schema
│   ├── seed-db.py                      # Seed database
│   └── create-indexes.py               # Create MongoDB indexes
│
│
└── infrastructure/                     # Infrastructure
    ├── docker/
    │   ├── gateway.Dockerfile
    │   ├── config-service.Dockerfile
    │   ├── ingestion-service.Dockerfile
    │   ├── rag-service.Dockerfile
    │   ├── configurator-ui.Dockerfile
    │   └── sandbox-ui.Dockerfile
    │
    ├── mongo/
    │   ├── init-db.js                  # Initialize databases
    │   ├── create-indexes.js           # Create indexes
    │   └── create-search-index.js      # Atlas Search indexes
    │
    └── nginx/
        └── nginx.conf                  # Production reverse proxy
```

---

## 5. Interface Definitions

### 5.1 Core Configuration Model

```python
# shared/python/rag_config_common/models/config.py

"""
This is the SINGLE SOURCE OF TRUTH for configuration structure.
All services import from this package.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== ENUMS ====================

class DataSourceType(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"


class DataType(str, Enum):
    TEXT = "text"
    PDF = "pdf"
    IMAGE = "image"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    MARKDOWN = "markdown"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"
    VLLM = "vllm"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"


class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"


class RetrievalMethod(str, Enum):
    NAIVE = "naive"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    GRAPH = "graph"
    HYBRID_GRAPH = "hybrid_graph"


class AgentTemplate(str, Enum):
    NAIVE_RAG = "naive_rag"
    REACT = "react"
    CRAG = "crag"
    SELF_RAG = "self_rag"
    MULTI_QUERY = "multi_query"
    PLAN_SOLVE = "plan_solve"


class ChunkingStrategy(str, Enum):
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    DOCUMENT = "document"


class IngestionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ==================== STEP 1: DATA SOURCE ====================

class FolderConfig(BaseModel):
    """Configuration for a single data folder"""
    path: str = Field(..., description="Relative path from base")
    name: str = Field(..., description="Display name")
    detected_types: List[DataType] = Field(
        default_factory=list,
        description="Auto-detected file types"
    )
    allowed_roles: List[str] = Field(
        default=["*"],
        description="Roles that can access this folder (* = all)"
    )
    recursive: bool = Field(
        default=True,
        description="Include subfolders"
    )
    file_patterns: List[str] = Field(
        default=["*"],
        description="Glob patterns for file matching"
    )
    file_count: int = Field(default=0, description="Number of files detected")


class DataSourceConfig(BaseModel):
    """Step 1: Data source configuration"""
    type: DataSourceType
    base_path: str = Field(..., description="Root path for data")
    credentials: Optional[Dict[str, str]] = Field(
        default=None,
        description="Cloud credentials (encrypted)"
    )
    folders: List[FolderConfig] = Field(default_factory=list)
    has_multimodal: bool = Field(
        default=False,
        description="True if images/complex PDFs detected"
    )


# ==================== STEP 2: RBAC ====================

class RoleConfig(BaseModel):
    """Single role definition"""
    name: str = Field(..., description="Role identifier")
    description: str = Field(default="")
    allowed_folders: List[str] = Field(
        default=["*"],
        description="Folder paths this role can access"
    )
    can_query: bool = Field(default=True)
    can_view_sources: bool = Field(default=True)
    rate_limit: Optional[int] = Field(
        default=None,
        description="Max queries per minute"
    )


class RBACConfig(BaseModel):
    """Step 2: RBAC configuration (optional)"""
    enabled: bool = Field(default=False)
    roles: List[RoleConfig] = Field(default_factory=list)
    default_role: str = Field(default="user")


# ==================== STEP 3: MODEL SELECTION ====================

class LLMConfig(BaseModel):
    """LLM provider configuration"""
    provider: LLMProvider
    model_name: str
    base_url: Optional[str] = Field(
        default=None,
        description="For Ollama/vLLM/custom endpoints"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key (encrypted in storage)"
    )
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1)
    is_multimodal: bool = Field(default=False)


class EmbeddingConfig(BaseModel):
    """Embedding model configuration"""
    provider: EmbeddingProvider
    model_name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    dimensions: int = Field(default=1536)


class DocumentProcessingConfig(BaseModel):
    """Document processing options"""
    use_docling: bool = Field(
        default=False,
        description="Use Docling for PDF structure extraction"
    )
    use_vision_llm: bool = Field(
        default=False,
        description="Use vision LLM for images/complex docs"
    )
    vision_llm: Optional[LLMConfig] = None
    ocr_enabled: bool = Field(default=True)


class ModelConfig(BaseModel):
    """Step 3: Combined model configuration"""
    llm: LLMConfig
    embedding: EmbeddingConfig
    document_processing: DocumentProcessingConfig = Field(
        default_factory=DocumentProcessingConfig
    )


# ==================== STEP 4: RETRIEVAL ====================

class VectorSearchConfig(BaseModel):
    """Vector search settings"""
    enabled: bool = True
    top_k: int = Field(default=5, ge=1, le=100)
    score_threshold: float = Field(default=0.7, ge=0, le=1)


class KeywordSearchConfig(BaseModel):
    """Atlas Search / keyword settings"""
    enabled: bool = False
    top_k: int = Field(default=5, ge=1, le=100)
    use_fuzzy: bool = True
    boost_factor: float = Field(
        default=1.0,
        description="Weight for hybrid scoring"
    )


class GraphSearchConfig(BaseModel):
    """Graph RAG settings"""
    enabled: bool = False
    max_depth: int = Field(default=2, ge=1, le=5)
    top_k: int = Field(default=5, ge=1, le=100)


class GraphSchemaNode(BaseModel):
    """Node type definition for knowledge graph"""
    name: str = Field(..., description="Node type name (e.g., Person, Company)")
    description: str = Field(default="")
    properties: List[str] = Field(
        default_factory=list,
        description="Expected properties"
    )


class GraphSchemaRelation(BaseModel):
    """Relation type definition for knowledge graph"""
    name: str = Field(..., description="Relation name (e.g., WORKS_FOR)")
    source_node: str = Field(..., description="Source node type")
    target_node: str = Field(..., description="Target node type")
    description: str = Field(default="")


class GraphSchema(BaseModel):
    """Knowledge graph schema definition"""
    nodes: List[GraphSchemaNode] = Field(default_factory=list)
    relations: List[GraphSchemaRelation] = Field(default_factory=list)
    auto_extract: bool = Field(
        default=True,
        description="Let LLM automatically extract entities"
    )


class RetrievalConfig(BaseModel):
    """Step 4: Retrieval configuration"""
    method: RetrievalMethod
    vector: VectorSearchConfig = Field(default_factory=VectorSearchConfig)
    keyword: KeywordSearchConfig = Field(default_factory=KeywordSearchConfig)
    graph: GraphSearchConfig = Field(default_factory=GraphSearchConfig)
    graph_schema: Optional[GraphSchema] = None
    reranker_enabled: bool = False
    reranker_model: Optional[str] = None


# ==================== STEP 4 ADDON: CHUNKING ====================

class ChunkingConfig(BaseModel):
    """Chunking strategy configuration"""
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = Field(default=512, ge=100, le=4000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    separators: List[str] = Field(
        default=["\n\n", "\n", " ", ""]
    )


# ==================== STEP 5: AGENT ====================

class AgentConfig(BaseModel):
    """Step 5: Agent template configuration"""
    template: AgentTemplate
    max_iterations: int = Field(default=5, ge=1, le=20)
    enable_judge: bool = Field(
        default=False,
        description="Enable LLM-as-judge evaluation"
    )
    judge_llm: Optional[LLMConfig] = None


# ==================== STEP 6: PROMPTS ====================

class PromptConfig(BaseModel):
    """Step 6: Prompt configuration"""
    system_prompt: str = Field(
        ...,
        description="System prompt for the LLM"
    )
    rag_prompt_template: str = Field(
        ...,
        description="RAG prompt with {context} and {query} placeholders"
    )
    judge_prompts: Optional[Dict[str, str]] = Field(
        default=None,
        description="Prompts for evaluation (relevance, faithfulness, etc.)"
    )


# ==================== MAIN CONFIG ====================

class RAGPipelineConfig(BaseModel):
    """
    Complete RAG pipeline configuration.
    This is the main document stored in MongoDB.
    """
    # Metadata
    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    version: str = Field(default="1.0.0")
    created_by: str = Field(..., description="User ID of creator")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Status
    status: IngestionStatus = Field(default=IngestionStatus.PENDING)
    api_endpoint: Optional[str] = Field(
        default=None,
        description="Generated API endpoint path"
    )
    
    # Configuration Steps
    data_source: DataSourceConfig
    rbac: RBACConfig = Field(default_factory=RBACConfig)
    models: ModelConfig
    retrieval: RetrievalConfig
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    agent: AgentConfig
    prompts: PromptConfig
    
    # Ingestion Stats
    stats: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Ingestion statistics (document count, chunk count, etc.)"
    )

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### 5.2 API Endpoints

#### Config Service API

```yaml
# Config Service - /api/v1/

# Authentication
POST   /auth/register          # Register new user
POST   /auth/login             # Login, returns JWT
POST   /auth/refresh           # Refresh JWT token
POST   /auth/logout            # Invalidate token

# User Management
GET    /users/me               # Get current user
PUT    /users/me               # Update current user
DELETE /users/me               # Delete account

# Configuration CRUD
GET    /configs                # List user's configs
POST   /configs                # Create new config
GET    /configs/{id}           # Get config by ID
PUT    /configs/{id}           # Update config
DELETE /configs/{id}           # Delete config
POST   /configs/{id}/duplicate # Duplicate config

# Export/Import
GET    /configs/{id}/export    # Export as YAML
POST   /configs/import         # Import from YAML

# Folder Scanning
POST   /folders/scan           # Scan a path, return folder tree
```

#### Ingestion Service API

```yaml
# Ingestion Service - /api/v1/

# Ingestion Control
POST   /ingest/{config_id}/start    # Start ingestion job
GET    /ingest/{config_id}/status   # Get job status
POST   /ingest/{config_id}/cancel   # Cancel running job
POST   /ingest/{config_id}/retry    # Retry failed job

# Job Details
GET    /ingest/{config_id}/logs     # Get processing logs
GET    /ingest/{config_id}/stats    # Get ingestion statistics
```

#### RAG Service API

```yaml
# RAG Service - /api/v1/

# Query Endpoints (config_id derived from API key or path)
POST   /query                  # Single query, returns response
POST   /chat                   # Chat with history
GET    /stream                 # SSE streaming response

# Health
GET    /health                 # Service health check
```

### 5.3 Request/Response Schemas

```typescript
// shared/typescript/src/api.ts

// ========== Auth ==========

interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

interface LoginRequest {
  email: string;
  password: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

interface UserResponse {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

// ========== Config ==========

interface ConfigListResponse {
  items: ConfigSummary[];
  total: number;
  page: number;
  page_size: number;
}

interface ConfigSummary {
  id: string;
  name: string;
  description: string;
  status: IngestionStatus;
  created_at: string;
  updated_at: string;
}

interface ConfigCreateRequest {
  name: string;
  description?: string;
  data_source: DataSourceConfig;
  rbac?: RBACConfig;
  models: ModelConfig;
  retrieval: RetrievalConfig;
  chunking?: ChunkingConfig;
  agent: AgentConfig;
  prompts: PromptConfig;
}

// ========== Folder Scan ==========

interface FolderScanRequest {
  type: DataSourceType;
  base_path: string;
  credentials?: Record<string, string>;
}

interface FolderScanResponse {
  base_path: string;
  folders: FolderInfo[];
  has_multimodal: boolean;
}

interface FolderInfo {
  path: string;
  name: string;
  detected_types: DataType[];
  file_count: number;
  children: FolderInfo[];
}

// ========== Ingestion ==========

interface IngestionStatusResponse {
  config_id: string;
  status: IngestionStatus;
  progress: number;  // 0-100
  current_step: string;
  steps_completed: string[];
  error?: string;
  stats?: IngestionStats;
}

interface IngestionStats {
  total_files: number;
  processed_files: number;
  total_chunks: number;
  total_embeddings: number;
  graph_nodes?: number;
  graph_edges?: number;
  processing_time_seconds: number;
}

// ========== RAG Query ==========

interface QueryRequest {
  query: string;
  config_id?: string;  // Optional if using API key auth
  user_role?: string;  // For RBAC
  include_sources?: boolean;
  include_debug?: boolean;
}

interface QueryResponse {
  answer: string;
  sources?: Source[];
  debug?: DebugInfo;
  usage?: UsageInfo;
}

interface Source {
  content: string;
  metadata: Record<string, any>;
  score: number;
  source_type: "vector" | "keyword" | "graph";
}

interface DebugInfo {
  retrieval_time_ms: number;
  generation_time_ms: number;
  agent_steps?: AgentStep[];
  retrieved_chunks: number;
}

interface AgentStep {
  step: number;
  action: string;
  observation: string;
  thought?: string;
}

interface ChatRequest {
  message: string;
  conversation_id?: string;
  config_id?: string;
  user_role?: string;
}

interface ChatResponse {
  answer: string;
  conversation_id: string;
  sources?: Source[];
}

// ========== Standard Response Wrapper ==========

interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: APIError;
  meta?: ResponseMeta;
}

interface APIError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

interface ResponseMeta {
  request_id: string;
  timestamp: string;
  version: string;
}
```

---

## 6. Implementation Roadmap

### Phase 0: Project Setup (Week 1)

| Task ID | Task | Description | Depends On | Deliverable |
|---------|------|-------------|------------|-------------|
| P0-1 | Repository Setup | Initialize monorepo, add README, LICENSE, .gitignore | - | Git repository |
| P0-2 | Docker Compose | Create docker-compose.yml with MongoDB, Redis | P0-1 | Working local infrastructure |
| P0-3 | Shared Schemas | Create JSON schemas and Pydantic models | P0-1 | `shared/` package |
| P0-4 | Python Package | Set up shared Python package with models | P0-3 | Installable package |
| P0-5 | TypeScript Types | Generate TypeScript types from schemas | P0-3 | `shared/typescript/` |
| P0-6 | Makefile | Create common commands (dev, test, build) | P0-2 | Working `make dev` |

### Phase 1: Config Service (Weeks 2-3)

| Task ID | Task | Description | Depends On | Deliverable |
|---------|------|-------------|------------|-------------|
| P1-1 | FastAPI Scaffold | Create config-service structure | P0-4 | Running FastAPI app |
| P1-2 | MongoDB Connection | Implement MongoDB client with connection pooling | P1-1 | `db/mongodb.py` |
| P1-3 | User Repository | Implement user CRUD operations | P1-2 | `repositories/user_repo.py` |
| P1-4 | Auth Endpoints | Implement register, login, refresh, logout | P1-3 | `api/v1/auth.py` |
| P1-5 | JWT Middleware | Implement JWT validation middleware | P1-4 | `core/security.py` |
| P1-6 | Config Repository | Implement config CRUD operations | P1-2 | `repositories/config_repo.py` |
| P1-7 | Config Endpoints | Implement config CRUD API | P1-6, P1-5 | `api/v1/configs.py` |
| P1-8 | Folder Scanner | Implement local folder scanning | P1-1 | `services/folder_service.py` |
| P1-9 | Folder Endpoints | Implement folder scan API | P1-8, P1-5 | `api/v1/folders.py` |
| P1-10 | YAML Export | Implement config export/import | P1-7 | `services/export_service.py` |
| P1-11 | Config Service Tests | Unit and integration tests | P1-10 | `tests/` |

### Phase 2: Go Gateway (Week 4)

| Task ID | Task | Description | Depends On | Deliverable |
|---------|------|-------------|------------|-------------|
| P2-1 | Gateway Scaffold | Create Go project structure | P0-1 | Compiling Go app |
| P2-2 | Router Setup | Configure Gin router | P2-1 | `internal/router/router.go` |
| P2-3 | JWT Middleware | Implement JWT validation | P2-2 | `internal/middleware/auth.go` |
| P2-4 | Proxy Handler | Implement reverse proxy to Python services | P2-2 | `internal/proxy/proxy.go` |
| P2-5 | CORS Middleware | Implement CORS handling | P2-2 | `internal/middleware/cors.go` |
| P2-6 | Rate Limiter | Implement rate limiting | P2-2 | `internal/middleware/ratelimit.go` |
| P2-7 | Health Endpoint | Implement health check | P2-2 | `internal/handlers/health.go` |
| P2-8 | WebSocket Handler | Implement WebSocket proxy for streaming | P2-4 | `internal/handlers/websocket.go` |
| P2-9 | Gateway Tests | Integration tests | P2-8 | Gateway test suite |

### Phase 3: Ingestion Service (Weeks 5-6)

| Task ID | Task | Description | Depends On | Deliverable |
|---------|------|-------------|------------|-------------|
| P3-1 | Service Scaffold | Create ingestion-service structure | P0-4 | Running service |
| P3-2 | Celery Setup | Configure Celery with Redis | P3-1 | `core/celery_app.py` |
| P3-3 | Base Processor | Abstract processor interface | P3-1 | `processors/base.py` |
| P3-4 | Text Processor | Plain text file processor | P3-3 | `processors/text.py` |
| P3-5 | PDF Processor | PDF processor with Docling | P3-3 | `processors/pdf.py` |
| P3-6 | Image Processor | Image processor | P3-3 | `processors/image.py` |
| P3-7 | Processor Factory | Factory to select processor by file type | P3-4, P3-5, P3-6 | `processors/factory.py` |
| P3-8 | Base Chunker | Abstract chunker interface | P3-1 | `chunkers/base.py` |
| P3-9 | Recursive Chunker | Recursive text splitter | P3-8 | `chunkers/recursive.py` |
| P3-10 | Semantic Chunker | Semantic chunking | P3-8 | `chunkers/semantic.py` |
| P3-11 | Chunker Factory | Factory to select chunker | P3-9, P3-10 | `chunkers/factory.py` |
| P3-12 | Base Embedder | Abstract embedder interface | P3-1 | `embedders/base.py` |
| P3-13 | OpenAI Embedder | OpenAI embedding implementation | P3-12 | `embedders/openai.py` |
| P3-14 | Ollama Embedder | Ollama embedding implementation | P3-12 | `embedders/ollama.py` |
| P3-15 | Embedder Factory | Factory to select embedder | P3-13, P3-14 | `embedders/factory.py` |
| P3-16 | Vector Store | MongoDB vector operations | P3-1 | `storage/vector_store.py` |
| P3-17 | Graph Extractor | Entity/relation extraction | P3-1 | `graph/extractor.py` |
| P3-18 | Graph Builder | Knowledge graph construction | P3-17 | `graph/builder.py` |
| P3-19 | Graph Store | MongoDB graph operations | P3-18 | `storage/graph_store.py` |
| P3-20 | Ingest Task | Main orchestration Celery task | P3-7, P3-11, P3-15, P3-16, P3-19 | `tasks/ingest_task.py` |
| P3-21 | Ingest API | Trigger and status endpoints | P3-20 | `api/v1/ingest.py` |
| P3-22 | Ingestion Tests | Unit and integration tests | P3-21 | Test suite |

### Phase 4: RAG Service (Weeks 7-8)

| Task ID | Task | Description | Depends On | Deliverable |
|---------|------|-------------|------------|-------------|
| P4-1 | Service Scaffold | Create rag-service structure | P0-4 | Running service |
| P4-2 | Base Retriever | Abstract retriever interface | P4-1 | `retrieval/base.py` |
| P4-3 | Vector Retriever | MongoDB vector search | P4-2 | `retrieval/vector.py` |
| P4-4 | Keyword Retriever | Atlas Search | P4-2 | `retrieval/keyword.py` |
| P4-5 | Graph Retriever | Graph traversal retrieval | P4-2 | `retrieval/graph.py` |
| P4-6 | Hybrid Retriever | Combined retrieval | P4-3, P4-4, P4-5 | `retrieval/hybrid.py` |
| P4-7 | Retriever Factory | Factory to create retriever from config | P4-6 | `retrieval/factory.py` |
| P4-8 | Base LLM | Abstract LLM interface | P4-1 | `llm/base.py` |
| P4-9 | OpenAI LLM | OpenAI implementation | P4-8 | `llm/openai.py` |
| P4-10 | Ollama LLM | Ollama implementation | P4-8 | `llm/ollama.py` |
| P4-11 | LLM Factory | Factory to create LLM from config | P4-9, P4-10 | `llm/factory.py` |
| P4-12 | Prompt Manager | Load prompts from config | P4-1 | `prompts/manager.py` |
| P4-13 | Naive RAG Graph | LangGraph naive RAG flow | P4-7, P4-11, P4-12 | `agents/graphs/naive.py` |
| P4-14 | ReAct Graph | LangGraph ReAct flow | P4-13 | `agents/graphs/react.py` |
| P4-15 | CRAG Graph | LangGraph CRAG flow | P4-13 | `agents/graphs/crag.py` |
| P4-16 | Agent Factory | Factory to create agent from template | P4-13, P4-14, P4-15 | `agents/factory.py` |
| P4-17 | RBAC Enforcement | Filter retrieval by user role | P4-7 | `core/rbac.py` |
| P4-18 | Query Endpoint | Single query API | P4-16, P4-17 | `api/v1/query.py` |
| P4-19 | Chat Endpoint | Chat with history API | P4-18 | `api/v1/chat.py` |
| P4-20 | Stream Endpoint | SSE streaming | P4-18 | `api/v1/stream.py` |
| P4-21 | RAG Service Tests | Unit and integration tests | P4-20 | Test suite |

### Phase 5: Configurator UI (Weeks 9-11)

| Task ID | Task | Description | Depends On | Deliverable |
|---------|------|-------------|------------|-------------|
| P5-1 | Vue Project Setup | Create Vue 3 project with Vite | P0-5 | Running dev server |
| P5-2 | Naive UI Setup | Install and configure Naive UI | P5-1 | Theme configured |
| P5-3 | Pinia Stores | Set up auth, config, wizard stores | P5-1 | `stores/` |
| P5-4 | API Service | Create Axios client with interceptors | P5-3 | `services/api.ts` |
| P5-5 | Router Setup | Configure Vue Router with guards | P5-4 | `router/index.ts` |
| P5-6 | Login View | Login/register pages | P5-5 | `views/LoginView.vue` |
| P5-7 | Dashboard View | Config list page | P5-6 | `views/DashboardView.vue` |
| P5-8 | Wizard Container | Step wizard component | P5-7 | `components/wizard/` |
| P5-9 | Step 1: Data Source | Data source config step | P5-8 | `components/steps/Step1DataSource.vue` |
| P5-10 | Folder Tree Component | Visual folder tree | P5-9 | `components/visualizers/FolderTree.vue` |
| P5-11 | Step 2: RBAC | Role configuration step | P5-10 | `components/steps/Step2RBAC.vue` |
| P5-12 | Step 3: Models | Model selection step | P5-11 | `components/steps/Step3ModelSelection.vue` |
| P5-13 | Step 4: Retrieval | Retrieval config step | P5-12 | `components/steps/Step4Retrieval.vue` |
| P5-14 | Step 4b: Graph Schema | Graph schema editor | P5-13 | `components/steps/Step4bGraphSchema.vue` |
| P5-15 | Step 5: Agent | Agent template selection | P5-14 | `components/steps/Step5AgentTemplate.vue` |
| P5-16 | Step 6: Prompts | Prompt editor step | P5-15 | `components/steps/Step6Prompts.vue` |
| P5-17 | Step 7: Review | Review and deploy step | P5-16 | `components/steps/Step7Review.vue` |
| P5-18 | Pipeline Preview | Visual pipeline preview | P5-17 | `components/visualizers/PipelinePreview.vue` |
| P5-19 | Ingestion Progress | Progress tracking component | P5-17 | Ingestion status component |
| P5-20 | UI Tests | Component and E2E tests | P5-19 | Test suite |

### Phase 6: Sandbox UI (Week 12)

| Task ID | Task | Description | Depends On | Deliverable |
|---------|------|-------------|------------|-------------|
| P6-1 | Vue Project Setup | Create sandbox Vue project | P5-1 | Running dev server |
| P6-2 | Chat Store | Chat history state management | P6-1 | `stores/chat.ts` |
| P6-3 | Chat Container | Main chat component | P6-2 | `components/ChatContainer.vue` |
| P6-4 | Message Components | Message bubble and list | P6-3 | `components/MessageBubble.vue` |
| P6-5 | Sources Panel | Show retrieved sources | P6-4 | `components/SourcesPanel.vue` |
| P6-6 | Debug Panel | Show agent steps/debug info | P6-5 | `components/DebugPanel.vue` |
| P6-7 | Streaming Support | Handle SSE streaming | P6-4 | Streaming implementation |
| P6-8 | Config Selector | Select which config to test | P6-7 | `components/ConfigSelector.vue` |
| P6-9 | Sandbox Tests | Component tests | P6-8 | Test suite |

### Phase 7: Integration & Polish (Weeks 13-14)

| Task ID | Task | Description | Depends On | Deliverable |
|---------|------|-------------|------------|-------------|
| P7-1 | End-to-End Testing | Full pipeline tests | All phases | E2E test suite |
| P7-2 | Documentation | Complete all documentation | All phases | `docs/` complete |
| P7-3 | Docker Production | Production Docker configs | All phases | `docker-compose.prod.yml` |
| P7-4 | CI/CD Pipeline | GitHub Actions workflow | P7-3 | `.github/workflows/` |
| P7-5 | Performance Testing | Load testing | P7-1 | Performance report |
| P7-6 | Security Audit | Security review | P7-1 | Security report |
| P7-7 | Demo Data | Sample configs and data | P7-1 | Demo setup script |
| P7-8 | Release | Version 1.0.0 release | P7-7 | GitHub release |

---

## 7. Testing Requirements

### 7.1 Unit Tests

| Module | Test Coverage | Key Test Cases |
|--------|--------------|----------------|
| Config Service | 80%+ | User CRUD, Config CRUD, Validation, JWT |
| Ingestion Service | 80%+ | Each processor, chunker, embedder |
| RAG Service | 80%+ | Each retriever, agent graph |
| Gateway | 70%+ | Routing, Auth middleware |
| Configurator UI | 70%+ | Wizard flow, Form validation |

### 7.2 Integration Tests

| Test | Description |
|------|-------------|
| Auth Flow | Register → Login → Access protected endpoint |
| Config Flow | Create config → Update → Export YAML → Import |
| Ingestion Flow | Create config → Trigger ingestion → Verify vectors |
| Query Flow | Create config → Ingest → Query → Verify response |
| RBAC Flow | Create roles → Assign folders → Verify access control |

### 7.3 E2E Tests

| Test | Description |
|------|-------------|
| Full Wizard | Complete all wizard steps → Deploy → Test query |
| Multi-User | Two users with different roles → Verify isolation |
| Error Recovery | Simulate failures → Verify recovery |

---

## 8. Database Schemas

### 8.1 MongoDB Collections

```javascript
// Collection: users
{
  _id: ObjectId,
  email: String (unique, indexed),
  password_hash: String,
  name: String,
  created_at: ISODate,
  updated_at: ISODate,
  is_active: Boolean
}

// Collection: configs
{
  _id: ObjectId,
  name: String,
  description: String,
  version: String,
  created_by: ObjectId (ref: users),
  created_at: ISODate,
  updated_at: ISODate,
  status: String (enum: pending, processing, completed, failed),
  api_endpoint: String,
  
  // Step 1
  data_source: {
    type: String,
    base_path: String,
    credentials: Object (encrypted),
    folders: [{
      path: String,
      name: String,
      detected_types: [String],
      allowed_roles: [String],
      recursive: Boolean,
      file_patterns: [String],
      file_count: Number
    }],
    has_multimodal: Boolean
  },
  
  // Step 2
  rbac: {
    enabled: Boolean,
    roles: [{
      name: String,
      description: String,
      allowed_folders: [String],
      can_query: Boolean,
      can_view_sources: Boolean,
      rate_limit: Number
    }],
    default_role: String
  },
  
  // Step 3
  models: {
    llm: {
      provider: String,
      model_name: String,
      base_url: String,
      api_key: String (encrypted),
      temperature: Number,
      max_tokens: Number,
      is_multimodal: Boolean
    },
    embedding: {
      provider: String,
      model_name: String,
      base_url: String,
      api_key: String (encrypted),
      dimensions: Number
    },
    document_processing: {
      use_docling: Boolean,
      use_vision_llm: Boolean,
      vision_llm: Object,
      ocr_enabled: Boolean
    }
  },
  
  // Step 4
  retrieval: {
    method: String,
    vector: { enabled: Boolean, top_k: Number, score_threshold: Number },
    keyword: { enabled: Boolean, top_k: Number, use_fuzzy: Boolean, boost_factor: Number },
    graph: { enabled: Boolean, max_depth: Number, top_k: Number },
    graph_schema: {
      nodes: [{ name: String, description: String, properties: [String] }],
      relations: [{ name: String, source_node: String, target_node: String, description: String }],
      auto_extract: Boolean
    },
    reranker_enabled: Boolean,
    reranker_model: String
  },
  
  // Chunking
  chunking: {
    strategy: String,
    chunk_size: Number,
    chunk_overlap: Number,
    separators: [String]
  },
  
  // Step 5
  agent: {
    template: String,
    max_iterations: Number,
    enable_judge: Boolean,
    judge_llm: Object
  },
  
  // Step 6
  prompts: {
    system_prompt: String,
    rag_prompt_template: String,
    judge_prompts: Object
  },
  
  // Stats
  stats: {
    total_files: Number,
    total_chunks: Number,
    total_embeddings: Number,
    graph_nodes: Number,
    graph_edges: Number,
    processing_time_seconds: Number
  }
}

// Collection: documents (processed documents metadata)
{
  _id: ObjectId,
  config_id: ObjectId (indexed),
  file_path: String,
  file_name: String,
  file_type: String,
  folder_path: String,
  content_hash: String,
  processed_at: ISODate,
  chunk_count: Number,
  metadata: Object
}

// Collection: chunks (with vector embeddings)
{
  _id: ObjectId,
  config_id: ObjectId (indexed),
  document_id: ObjectId (indexed),
  content: String,
  embedding: [Number] (vector, indexed),
  metadata: {
    file_path: String,
    folder_path: String,
    chunk_index: Number,
    start_char: Number,
    end_char: Number
  },
  created_at: ISODate
}

// Collection: graph_nodes (for Graph RAG)
{
  _id: ObjectId,
  config_id: ObjectId (indexed),
  node_type: String (indexed),
  name: String,
  properties: Object,
  embedding: [Number] (vector),
  source_documents: [ObjectId],
  created_at: ISODate
}

// Collection: graph_edges
{
  _id: ObjectId,
  config_id: ObjectId (indexed),
  relation_type: String (indexed),
  source_node: ObjectId,
  target_node: ObjectId,
  properties: Object,
  source_documents: [ObjectId],
  created_at: ISODate
}

// Collection: conversations (chat history)
{
  _id: ObjectId,
  config_id: ObjectId (indexed),
  user_id: ObjectId,
  messages: [{
    role: String (user/assistant),
    content: String,
    timestamp: ISODate,
    sources: [Object],
    debug: Object
  }],
  created_at: ISODate,
  updated_at: ISODate
}

// Collection: ingestion_jobs
{
  _id: ObjectId,
  config_id: ObjectId (indexed),
  status: String,
  progress: Number,
  current_step: String,
  steps_completed: [String],
  error: String,
  started_at: ISODate,
  completed_at: ISODate,
  logs: [{ timestamp: ISODate, level: String, message: String }]
}
```

### 8.2 Indexes

```javascript
// users
db.users.createIndex({ email: 1 }, { unique: true });

// configs
db.configs.createIndex({ created_by: 1 });
db.configs.createIndex({ status: 1 });
db.configs.createIndex({ created_at: -1 });

// chunks - Vector Search Index (Atlas)
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "type": "knnVector",
        "dimensions": 1536,
        "similarity": "cosine"
      },
      "config_id": { "type": "objectId" },
      "metadata.folder_path": { "type": "string" }
    }
  }
}

// chunks - Atlas Search Index (for keyword search)
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "content": {
        "type": "string",
        "analyzer": "lucene.standard"
      },
      "config_id": { "type": "objectId" },
      "metadata.folder_path": { "type": "string" }
    }
  }
}

// graph_nodes
db.graph_nodes.createIndex({ config_id: 1, node_type: 1 });
db.graph_nodes.createIndex({ config_id: 1, name: 1 });

// graph_edges
db.graph_edges.createIndex({ config_id: 1, source_node: 1 });
db.graph_edges.createIndex({ config_id: 1, target_node: 1 });
db.graph_edges.createIndex({ config_id: 1, relation_type: 1 });

// conversations
db.conversations.createIndex({ config_id: 1, user_id: 1 });

// ingestion_jobs
db.ingestion_jobs.createIndex({ config_id: 1 });
```

---

## 9. Environment Variables

```bash
# .env.example

# ===== General =====
ENVIRONMENT=development  # development | staging | production
LOG_LEVEL=INFO

# ===== MongoDB =====
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=rag_configurator

# ===== Redis =====
REDIS_URL=redis://localhost:6379/0

# ===== JWT =====
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ===== Services =====
CONFIG_SERVICE_URL=http://localhost:8001
INGESTION_SERVICE_URL=http://localhost:8002
RAG_SERVICE_URL=http://localhost:8003

# ===== Gateway =====
GATEWAY_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# ===== External APIs (optional) =====
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...

# ===== MLflow =====
MLFLOW_TRACKING_URI=http://localhost:5000
```

---

## 10. Summary

This document serves as the complete blueprint for the RAG Configurator project. Key principles:

1. **Strict Modularity**: Each service is independent and communicates via well-defined APIs
2. **Sequential Configuration**: The wizard flow prevents circular dependencies
3. **Factory Pattern**: All major components (processors, chunkers, embedders, retrievers, agents) use factories for config-driven instantiation
4. **Single Source of Truth**: Shared schemas ensure consistency across all services
5. **Open Source Ready**: MIT/Apache 2.0 license, no proprietary dependencies

The implementation roadmap spans 14 weeks with clear dependencies. Each task is atomic and can be assigned to an individual developer or AI coding agent without requiring full system context.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Obsidian Vault — Second Brain Integration

## Vault Discovery (MANDATORY — run at session start)

Before any work, locate the Obsidian vault. Run this detection in order and use the first match:

```bash
# Try common locations
for candidate in \
  "G:/My Drive/MyNotes" \
  "$HOME/Google Drive/MyNotes" \
  "$HOME/google-drive/MyNotes" \
  "$HOME/My Drive/MyNotes" \
  "/mnt/google-drive/MyNotes" \
  "$HOME/MyNotes"; do
  if [ -d "$candidate/projects" ] && [ -d "$candidate/claude-code-files" ]; then
    echo "VAULT_FOUND: $candidate"
    break
  fi
done
```

If **no vault is found**, immediately warn the user:
> "I cannot find your Obsidian vault (MyNotes). Please connect your Google Drive or tell me the vault path. Without it, I cannot access your Second Brain, project knowledge, or documentation system."

Do NOT proceed with project onboarding, graphify operations, or vault writes until the vault is accessible.

Store the discovered path as `VAULT_ROOT` for the rest of the session.

## Vault Structure (PARA)

```
[VAULT_ROOT]/
├── inbox/              Quick captures
├── journal/            Monthly journals
├── projects/
│   ├── active/         Current work — graphify output + Index.md
│   ├── ideas/          Not yet started
│   ├── on-hold/        Paused
│   └── completed/      Shipped
├── areas/              Ongoing responsibilities (career, research, website)
├── resources/          Reference material
├── archive/            Cold storage
├── assets/             Images, attachments
├── templates/          Obsidian templates
├── claude-code-files/  Claude Code skills and system docs
│   ├── skills/         Reusable skills
│   ├── SECOND_BRAIN.md Full system documentation
│   └── BASE_CLAUDE.md  This template
└── rookie/             Agent config — DO NOT modify
```

## Project Knowledge Base

Every active project has a folder at `[VAULT_ROOT]/projects/active/[project-name]/` containing:
- **Index.md** — Project summary, god nodes, architecture, quick links
- **GRAPH_REPORT.md** — Graphify structural analysis (god nodes, communities, surprising connections)
- **wiki/** — Auto-generated community articles

Before answering architecture or structural questions about this project, check if `[VAULT_ROOT]/projects/active/[this-project]/GRAPH_REPORT.md` exists and read it for context.

## Project Onboarding

When starting a new project that has no vault folder yet:
1. Run `graphify claude install` in the project root
2. Build graph: `PYTHONUTF8=1 python -X utf8 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"`
3. Generate wiki from graph
4. Create `[VAULT_ROOT]/projects/active/[project-name]/`
5. Copy `GRAPH_REPORT.md` + `wiki/` to vault
6. Create `Index.md` with project summary

Full procedure: read `[VAULT_ROOT]/claude-code-files/skills/graphify-onboard/SKILL.md`

## Documentation Rules

- The vault is the single source of truth for project knowledge and decisions
- Repos hold code-specific CLAUDE.md (build, test, lint, patterns); the vault holds the why and the architecture
- Always use `[[wikilinks]]` in vault markdown files for Obsidian compatibility
- When creating vault files, add YAML frontmatter with at minimum: title, date, tags

---

# Workflow Orchestration

## 1. Plan Mode Default

- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately — don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

## 2. Subagent Strategy

- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

## 3. Self-Improvement Loop

- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

## 4. Verification Before Done

- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

## 5. Demand Elegance (Balanced)

- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

## 6. Autonomous Bug Fixing

- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

---

# Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

---

# Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

---

# Project: RAG Configurator

Low-code platform for building and deploying custom RAG pipelines. Four microservices behind a Go reverse proxy gateway, two Vue 3 frontends, MongoDB + Redis infrastructure.

## Build & Run

```bash
# Full stack (11 containers)
docker compose up -d

# With observability (adds Langfuse + PostgreSQL)
docker compose --profile observability up -d

# Infrastructure only (for local service dev)
docker compose up -d mongodb redis

# Install ALL dependencies at once
make install

# Or manually — install shared Python package first (required before any Python service)
pip install -e shared/python

# Individual Python services (run from their directory)
cd services/config-service && uvicorn app.main:app --port 8001 --reload
cd services/ingestion-service && uvicorn app.main:app --port 8002 --reload
cd services/rag-service && uvicorn app.main:app --port 8003 --reload

# Celery worker (from ingestion-service directory)
celery -A app.core.celery_app worker --loglevel=info --concurrency=2

# Go gateway
cd gateway && go run ./cmd/server/main.go

# Frontend apps
cd apps/configurator-ui && npm run dev    # port 5173
cd apps/sandbox-ui && npm run dev         # port 3001

# Shared TypeScript package (rebuild after model changes)
cd shared/typescript && npm run build
```

## Testing

```bash
# All tests
make test

# Per-service
cd services/config-service && python -m pytest tests/ -v
cd services/ingestion-service && python -m pytest tests/ -v
cd services/rag-service && python -m pytest tests/ -v
cd gateway && go test ./... -v

# Single test file / function
cd services/config-service && python -m pytest tests/test_auth.py -v
cd services/config-service && python -m pytest tests/test_auth.py::test_register -v

# E2E tests (requires full stack running on localhost:8000)
python -m pytest tests/e2e/ -v

# Load tests
cd tests/performance && locust -f locustfile.py
```

Python services use `asyncio_mode = "auto"` (in root `pyproject.toml`) — no `@pytest.mark.asyncio` needed.

## Linting

```bash
# All at once
make lint

# Python
cd services/{service-name} && ruff check . && black --check .

# Go
cd gateway && golangci-lint run

# Frontend
cd apps/{app-name} && npm run lint
```

## Architecture

```
Client → Gateway (Go/Gin :8000) → Config Service (FastAPI :8001)
                                 → Ingestion Service (FastAPI+Celery :8002)
                                 → RAG Service (FastAPI+LangGraph :8003)

Data: MongoDB :27017 (configs, users, chunks, vectors, graphs, evaluations)
      Redis :6379 (Celery broker, embedding cache, query cache)
```

- **Gateway** — JWT validation, CORS, rate limiting, HMAC inter-service signing, reverse proxy, SSE passthrough. Auth endpoints (`/api/v1/auth/*`) skip JWT check; all others require it. Sets `X-User-ID` header from JWT before proxying. Health check at `/health`.
- **Config Service** — User auth (register/login/refresh/logout with token blacklist), config CRUD, folder browsing/scanning, YAML/JSON export/import, pipeline templates.
- **Ingestion Service** — Document processing pipeline: processors → chunkers → embedders → storage. Celery workers run async. Graph extraction for GraphRAG. Supports PDF (Docling), DOCX, TXT, MD, HTML, images (OCR).
- **RAG Service** — 7 LangGraph agent types (Naive, ReAct, CRAG, Self-RAG, Multi-Query, Plan-Solve, GraphRAG), 5 retrieval strategies (vector, keyword, graph, hybrid, hybrid_graph), 4 LLM providers (OpenAI, Anthropic, Ollama, vLLM). RAGAS evaluation, guardrails, query caching, SSE streaming via sse-starlette.

Frontend apps live in `apps/` (NOT `ui/` — that's a legacy placeholder):
- `apps/configurator-ui` — Vue 3 + Tailwind + Headless UI, 9-step wizard for pipeline configuration
- `apps/sandbox-ui` — Vue 3 + Tailwind + Naive UI, chat interface with SSE streaming and retrieval debugger

## Shared Packages

### `rag_config_common` (Python — `shared/python/`)
All services depend on this. Must be installed first (`pip install -e shared/python`).
- **Models:** Pydantic models for `RAGPipelineConfig` and sub-configs, `User`, all enums (`LLMProvider`, `AgentTemplate`, `ChunkingStrategy`, `RetrievalMethod`, etc.)
- **Auth:** HMAC signing/verification, JWT utilities, `TokenBlacklist`, `ServiceAuthMiddleware`
- **Observability:** OpenTelemetry tracing setup, Langfuse integration, custom metrics
- **Cache:** `embedding_cache` and `query_cache` wrappers

### `shared/typescript/`
TypeScript interfaces mirroring the Python Pydantic models. Used by both frontend apps for type safety. Rebuild with `npm run build` after changing shared models.

## Key Patterns

- **Shared models**: Import from `rag_config_common` — never redefine config/user models or enums in individual services.
- **Factory pattern**: Processors, chunkers, embedders, retrievers, LLM clients, and agents all use factory classes. Register new implementations in the corresponding `factory.py`.
- **Repository pattern**: MongoDB access goes through `app/db/repositories/`. Services never touch collections directly.
- **JWT flow**: Config service creates tokens → gateway validates with same `JWT_SECRET_KEY`/`JWT_ALGORITHM` (HS256). Gateway sets `X-User-ID` header before proxying. Token payload: `{"sub": "user_id", "type": "access", "exp": ..., "iat": ...}`.
- **HMAC inter-service auth**: Gateway signs proxied requests with `INTER_SERVICE_SECRET`. Backend services verify via `ServiceAuthMiddleware` from `rag_config_common`.
- **API response envelope**: All endpoints return `{"success": bool, "data": ..., "error": ..., "meta": ...}`.
- **SSE streaming**: Gateway has special trailing-slash handling for `/api/v1/stream` to avoid 307 redirects with FastAPI. SSE uses `sse-starlette` on the RAG service side.
- **Caching**: Redis-backed embedding cache (`emb_cache:{sha256}`) avoids re-embedding duplicate content. Query cache (`query_cache:{config_id}:{sha256}`) caches full RAG responses. Both degrade gracefully on Redis failure.

## Service Ports

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
| Mongo Express (dev) | 8081 |
| Redis Commander (dev) | 8082 |
| Langfuse (observability profile) | 3003 |

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `PYTHONUTF8=1 python -X utf8 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current

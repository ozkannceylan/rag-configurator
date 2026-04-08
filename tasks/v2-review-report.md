# RAG Configurator v2 Review Report

**Date:** 2026-04-08
**Scope:** Full project audit against PLAN.md, code quality review, latest RAG research
**Purpose:** Base document for v2 release planning

---

## Table of Contents

1. [PLAN.md Compliance Audit](#1-planmd-compliance-audit)
2. [Security & Code Quality Issues](#2-security--code-quality-issues)
3. [Latest RAG Techniques for v2](#3-latest-rag-techniques-for-v2)
4. [New Chunking & Embedding Methods](#4-new-chunking--embedding-methods)
5. [Agent Framework Evolution](#5-agent-framework-evolution)
6. [Evaluation & Observability](#6-evaluation--observability)
7. [Multi-Modal RAG](#7-multi-modal-rag)
8. [Performance & Scalability](#8-performance--scalability)
9. [Security & Governance Features](#9-security--governance-features)
10. [Developer Experience & Platform](#10-developer-experience--platform)
11. [Prioritized v2 Roadmap](#11-prioritized-v2-roadmap)
12. [New Dependencies & Config Models](#12-new-dependencies--config-models)

---

## 1. PLAN.md Compliance Audit

### Overall Score: 98/100

Almost every task from the 8-phase plan is fully implemented. The project is production-shape.

### Phase-by-Phase Status

| Phase | Tasks | Done | Partial | Missing | Score |
|-------|-------|------|---------|---------|-------|
| P0: Project Setup | 6 | 6 | 0 | 0 | 100% |
| P1: Config Service | 11 | 11 | 0 | 0 | 100% |
| P2: Go Gateway | 9 | 9 | 0 | 0 | 100% |
| P3: Ingestion Service | 9 | 9 | 0 | 0 | 100% |
| P4: RAG Service | 16 | 16 | 0 | 0 | 100% |
| P5: Configurator UI | 18 | 17 | 1 | 0 | 97% |
| P6: Sandbox UI | 8 | 7 | 1 | 0 | 94% |
| P7: Integration & Polish | 8 | 8 | 0 | 0 | 100% |
| **TOTAL** | **85** | **83** | **2** | **0** | **98%** |

### Partial Items

| Task | Status | Detail |
|------|--------|--------|
| P5-18: Component & E2E Tests (Configurator UI) | ⚠️ PARTIAL | Test infrastructure exists but component-level tests are minimal. E2E tests are solid. |
| P6-8: Tests (Sandbox UI) | ⚠️ PARTIAL | Test setup exists but limited coverage. |

### Deviations from Plan

| Area | Planned | Actual | Impact |
|------|---------|--------|--------|
| UI directory | `ui/configurator`, `ui/sandbox` | `apps/configurator-ui`, `apps/sandbox-ui` | Positive — better naming |
| Test emphasis | Component + E2E tests | Heavy E2E, light component | Acceptable trade-off |
| Celery deployment | In-service workers | Separate `celery-worker` container | Positive — better scaling |

### Data Models: 100% Complete

All models from PLAN.md are implemented with all required fields:
- User, RAGConfig, DataSourceConfig, RBACConfig, ModelsConfig, RetrievalConfig, ChunkingConfig, AgentConfig, PromptConfig
- Document, Chunk, GraphNode, GraphEdge, IngestionJob, IngestionStats

### API Endpoints: 100% Complete

All 30+ endpoints from the API reference are implemented:
- Auth (4), Users (3), Configs (8), Folders (2), Ingestion (6), RAG (3), Health (2)

---

## 2. Security & Code Quality Issues

### Summary: 33 Issues Found

| Severity | Count | Must Fix Before |
|----------|-------|-----------------|
| CRITICAL | 5 | Production |
| HIGH | 12 | Beta |
| MEDIUM | 10 | v2 Release |
| LOW | 6 | Nice to have |

### CRITICAL Issues (Fix Immediately)

#### C1. Exposed `.env` File in Git
- **Location:** `.env` (tracked in repo)
- **Risk:** Demo credentials, JWT secret, DB credentials visible in git history
- **Fix:** `git rm --cached .env`, filter-branch to purge history, rotate all credentials
- **Add:** Pre-commit hook to prevent `.env` commits

#### C2. Missing Authentication on RAG Service Endpoints
- **Location:** `services/rag-service/app/api/v1/query.py` (lines 65-178)
- **Risk:** Any user can query ANY config by providing a `config_id` — no auth check, no ownership validation
- **Fix:** Add `current_user` dependency, verify `config.created_by == current_user.id`
- **Same issue on:** `/stream` endpoint

#### C3. Missing Authentication on Ingestion Service Endpoints
- **Location:** `services/ingestion-service/app/api/v1/ingest.py` (lines 202-250)
- **Risk:** Any user can start/cancel/check ingestion for ANY config
- **Fix:** Add auth dependency, verify ownership before all operations

#### C4. JWT Secret Synchronization Fragility
- **Location:** Gateway `pkg/jwt/jwt.go` vs Config Service `app/core/security.py`
- **Risk:** Two separate `JWT_SECRET_KEY` env vars — if they mismatch, auth breaks silently
- **Fix:** Centralize JWT config, add integration tests verifying cross-service JWT compatibility, add health check

#### C5. No Token Revocation / Blacklist
- **Location:** `services/config-service/app/services/auth_service.py` (lines 60-91)
- **Risk:** Logout doesn't invalidate tokens. Old refresh tokens remain valid forever. Token replay attacks possible.
- **Fix:** Implement Redis-based token blacklist with JTI claim tracking. Check blacklist on every validation.

### HIGH Issues (Fix Before Beta)

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| H1 | Weak default JWT secret | `config-service/app/core/settings.py:28` | Require explicit secret in production, validate on startup |
| H2 | Unsafe ObjectId parsing | `rag-service/app/api/v1/query.py:81-91` | Return 400 on InvalidId instead of silent fallback |
| H3 | CORS allows all methods/headers | `config-service/app/main.py:32-38` | Restrict to GET/POST/PUT/DELETE/OPTIONS and specific headers |
| H4 | Rate limiter unbounded memory | `gateway/internal/middleware/ratelimit.go:13-86` | Add cleanup goroutine with TTL to evict stale IP entries |
| H5 | WebSocket origin always accepted | `gateway/internal/handlers/websocket.go:18-26` | Validate against allowed CORS origins |
| H6 | No config ownership check in ingestion | `ingestion-service/app/api/v1/ingest.py:211-228` | Verify `config.created_by == current_user.id` |
| H7 | No error handling for LLM provider failures | `rag-service/app/api/v1/query.py:103-120` | Wrap in try/except, return 503 for unavailable providers |
| H8 | Incomplete health checks | `rag-service/app/main.py:99-133` | Add Redis, Celery, LLM provider checks with timeouts |
| H9 | No input validation on query length | `rag-service/app/api/v1/query.py:28` | Add `max_length=5000` to query field |
| H10 | Celery retry without exponential backoff | `ingestion-service/app/core/celery_app.py:36-40` | Enable `retry_backoff=True, retry_jitter=True` |
| H11 | Frontend token refresh race condition | `apps/configurator-ui/src/api/client.ts:22-57` | Deduplicate concurrent refresh calls with shared promise |
| H12 | SSE streaming no timeout | `rag-service/app/api/v1/stream.py:88-135` | Add `asyncio.timeout(300)` wrapper |

### MEDIUM Issues

| # | Issue | Fix |
|---|-------|-----|
| M1 | No refresh token rotation logging | Log auth failures for brute-force detection |
| M2 | MongoDB indexes not unique where needed | Add unique constraint on `(config_id, file_path)` |
| M3 | No pagination cap on chunk retrieval | Hard cap `top_k` at 100 |
| M4 | Missing string length validation on config creation | Add `min_length`/`max_length` to Pydantic fields |
| M5 | Docker dev images run as root | Add `USER appuser` to development stage |
| M6 | No content-type validation on file uploads | Validate MIME types before processing |
| M7 | No inter-service request signing | Add HMAC signing or mTLS |
| M8 | Error messages leak implementation details | Mask stack traces in production |
| M9 | No distributed tracing | Implement OpenTelemetry |
| M10 | Rate limiting per-IP only (useless behind proxy) | Add per-user rate limiting from JWT |

### Architecture Issues

| Issue | Recommendation |
|-------|---------------|
| No shared auth library | Create `shared/auth/` with unified JWT validation |
| No API versioning strategy | Plan header-based or route-based versioning for v2 |
| Celery tasks lack idempotency | Add idempotency keys to prevent duplicate processing |
| No circuit breaker pattern | Add `pybreaker` for LLM provider failures |
| Inconsistent error response formats | Standardize error envelope across all services |

---

## 3. Latest RAG Techniques for v2

### Contextual Retrieval (Anthropic, 2024)
- **What:** Prepend an LLM-generated contextual preamble to each chunk before embedding, so isolated chunks carry document-level context
- **Impact:** 49% reduction in retrieval failures (when combined with hybrid search)
- **Implementation:** Add pre-embedding step in ingestion that calls LLM for 1-2 sentence context prefix per chunk. Store as `contextual_prefix` field.
- **Complexity:** Medium | **Impact:** HIGH

### RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)
- **What:** Cluster chunks recursively, summarize each cluster, build a tree of summaries. Search across all tree levels at query time.
- **Implementation:** Post-chunking step: embed → cluster (k-means/HDBSCAN) → summarize → recurse. Store tree nodes with `tree_level` field.
- **Complexity:** Hard | **Impact:** HIGH (especially for long documents, multi-hop questions)

### Adaptive RAG (Query Router)
- **What:** Classifier or LLM routes queries to the best agent/retrieval strategy dynamically instead of manual selection
- **Implementation:** New `ADAPTIVE` agent template using lightweight classifier to route between existing 6 agents
- **Complexity:** Medium | **Impact:** HIGH (turns 6 agents into a smart ensemble)

### Speculative RAG
- **What:** Smaller "drafter" model generates multiple drafts from different chunk subsets, larger "verifier" selects best one
- **Implementation:** New `SPECULATIVE` agent template with drafter/verifier LLM config
- **Complexity:** Medium | **Impact:** Medium

### Microsoft GraphRAG
- **What:** Builds community-level summaries from knowledge graphs via Leiden algorithm, enabling global corpus queries
- **Current gap:** Your graph support extracts entities/relations but lacks community detection and global summarization
- **Implementation:** Integrate community detection, store community summaries, add `GLOBAL_SEARCH` retrieval method
- **Library:** `graphrag` (pip install graphrag)
- **Complexity:** Hard | **Impact:** HIGH

### New Agent Templates for v2
```python
class AgentTemplate(str, Enum):
    # Existing
    NAIVE_RAG = "naive_rag"
    REACT = "react"
    CRAG = "crag"
    SELF_RAG = "self_rag"
    MULTI_QUERY = "multi_query"
    PLAN_SOLVE = "plan_solve"
    # v2
    ADAPTIVE = "adaptive"          # Routes to best agent dynamically
    SPECULATIVE = "speculative"    # Draft + verify pattern
    GRAPH_RAG = "graph_rag"        # Microsoft GraphRAG global search
    AGENTIC_RAG = "agentic_rag"    # Tool-using agent with RAG as tool
```

---

## 4. New Chunking & Embedding Methods

### Late Chunking (Jina AI, 2024)
- **What:** Embed the entire document through a long-context model first, then split while preserving full-document attention context
- **Current gap:** You chunk first, then embed independently
- **Library:** `jina-embeddings-v3` supports natively
- **Complexity:** Medium | **Impact:** HIGH

### ColBERT / Late Interaction Models
- **What:** Per-token embeddings with MaxSim scoring at query time — much better precision than single-vector
- **Pragmatic approach:** Use ColBERT as a **reranker only** via RAGatouille library, keeping single-vector first-stage retrieval
- **Library:** `ragatouille>=0.0.8`
- **Full ColBERT complexity:** Hard | **As reranker:** Easy | **Impact:** HIGH

### New Embedding Providers to Add
| Provider | Key Feature | Complexity |
|----------|-------------|------------|
| Cohere embed-v3 | Multilingual, search_document/search_query types | Easy |
| Voyage AI | Purpose-built for RAG, high quality | Easy |
| Jina v3 | 8192 context, late chunking support | Easy |
| BGE-M3 (BAAI) | Dense + sparse + ColBERT simultaneously | Medium |

### Matryoshka Embeddings
- Already supported by OpenAI `text-embedding-3-*` and `nomic-embed-text`
- Add `truncate_dimensions` option to `EmbeddingConfig` — faster search, lower storage with minimal quality loss
- **Complexity:** Easy | **Impact:** Medium

### New Chunking Strategies
```python
class ChunkingStrategy(str, Enum):
    # Existing
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    DOCUMENT = "document"
    # v2
    LATE_CHUNKING = "late_chunking"      # Jina-style embed-then-split
    CONTEXTUAL = "contextual"            # Anthropic-style context injection
    HIERARCHICAL = "hierarchical"        # RAPTOR tree
    AGENTIC = "agentic"                  # LLM-guided chunk boundaries
```

---

## 5. Agent Framework Evolution

### LangGraph Upgrade (0.2.x → 0.3.x+)
Key new features since your current `langgraph==0.2.0`:
- **Subgraphs:** Compose agent graphs as subgraphs of larger graphs
- **Checkpointing/Memory:** Built-in persistence with MemorySaver, SqliteSaver, PostgresSaver — enables conversation memory
- **Human-in-the-loop:** Built-in interrupts for human approval
- **Token-level streaming:** Stream from within graph nodes

**Current gap:** Your agents don't use checkpointing. Conversation history is passed in state but not persisted.

**Fix:** Upgrade to `langgraph>=0.3.x`, add MongoDB-backed checkpointer for conversation persistence, use subgraphs for Adaptive RAG router.

### New Agent Patterns

| Pattern | Description | Complexity | Impact |
|---------|-------------|------------|--------|
| **Agentic RAG** | LLM decides when/how to call retrieval as a tool (can call multiple times, skip, etc.) | Medium | HIGH |
| **Reflection** | Agent critiques its own final answer and optionally re-generates | Easy | Medium |
| **Multi-Agent RAG** | Specialized agents collaborate (researcher → analyst → critic) | Hard | Medium |

### Framework Recommendation
Stay with LangGraph — strongest ecosystem for custom RAG. Don't switch to CrewAI/AutoGen.

---

## 6. Evaluation & Observability

### RAG Evaluation: RAGAS
- **Library:** `ragas>=0.1.10` — leading open-source RAG evaluation
- **Key metrics:**
  - Faithfulness (is answer grounded in context?)
  - Answer Relevancy (does answer address question?)
  - Context Precision (are retrieved docs relevant?)
  - Context Recall (are all needed docs retrieved?)
  - Answer Correctness (vs ground truth)
- **Implementation:** New `/api/v1/evaluate` endpoint, store results in MongoDB
- **Complexity:** Medium | **Impact:** HIGH

### Alternative: DeepEval
- `deepeval>=0.21.0` — more metrics, LLM-as-judge, hallucination detection, toxicity
- **Complexity:** Easy | **Impact:** Medium

### Observability: Langfuse (Recommended)
- Open-source, self-hostable LLM observability platform
- Traces LLM calls, evaluations, cost tracking
- Drop-in decorator/callback for LangChain/LangGraph
- **Library:** `langfuse>=2.0.0`
- **Complexity:** Medium | **Impact:** HIGH

### Other Options
| Tool | Type | Notes |
|------|------|-------|
| LangSmith | Commercial | By LangChain, great integration but paid |
| Phoenix (Arize) | Open-source | Traces, evals, embedding visualization |
| OpenLLMetry (Traceloop) | Open-source | OpenTelemetry for LLMs |

### Recommendation
Integrate **Langfuse** as primary observability + **RAGAS** for structured evaluation. These two together give you full pipeline visibility and quality measurement.

---

## 7. Multi-Modal RAG

### Activate Docling (IBM)
- Already in your requirements.txt (commented out)
- Handles: PDF layout analysis, table extraction, figure extraction, hierarchical structure
- **Complexity:** Easy | **Impact:** HIGH

### ColPali / ColQwen — Vision Retrieval
- Process document page images directly (no OCR needed) with vision-language models
- Produces multi-vector representations for document retrieval
- **Library:** `colpali-engine>=0.2.0`
- **Paradigm shift:** Embed page images directly instead of extract-text-then-embed
- **Complexity:** Hard | **Impact:** Medium-High

### Multi-Modal Embedding
- CLIP/SigLIP for embedding images + text into same vector space
- Nomic Embed Vision for image embedding
- **Complexity:** Medium | **Impact:** Medium

### Table-Aware Chunking
- When Docling detects tables, serialize as Markdown tables in chunks instead of losing structure
- **Complexity:** Easy | **Impact:** Medium

---

## 8. Performance & Scalability

### Embedding Caching (Redis)
- Hash query text, check Redis before calling embedding API
- You already have Redis in stack
- **Complexity:** Easy | **Impact:** Medium (reduces latency + API costs)

### Semantic Caching
- Cache full RAG responses for semantically similar queries
- Use vector similarity to match new queries against cached embeddings
- **Library:** `gptcache` or roll your own with Redis
- **Complexity:** Medium | **Impact:** HIGH (dramatic latency reduction for common queries)

### True Streaming
- **Current gap:** Some agents simulate streaming (run full pipeline, yield words)
- **Fix:** Stream LLM tokens directly via SSE as they arrive, send retrieval metadata first
- **Complexity:** Medium | **Impact:** Medium

### Batch Embedding Optimization
- Use OpenAI batch API for non-time-sensitive bulk embedding (50% cost reduction)
- **Complexity:** Easy | **Impact:** Medium

### Quantized Vector Search
- MongoDB scalar/binary quantization for vector indexes
- 4-32x memory reduction with minimal recall loss
- **Complexity:** Easy | **Impact:** Medium (for large collections)

---

## 9. Security & Governance Features

### Guardrails (New for v2)

| Library | Features | Recommendation |
|---------|----------|----------------|
| **LLM Guard** (Protect AI) | Prompt injection, PII, toxicity, ban topics, code detection | Primary choice |
| **NeMo Guardrails** (NVIDIA) | Declarative conversational rails, jailbreak prevention | Alternative |
| **Guardrails AI** | Schema validation, PII, hallucination | Alternative |

### New Config Model: GuardrailsConfig
```python
class GuardrailsConfig(BaseModel):
    enabled: bool = False
    detect_pii: bool = True
    detect_prompt_injection: bool = True
    detect_toxicity: bool = False
    blocked_topics: List[str] = []
    max_output_tokens: int = 4096
    require_grounding: bool = False  # Require citations
```

### Audit Logging
- Log all queries, responses, and retrieved sources for compliance
- Separate MongoDB collection
- **Complexity:** Easy | **Impact:** Medium

### Data Lineage
- Track which source documents contributed to each answer
- Extend existing `sources` in `AgentResponse` to full queryable lineage
- **Complexity:** Easy | **Impact:** Medium

---

## 10. Developer Experience & Platform

### Competing Platforms to Study
- **LangFlow / Flowise:** Visual drag-and-drop pipeline builders
- **Dify:** Open-source LLMOps with RAG, prompt engineering, agent builder
- **Haystack (deepset):** Open-source pipeline builder framework
- **Vectara:** Commercial RAG-as-a-service with built-in evaluation

### Key Features to Add

| Feature | Description | Complexity | Impact |
|---------|-------------|------------|--------|
| **Side-by-side comparison** | Run same query against two configs in sandbox | Medium | HIGH |
| **Retrieval debugger** | Show retrieved chunks, scores, and reasoning in sandbox | Medium | HIGH |
| **Step-by-step trace viewer** | Visualize agent decision path (data exists in `AgentResponse.steps`) | Medium | HIGH |
| **Config templates/marketplace** | Pre-built configs for legal, technical, support use cases | Easy | Medium |
| **One-click evaluation** | Upload test dataset, run automated RAGAS evaluation, dashboard | Medium | HIGH |
| **Cost estimation** | Estimate API costs before ingestion, track per-query costs | Easy | Medium |
| **Config version history** | Version history with diff viewing (field exists, history doesn't) | Medium | Medium |
| **Visual pipeline builder** | Drag-and-drop pipeline composition | Hard | HIGH |

---

## 11. Prioritized v2 Roadmap

### Tier 0: Security Fixes (BEFORE anything else)

| Item | Effort | Priority |
|------|--------|----------|
| Remove `.env` from git, rotate credentials | 1 hour | CRITICAL |
| Add auth to RAG service endpoints | 2 hours | CRITICAL |
| Add auth to Ingestion service endpoints | 2 hours | CRITICAL |
| Implement Redis token blacklist | 4 hours | CRITICAL |
| Fix rate limiter memory leak | 2 hours | HIGH |
| Add input validation (query length, ObjectId, config fields) | 4 hours | HIGH |
| Fix CORS to restrict methods/headers | 1 hour | HIGH |
| Fix WebSocket origin validation | 1 hour | HIGH |
| Add config ownership checks everywhere | 3 hours | HIGH |
| Frontend token refresh deduplication | 2 hours | HIGH |

### Tier 1: High Impact, Reasonable Effort

| Feature | Complexity | Impact | Touches |
|---------|------------|--------|---------|
| Contextual Retrieval (chunk context injection) | Medium | HIGH | Ingestion pipeline, ChunkingConfig |
| Adaptive RAG (query router agent) | Medium | HIGH | New agent, AgentTemplate enum |
| RAGAS evaluation integration | Medium | HIGH | New /evaluate endpoint |
| Langfuse observability | Medium | HIGH | Callbacks in LLM/retrieval |
| Guardrails (PII, prompt injection) | Easy | HIGH | New middleware, GuardrailsConfig |
| Embedding caching (Redis) | Easy | Medium | Retrieval path |
| Activate Docling for PDF parsing | Easy | HIGH | Uncomment dep, wire processor |
| Structured output for eval parsing | Easy | Medium | CRAG, Self-RAG refactors |
| ColBERT as reranker (RAGatouille) | Easy | HIGH | Retrieval pipeline |
| Sandbox side-by-side comparison | Medium | HIGH | Sandbox UI |
| Retrieval debugger in sandbox | Medium | HIGH | Sandbox UI |

### Tier 2: High Impact, Higher Effort

| Feature | Complexity | Impact |
|---------|------------|--------|
| Late Chunking support | Medium | HIGH |
| RAPTOR hierarchical indexing | Hard | HIGH |
| Microsoft GraphRAG communities | Hard | HIGH |
| Semantic caching for queries | Medium | HIGH |
| LangGraph upgrade + checkpointing | Medium | HIGH |
| One-click evaluation dashboard | Medium | HIGH |
| Config version history with diffs | Medium | Medium |
| UI component test coverage | Medium | Medium |

### Tier 3: Strategic / Experimental

| Feature | Complexity | Impact |
|---------|------------|--------|
| ColBERT multi-vector with Qdrant | Hard | HIGH |
| ColPali vision retrieval | Hard | Medium-High |
| DSPy prompt optimization | Hard | HIGH |
| Visual drag-and-drop pipeline builder | Hard | HIGH |
| Multi-agent RAG | Hard | Medium |
| Qdrant as optional vector store | Medium | Medium |
| Agentic RAG (retrieval as tool) | Medium | HIGH |

---

## 12. New Dependencies & Config Models

### Python Dependencies to Add

```txt
# Evaluation
ragas>=0.1.10
deepeval>=0.21.0

# Observability
langfuse>=2.0.0

# Guardrails
llm-guard>=0.3.0

# Advanced Retrieval
ragatouille>=0.0.8           # ColBERT reranking

# Document Processing
docling>=1.0.0               # Structured PDF parsing (uncomment)

# Embeddings (new providers)
cohere>=5.0.0
voyageai>=0.2.0

# Resilience
pybreaker>=1.0.0             # Circuit breaker for LLM providers

# Optional / Experimental
# colpali-engine>=0.2.0      # Vision retrieval
# dspy-ai>=2.4.0             # Prompt optimization
# gptcache>=0.1.0            # Semantic caching
```

### New Enum Values

```python
# AgentTemplate additions
ADAPTIVE = "adaptive"
SPECULATIVE = "speculative"
GRAPH_RAG = "graph_rag"
AGENTIC_RAG = "agentic_rag"

# ChunkingStrategy additions
LATE_CHUNKING = "late_chunking"
CONTEXTUAL = "contextual"
HIERARCHICAL = "hierarchical"

# EmbeddingProvider additions
COHERE = "cohere"
VOYAGE = "voyage"
JINA = "jina"
COLBERT = "colbert"

# RetrievalMethod additions
COLBERT = "colbert"
GLOBAL_GRAPH = "global_graph"

# New enum
class GuardrailsProvider(str, Enum):
    LLM_GUARD = "llm_guard"
    NEMO = "nemo"
    GUARDRAILS_AI = "guardrails_ai"
```

### New Config Models

```python
class GuardrailsConfig(BaseModel):
    enabled: bool = False
    provider: GuardrailsProvider = GuardrailsProvider.LLM_GUARD
    detect_pii: bool = True
    detect_prompt_injection: bool = True
    detect_toxicity: bool = False
    blocked_topics: List[str] = []
    max_output_tokens: int = 4096
    require_grounding: bool = False

class EvaluationConfig(BaseModel):
    enabled: bool = False
    framework: str = "ragas"  # "ragas" | "deepeval"
    metrics: List[str] = ["faithfulness", "answer_relevancy", "context_precision"]
    test_dataset_id: Optional[str] = None
    auto_evaluate: bool = False

class CachingConfig(BaseModel):
    embedding_cache_enabled: bool = True
    embedding_cache_ttl: int = 3600  # seconds
    semantic_cache_enabled: bool = False
    semantic_cache_similarity_threshold: float = 0.95

class ObservabilityConfig(BaseModel):
    enabled: bool = False
    provider: str = "langfuse"  # "langfuse" | "langsmith" | "phoenix"
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    trace_sampling_rate: float = 1.0
```

---

## Research Follow-Up Items

These areas may have evolved since the knowledge cutoff and should be verified with fresh web searches:

1. **LangGraph version** — check if 1.0 has been released
2. **MongoDB Atlas Vector Search** — any new features from MongoDB.local 2025/2026
3. **RAGAS API changes** — significant changes between 0.1 and 0.2
4. **Docling latest capabilities** — version and features
5. **New embedding models** — OpenAI, Cohere releases post-May 2025
6. **LangChain/LangGraph blog posts** — new agent patterns

---

*Report compiled from: PLAN.md compliance audit (85 tasks checked), deep code quality review (33 issues across 4 services + 2 UIs + gateway), and research on latest RAG techniques across 10 domains.*

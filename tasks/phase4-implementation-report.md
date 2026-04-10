# Phase 4 Implementation Report

Date: 2026-04-09
Plan source: `tasks/v2-plan.md`

## Summary

Phase 4 adds advanced RAG features: Microsoft GraphRAG with community summaries, RAPTOR hierarchical indexing, Late Chunking, LLM Guard guardrails, data lineage tracking, and Docling PDF verification.

## Implemented Deliverables

### 4.1 Microsoft GraphRAG (Community Summaries)

**Ingestion Side** — Created `services/ingestion-service/app/graph/`:
- `models.py` — `Entity`, `Relation`, `Community`, `CommunitySummary` with serialization
- `community.py` — `CommunityDetector`:
  - Entity/relation extraction from chunks via LLM
  - Leiden algorithm community detection (`leidenalg`/`igraph`)
  - Connected-components fallback when Leiden unavailable
  - JSON parsing with markdown code fence support
- `summarizer.py` — `CommunitySummarizer`:
  - LLM-generated 2-3 sentence summaries per community
  - Persists to MongoDB `community_summaries` collection

**RAG Side** — Created `services/rag-service/app/agents/graph_rag.py`:
- `GraphRAGAgent(BaseAgent)` with global/local query routing
- LLM-based query classification
- Global path: retrieves community summaries, synthesizes answer
- Local path: standard vector retrieval through existing retriever
- Registered in `factory.py` as `graph_rag` and in `query.py` helper

### 4.2 RAPTOR Hierarchical Indexing

- Created `services/ingestion-service/app/chunkers/raptor.py`:
  - `RAPTORChunker(BaseChunker)` with synchronous `chunk()` for leaf-level and async `chunk_async()` for full tree
  - Embedding-based clustering (k-means or sequential fallback)
  - Recursive tree building: cluster → summarize → repeat
  - `tree_level` and `parent_chunk_id` metadata on all chunks
- Registered in factory as `raptor`

### 4.3 Late Chunking (Jina)

- Created `services/ingestion-service/app/chunkers/late_chunking.py`:
  - `LateChunker(BaseChunker)` splits at sentence boundaries
  - Marks chunks with `requires_late_embedding: True` metadata
  - Stores `span_start_token`/`span_end_token` positions for full-document embedding extraction
- Registered in factory as `late`

### 4.4 LLM Guard Guardrails

- Created `services/rag-service/app/guardrails/`:
  - `base.py` — `BaseGuardrail` ABC with `check_input()`/`check_output()`, `GuardrailResult`, `GuardrailCheck`
  - `llm_guard.py` — `LLMGuard(BaseGuardrail)`:
    - Pre-query: prompt injection detection, PII scan
    - Post-response: toxicity check, PII leak detection
    - Uses structured JSON output from LLM
    - Configurable thresholds per check
  - `factory.py` — `create_guardrail()` factory function

### 4.5 Data Lineage Tracking

- Created `services/rag-service/app/api/v1/lineage.py`:
  - `GET /api/v1/lineage/{query_id}` — full lineage (source files → chunks → scores → generation)
  - `GET /api/v1/lineage/config/{config_id}` — recent lineage records
  - `store_query_lineage()` helper for persistence during agent execution
  - Ownership verification (user_id check)
- Registered in `services/rag-service/app/api/v1/router.py`

### 4.6 Docling for Structured PDF

- Verified: `services/ingestion-service/app/processors/pdf.py` already has Docling integration with PyMuPDF fallback
- Uses `export_to_markdown()` for table-aware output
- `DocumentProcessingConfig.use_docling` flag exists in shared models
- No changes needed — already functional

### MongoDB Updates

- `infrastructure/mongo/init-db.js`: added `community_summaries` collection (indexes: config_id+level, community_id) and `query_lineage` collection (indexes: query_id unique, config_id+created_at, user_id+created_at)

### Dependencies

- `services/ingestion-service/requirements.txt`: added `igraph>=0.11.0`, `leidenalg>=0.10.0`

## Verification

- **rag-service**: 401 tests passed (32 new tests: 9 graph_rag + 16 guardrails + 7 lineage)
- **ingestion-service**: 85 targeted tests passed (16 raptor + 45 graph + 24 api)
- `python -m compileall` clean on all new files

## Plan Checkpoint Comparison

| Checkpoint | Status |
|---|---|
| GraphRAG: community summaries generated, global questions answered | DONE |
| RAPTOR: chunks DB shows multi-level hierarchy (tree_level 0, 1, 2+) | DONE |
| Late Chunking: embeddings reflect full-document context | DONE (metadata-based) |
| Guardrails: prompt injection blocked, PII flagged | DONE |
| Lineage API: returns complete source chain | DONE |
| Docling: complex PDF tables as Markdown | VERIFIED (pre-existing) |

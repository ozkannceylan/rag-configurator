# Graph Report - .  (2026-04-10)

## Corpus Check
- 277 files · ~236,012 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4668 nodes · 5339 edges · 332 communities detected
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `VectorStore` - 28 edges
2. `ReActAgent` - 24 edges
3. `GraphStore` - 23 edges
4. `IngestionPipeline` - 20 edges
5. `SelfRAGAgent` - 19 edges
6. `TestPromptManager` - 19 edges
7. `CRAGAgent` - 18 edges
8. `PromptManager` - 18 edges
9. `RBACEnforcer` - 18 edges
10. `GraphRetriever` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Application settings loaded from environment variables.` --rationale_for--> `Settings`  [EXTRACTED]
  C:\Users\ozkan\projects\rag-configurator\services\config-service\app\core\settings.py → C:\Users\ozkan\projects\rag-configurator\services\rag-service\app\core\settings.py
- `MongoDB connection manager.` --rationale_for--> `MongoDB`  [EXTRACTED]
  C:\Users\ozkan\projects\rag-configurator\services\config-service\app\db\mongodb.py → C:\Users\ozkan\projects\rag-configurator\services\rag-service\app\db\mongodb.py
- `Create synchronous test client.` --rationale_for--> `client()`  [EXTRACTED]
  C:\Users\ozkan\projects\rag-configurator\services\ingestion-service\tests\conftest.py → C:\Users\ozkan\projects\rag-configurator\tests\e2e\conftest.py
- `Create a test client with mocked dependencies.` --rationale_for--> `client()`  [EXTRACTED]
  C:\Users\ozkan\projects\rag-configurator\services\rag-service\tests\conftest.py → C:\Users\ozkan\projects\rag-configurator\tests\e2e\conftest.py
- `Type of retrieval source.` --rationale_for--> `ChunkingConfig`  [EXTRACTED]
  C:\Users\ozkan\projects\rag-configurator\services\rag-service\app\retrieval\base.py → C:\Users\ozkan\projects\rag-configurator\services\ingestion-service\app\chunkers\base.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (225): abortWithAuthError(), abortWithServiceError(), Auth(), get_config_by_id(), get_config_owner(), login(), LoginRequest, logout() (+217 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (188): AgentConfig, AgentState, from_mongo_doc(), MessageRole, Type of retrieval source., Types of agent steps., State for LangGraph agent execution., SourceType (+180 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (99): ABC, AgentConfig, AgentError, AgentResponse, AgentStep, BaseAgent, BaseChunker, BaseEmbedder (+91 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (83): Tests for LLM module., Test converting usage to dictionary., Test default usage values., Tests for LLMResponse class., Test creating response., Test response with usage stats., Test converting response to dictionary., Tests for LLMConfig class. (+75 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (63): Tests for graph extraction, storage, community detection, and summarization., Tests for EntityExtractor., Test creating an extractor., Test building prompt with auto extract., Test building prompt with schema constraints., Test parsing valid JSON response., Test parsing invalid JSON response., Test that low confidence results are filtered. (+55 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (55): AnthropicLLM, Anthropic LLM implementation., Stream a response from Anthropic Claude.          Args:             messages:, Anthropic Claude LLM client., Prepare messages for Anthropic API.          Anthropic expects system messages, Handle Anthropic API errors., Clean up Anthropic client., Initialize Anthropic LLM.          Args:             config: LLM configuratio (+47 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (90): get_data(), get_id(), make_config(), Helper utilities for E2E tests., Extract ID from response data, supporting both 'id' and '_id' field names., Build a valid config payload matching the current API schema., Extract data from API response, supporting both envelope and direct formats., E2E tests for authentication flow. (+82 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (55): Tests for prompt management module., Test default configuration., Test custom configuration., Test creating config from dictionary., Tests for PromptTemplate class., Test creating a template., Test variable extraction., Tests for context and history formatting. (+47 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (51): Tests for ReAct agent module., Tests for Observation class., Test creating an observation., Test failed observation., Tests for ReActConfig class., Test default configuration., Test custom configuration., Test creating config from dictionary. (+43 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (55): Tests for ingestion task and utilities., Test hashing nonexistent file returns empty string., Tests for directory scanning., Test basic directory scanning., Test recursive directory scanning., Test non-recursive directory scanning., Test scanning with specific extensions., Test scanning nonexistent directory. (+47 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (50): Tests for hybrid retrieval and factory modules., Test RRF with multiple rankings., Test RRF with empty rankings., Test that k parameter affects scores., Test that documents appearing in multiple rankings get boosted., Tests for HybridRetriever., Test creating a hybrid retriever., Test creating retriever with custom config. (+42 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (49): BaseChunker, DocumentChunker, FixedSizeChunker, ParagraphChunker, Document-level chunker that returns the entire document as one chunk., Document-level chunker that treats the entire document as a single chunk., Fixed-size chunker that splits text into equal-sized chunks.      Simpler than, Split text into fixed-size chunks.          Args:             text: The text (+41 more)

### Community 12 - "Community 12"
Cohesion: 0.02
Nodes (47): Tests for text chunkers., Test chunking simple text., Test that chunks respect size limit., Test chunking text with paragraphs., Test chunking empty text., Test chunking with metadata., Tests for SemanticChunker., Test that chunking respects sentence boundaries. (+39 more)

### Community 13 - "Community 13"
Cohesion: 0.03
Nodes (46): BaseAgent, GraphRAGAgent, GraphRAGConfig, GraphRAG agent: uses community summaries for global questions., Classify query as global or local using LLM.          Returns:             "glob, Retrieve community summaries from MongoDB., Generate answer from community summaries (global path)., Generate answer from vector-retrieved chunks (local path). (+38 more)

### Community 14 - "Community 14"
Cohesion: 0.04
Nodes (41): BaseHTTPMiddleware, createTestToken(), getTestConfig(), registerAndLogin(), setupGateway(), TestCORSOnEndpoints(), TestE2EAuthFlow(), TestE2EConfigCRUD() (+33 more)

### Community 15 - "Community 15"
Cohesion: 0.03
Nodes (69): async_client(), auth_headers(), check_mongodb_available(), client(), created_config_id(), event_loop(), get_data(), get_id() (+61 more)

### Community 16 - "Community 16"
Cohesion: 0.03
Nodes (40): Tests for CRAG (Corrective RAG) agent module., Tests for RelevanceGrade enum., Test creating a CRAG agent., Test creating agent with custom config., Tests for RelevanceEvaluation class., Test creating an evaluation., Tests for evaluation response parsing., Test parsing complete evaluation response. (+32 more)

### Community 17 - "Community 17"
Cohesion: 0.03
Nodes (38): Tests for agent module., Test response with steps., Test converting response to dictionary., Tests for AgentConfig class., Test default configuration., Test custom configuration., Test creating config from dictionary., Tests for AgentError class. (+30 more)

### Community 18 - "Community 18"
Cohesion: 0.04
Nodes (47): AuthLoadUser, BurstAuthUser, on_request(), Authentication load testing scenarios.  Tests the authentication system's abilit, Simulates burst authentication traffic.     Used for testing spike handling., Track authentication-specific metrics., User class for authentication load testing.          Simulates concurrent authen, Start with login to establish baseline. (+39 more)

### Community 19 - "Community 19"
Cohesion: 0.03
Nodes (44): Tests for graph retrieval module., Tests for GraphContext., Test creating graph context., Test converting context to dictionary., Tests for GraphConfig., Test default configuration., Test custom configuration., Test creating config from dictionary. (+36 more)

### Community 20 - "Community 20"
Cohesion: 0.03
Nodes (42): Tests for embedding providers., Test getting embedder with custom config., Test getting embedder with invalid provider., Test getting available providers., Test getting provider information., Test default config for OpenAI., Test default config for Ollama., Test default config for HuggingFace. (+34 more)

### Community 21 - "Community 21"
Cohesion: 0.03
Nodes (37): Tests for retrieval module., Tests for RetrievalConfig., Test default configuration., Test custom configuration., Test creating config from dictionary., Tests for RetrievalResult., Test creating retrieval result., Test converting result to dictionary. (+29 more)

### Community 22 - "Community 22"
Cohesion: 0.03
Nodes (34): Tests for keyword retrieval module., Test simple highlight generation., Tests for KeywordConfig., Test highlights with multiple query terms., Test highlights when no match found., Test that highlights include context., Test default configuration., Integration tests for KeywordRetriever with mocked MongoDB. (+26 more)

### Community 23 - "Community 23"
Cohesion: 0.04
Nodes (42): AsyncIterator, build_authorized_mock_db(), Tests for ingestion API endpoints., Tests for root API endpoints., Test API v1 root endpoint., Tests for starting ingestion., Build a database mock that authorizes the default test user., Tests for getting ingestion status. (+34 more)

### Community 24 - "Community 24"
Cohesion: 0.04
Nodes (28): Vector store for chunks and embeddings in MongoDB., Get a document by ID., Get all documents for a config., Check if a document with the same content already exists., Delete a document and its chunks., Delete all documents and chunks for a config., Store multiple chunk records.          Args:             chunks: List of chun, Store a single chunk record. (+20 more)

### Community 25 - "Community 25"
Cohesion: 0.04
Nodes (15): MockLLM, Tests for the evaluation framework (models, RAGAS evaluator, judge evaluator, AP, If the LLM raises, the metric gets score 0 with an error explanation., A mock LLM that returns configurable responses., Test the evaluation API endpoints via the ASGI test client., POST /api/v1/evaluation/evaluate should return evaluation results., Should reject requests without X-User-ID header., GET /api/v1/evaluation/{config_id} should return evaluation runs. (+7 more)

### Community 26 - "Community 26"
Cohesion: 0.05
Nodes (30): PromptConfig, PromptError, PromptManager, PromptTemplate, Prompt manager for template loading and variable substitution., Manages prompt templates with variable substitution and optional tracking., Initialize prompt manager.          Args:             config: Prompt configur, Load default templates from YAML files. (+22 more)

### Community 27 - "Community 27"
Cohesion: 0.05
Nodes (29): BaseRetriever, KeywordConfig, KeywordRetriever, Keyword retriever using MongoDB Atlas Search or text index fallback., Ensure text index exists for fallback search., Retrieve relevant chunks using keyword search.          Args:             que, Search using MongoDB Atlas Search., Configuration for keyword search. (+21 more)

### Community 28 - "Community 28"
Cohesion: 0.05
Nodes (28): Config, GraphEdge, GraphNode, GraphStore, normalize_name(), Graph storage for nodes and edges in MongoDB., Initialize graph store.          Args:             db: MongoDB database insta, Create necessary indexes for efficient queries. (+20 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (31): GraphConfig, GraphContext, GraphEdge, GraphNode, GraphRetrievalResult, GraphRetriever, Graph retriever using knowledge graph traversal., Result of graph-based retrieval. (+23 more)

### Community 30 - "Community 30"
Cohesion: 0.04
Nodes (27): AuditRepository, Audit log repository., Repository for audit log persistence., Create a new audit log entry., BaseRepository, ConfigRepository, Configuration repository for database operations., Repository for RAG pipeline configuration operations. (+19 more)

### Community 31 - "Community 31"
Cohesion: 0.05
Nodes (30): create_rbac_enforcer(), get_default_rbac_config(), RBAC (Role-Based Access Control) enforcement for retrieval results., Build MongoDB filter for allowed folders.          Args:             role: User, Configuration for RBAC enforcement., Build Atlas Search filter clauses for allowed folders.          Args:, Filter retrieval results based on role permissions.          Args:             r, Filter results by access tags.          Args:             results: List of retri (+22 more)

### Community 32 - "Community 32"
Cohesion: 0.07
Nodes (49): build_idempotency_key(), cancel_ingestion(), CancelIngestionResponse, compute_data_source_hash(), delete_ingestion_data(), format_datetime(), get_ingestion_collection(), get_ingestion_history() (+41 more)

### Community 33 - "Community 33"
Cohesion: 0.04
Nodes (25): Tests for document processors., Test supported extensions., Test can_process method., Tests for ProcessedDocument dataclass., Tests for processor factory., Test getting supported extensions., Test is_supported function., Test success property when content exists. (+17 more)

### Community 34 - "Community 34"
Cohesion: 0.06
Nodes (30): cancel_ingestion(), compute_retry_countdown(), get_ingestion_status(), IngestionPipeline, Main Celery task for document ingestion pipeline., Load configuration from MongoDB., Build a safe filter for config lookups/updates., Update ingestion job status in MongoDB. (+22 more)

### Community 35 - "Community 35"
Cohesion: 0.04
Nodes (25): Tests for folder scanning service (no MongoDB required)., Test scanning nested directories., Test that scanning nonexistent path raises ValueError., Test that scanning a file instead of directory raises ValueError., Tests for FolderService., Test that unsupported source type raises NotImplementedError., Test that file counting is correct., Test that hidden files are ignored. (+17 more)

### Community 36 - "Community 36"
Cohesion: 0.04
Nodes (28): Tests for vector storage layer., Test conversion to MongoDB document., Test chunk RBAC metadata., Tests for IngestionRecord model., Test creating an ingestion record., Test ingestion progress calculation., Test progress with zero files., Tests for DocumentRecord model. (+20 more)

### Community 37 - "Community 37"
Cohesion: 0.05
Nodes (35): compute_content_hash(), compute_file_hash(), create_sync_mongodb_client(), format_file_size(), get_all_supported_extensions(), get_file_metadata(), get_folder_path(), get_processor_type() (+27 more)

### Community 38 - "Community 38"
Cohesion: 0.04
Nodes (20): cache(), connected_cache(), Tests for EmbeddingCache., Test batch get operation., Create an EmbeddingCache instance (not connected)., Test batch set operation., Test connect/disconnect., Test graceful degradation when Redis is unavailable. (+12 more)

### Community 39 - "Community 39"
Cohesion: 0.05
Nodes (25): integration_db(), integration_files(), Integration tests for the complete ingestion pipeline.  These tests require Mo, Integration tests for the complete ingestion pipeline., Get integration test database., Integration tests for document processors., Integration tests for chunkers., Test recursive chunker with real content. (+17 more)

### Community 40 - "Community 40"
Cohesion: 0.06
Nodes (25): BaseProcessor, DocxProcessor, Word document processor for .docx files., Extract table data as a 2D list., Processor for Microsoft Word documents (.docx)., Convert table data to text representation., Process a Word document and extract content.          Args:             file_, ImageProcessor (+17 more)

### Community 41 - "Community 41"
Cohesion: 0.05
Nodes (23): Tests for security utilities (no MongoDB required)., Test decoding invalid token returns None., Test decoding tampered token returns None., Test creating access token with custom expiry., Test creating refresh token with custom expiry., Tests for token payload contents., Test access token contains all required fields., Test refresh token contains all required fields. (+15 more)

### Community 42 - "Community 42"
Cohesion: 0.05
Nodes (39): default_config(), raptor(), Tests for RAPTOR hierarchical chunker., Test async RAPTOR tree building with mock LLM., Test async chunk without LLM returns leaf chunks only., Create default chunking config., Test RAPTOR with embedding-based clustering., Test async chunk with empty text. (+31 more)

### Community 43 - "Community 43"
Cohesion: 0.06
Nodes (39): guard(), _make_response(), mock_llm(), Tests for LLM Guard guardrails., Test PII leakage detection in generated response., Test that a clean response passes toxicity check., Create a mock LLM for guardrail checks., Test that toxic content is blocked. (+31 more)

### Community 44 - "Community 44"
Cohesion: 0.05
Nodes (16): cache(), connected_cache(), Tests for QueryCache., Test config invalidation., Create a QueryCache instance (not connected)., Test connect/disconnect., Test graceful degradation when Redis is unavailable., All operations should silently no-op when not connected. (+8 more)

### Community 45 - "Community 45"
Cohesion: 0.07
Nodes (20): MultiQueryAgent, MultiQueryConfig, MultiQueryState, Multi-Query agent implementation using LangGraph., Multi-Query RAG agent with query expansion.      Flow:     Query → Generate Vari, Initialize Multi-Query agent.          Args:             retriever: Retriever fo, Initialize LangGraph if available., Build the LangGraph state graph. (+12 more)

### Community 46 - "Community 46"
Cohesion: 0.06
Nodes (19): Tests for PromptManager class., Test creating prompt manager., Test creating manager with config., Test getting default system prompt., Test getting named system prompt., Test system prompt config override., Test getting RAG prompt., Test RAG prompt with history. (+11 more)

### Community 47 - "Community 47"
Cohesion: 0.08
Nodes (22): EntityExtractor, ExtractedEntity, ExtractedRelation, ExtractionConfig, ExtractionResult, LLM-based entity and relationship extraction., Initialize entity extractor.          Args:             config: Extraction co, Get or create HTTP client. (+14 more)

### Community 48 - "Community 48"
Cohesion: 0.08
Nodes (18): HybridConfig, HybridRetrievalResult, HybridRetriever, Combines multiple retrieval methods with score fusion.      Supported retrieve, Initialize hybrid retriever.          Args:             db: MongoDB database, Get or create vector retriever., Get or create keyword retriever., Get or create graph retriever. (+10 more)

### Community 49 - "Community 49"
Cohesion: 0.07
Nodes (20): Tests for RAG service settings., Test parsing CORS origins from comma-separated string., Test default settings values., Test timeout configuration., Test CORS origins parsing from string., Test MongoDB settings., Test Celery broker falls back to Redis URL., Test LLM provider settings. (+12 more)

### Community 50 - "Community 50"
Cohesion: 0.1
Nodes (16): vLLM client for self-hosted inference servers., Stream a response from vLLM.          Args:             messages: List of mes, vLLM client for OpenAI-compatible inference servers., Initialize vLLM client.          Args:             config: LLM configuration, List available models from vLLM server.          Returns:             List of, Get information about the current model.          Returns:             Model, Check if vLLM server is available.          Returns:             True if serv, Handle HTTP errors from vLLM. (+8 more)

### Community 51 - "Community 51"
Cohesion: 0.1
Nodes (21): BaseLLMRateLimitError, AlreadyExistsException, ForbiddenException, LLMAuthError, LLMConnectionError, LLMRateLimitError, NotFoundException, Shared LLM provider exception types. (+13 more)

### Community 52 - "Community 52"
Cohesion: 0.07
Nodes (25): graph_rag_agent(), mock_db(), mock_retriever(), Tests for GraphRAG agent., Create a GraphRAG agent instance., Test that broad queries are classified as global., Test that specific queries are classified as local., Test that ambiguous classification defaults to local. (+17 more)

### Community 53 - "Community 53"
Cohesion: 0.11
Nodes (25): computeBodyHash(), readAndRestoreBody(), signaturePayload(), SignRequest(), build_signed_headers(), compute_body_hash(), copy_signed_headers(), HMACVerificationError (+17 more)

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (19): get_config_details(), list_configs(), on_test_start(), on_test_stop(), PeakLoadUser, query_rag(), RAGUser, Performance testing configuration for RAG Configurator.  This Locust file define (+11 more)

### Community 55 - "Community 55"
Cohesion: 0.08
Nodes (23): Tests for template marketplace endpoints., Test listing templates., Test listing templates with category filter., Sample configuration data for creating a template source., Test listing templates with search., Test getting a specific template., Test cloning a template as a new config., Test deleting a template. (+15 more)

### Community 56 - "Community 56"
Cohesion: 0.11
Nodes (14): GraphBuildConfig, GraphBuilder, GraphBuildResult, Graph builder for orchestrating extraction and storage., Build graph from a list of text chunks.          Args:             chunks: Li, Configuration for graph building., Embed entities that don't have embeddings yet., Build graph from a single text.          Args:             text: Text content (+6 more)

### Community 57 - "Community 57"
Cohesion: 0.12
Nodes (13): BaseEvaluator, JudgeEvaluator, _parse_judge_response(), LLM-as-Judge evaluator with configurable rubrics.  Uses a (possibly different) L, Evaluate RAG outputs using an LLM judge with rubric-based scoring.      Args:, Run the judge evaluation and return an ``EvaluationResult``., Parse the structured JSON from the judge LLM., _parse_score_response() (+5 more)

### Community 58 - "Community 58"
Cohesion: 0.1
Nodes (19): global_exception_handler(), health_check(), health_detailed(), lifespan(), liveness_check(), main(), RAG Service - FastAPI application for query processing., Health check endpoint. (+11 more)

### Community 59 - "Community 59"
Cohesion: 0.13
Nodes (12): get_embedder(), QueryEmbedder, Embedding utilities for retrieval., Generate embeddings for multiple texts using OpenAI API., Generates embeddings for queries., Generate embedding using Ollama API., Get an embedder instance.      Args:         provider: Embedding provider (de, Initialize query embedder.          Args:             provider: Embedding pro (+4 more)

### Community 60 - "Community 60"
Cohesion: 0.12
Nodes (15): get_database(), get_db(), MongoDB, MongoDB connection management., MongoDB connection manager., Disconnect from MongoDB., Get the database instance., Disconnect from MongoDB. (+7 more)

### Community 61 - "Community 61"
Cohesion: 0.27
Nodes (17): setupGateway(), setupMockBackend(), TestProxy_AddsForwardedHeaders(), TestProxy_CircuitBreakerOpensAfterRepeatedFailures(), TestProxy_CopiesResponseHeaders(), TestProxy_DELETE_Method(), TestProxy_ForwardsAuthorizationHeader(), TestProxy_ForwardsBody() (+9 more)

### Community 62 - "Community 62"
Cohesion: 0.11
Nodes (17): Tests for authentication endpoints., Test a refresh token is revoked once it is exchanged., Test logout blacklists the submitted refresh token., Test service API routes reject unsigned requests., Test user registration creates an audit log entry., Test registration with duplicate email., Test successful login., Test login with invalid password. (+9 more)

### Community 63 - "Community 63"
Cohesion: 0.11
Nodes (12): Tests for RAG service main application., Test API v1 root endpoint., Test CORS headers are present., Tests for root endpoints., Tests for providers endpoint., Tests for health check endpoints., test_api_v1_root(), test_cors_headers() (+4 more)

### Community 64 - "Community 64"
Cohesion: 0.14
Nodes (10): EmbeddingCache, Redis-backed cache for embedding vectors to avoid recomputation., Get cached embeddings for multiple texts.          Returns dict of index -> embe, Cache multiple embeddings with TTL. Uses Redis pipeline., Redis-backed cache for embedding vectors to avoid recomputation., Connect to Redis. Graceful fallback if unavailable., Close Redis connection., Generate cache key: prefix:model:sha256(text). (+2 more)

### Community 65 - "Community 65"
Cohesion: 0.33
Nodes (16): createTestToken(), newTestConfig(), setupGatewayServer(), setupMockBackend(), TestAuthRoutesExist(), TestCORSHeaders(), TestHealthEndpoint(), TestIngestionRoutesExist() (+8 more)

### Community 66 - "Community 66"
Cohesion: 0.14
Nodes (10): _apply_config_defaults(), ConfigService, Configuration service with business logic., List configurations for a user., Update configuration., Delete configuration., Duplicate a configuration., Service for configuration operations. (+2 more)

### Community 67 - "Community 67"
Cohesion: 0.11
Nodes (17): Tests for configuration endpoints., Test updating a configuration., Test deleting a configuration., Sample configuration data., Test config create/update/delete flows create audit log entries., Test that endpoints require authentication., Test creating a configuration., Test listing configurations. (+9 more)

### Community 68 - "Community 68"
Cohesion: 0.16
Nodes (11): BaseGuardrail, LLMGuard, _parse_json(), LLM-based guardrails for prompt injection, PII, and toxicity detection., Run pre-query guardrail checks.          Checks for prompt injection and PII in, Run post-response guardrail checks.          Checks for toxicity and PII leakage, Check for prompt injection attempts., Check for PII in text. (+3 more)

### Community 69 - "Community 69"
Cohesion: 0.16
Nodes (15): build_pipeline_config(), build_stream_events(), API endpoints for streaming responses., Build SSE payloads for a streaming response., Yield prebuilt SSE events., Stream a RAG response via Server-Sent Events.      This endpoint provides real-t, Stream a RAG response via Server-Sent Events (POST).      Same as GET but accept, Resolve base URL, preferring OLLAMA_BASE_URL env var for ollama providers. (+7 more)

### Community 70 - "Community 70"
Cohesion: 0.14
Nodes (11): _doc_to_run(), EvaluationRepository, MongoDB repository for evaluation runs., Map a 0-1 score to a distribution bucket., Convert a MongoDB document to an ``EvaluationRun``., Persist and query evaluation runs in MongoDB., Insert an evaluation run and return its document id., Return evaluation runs for a config, newest first. (+3 more)

### Community 71 - "Community 71"
Cohesion: 0.13
Nodes (9): QueryCache, Redis-backed cache for RAG query responses., Invalidate all cached queries for a config (uses SCAN pattern)., Redis-backed cache for RAG query responses., Connect to Redis. Graceful fallback if unavailable., Close Redis connection., Generate key: prefix:config_id:sha256(query)., Get cached query response. Returns None on miss. (+1 more)

### Community 72 - "Community 72"
Cohesion: 0.16
Nodes (8): AuthService, Authentication service with business logic., Blacklist access and refresh tokens until they expire., Create access and refresh tokens., Blacklist a token when it is valid and matches the expected type., Service for authentication operations., Authenticate user and return tokens., Refresh access token using refresh token.

### Community 73 - "Community 73"
Cohesion: 0.16
Nodes (10): _check_leiden(), CommunityDetector, _parse_extraction(), Community detection for knowledge graphs using Leiden algorithm., Detect communities in the knowledge graph.          Uses Leiden algorithm when a, Community detection via Leiden algorithm (igraph + leidenalg)., Fallback: group entities by connected components using union-find., Detect communities in knowledge graph using Leiden algorithm. (+2 more)

### Community 74 - "Community 74"
Cohesion: 0.12
Nodes (15): Tests for data lineage tracking endpoint., Test GET /api/v1/lineage/{query_id}., Test GET lineage returns 404 for missing query., Test GET lineage returns 403 for wrong user., Test GET /api/v1/lineage/config/{config_id}., Test query ID generation., Test storing lineage to MongoDB., Test storing lineage with dict sources (not RetrievedChunk). (+7 more)

### Community 75 - "Community 75"
Cohesion: 0.12
Nodes (15): decode_token(), extract_bearer_token(), get_token_jti(), get_token_subject(), get_token_ttl_seconds(), get_token_type(), Shared JWT parsing helpers used across Python services., Decode and validate a JWT, returning None on failure. (+7 more)

### Community 76 - "Community 76"
Cohesion: 0.17
Nodes (15): _ensure_instruments(), OpenTelemetry metrics for RAG pipeline observability.  Exposes convenience funct, Record the duration of a retrieval step., Record LLM token usage.      Args:         count: Number of tokens.         prov, Increment the error counter., Increment the cache-hit counter., Record an evaluation metric score., Lazily create OTel instruments on first use. (+7 more)

### Community 77 - "Community 77"
Cohesion: 0.24
Nodes (11): createTestToken(), setupRouter(), TestAuth_BlacklistCheckFailure(), TestAuth_ExpiredToken(), TestAuth_InvalidToken(), TestAuth_MalformedAuthHeader(), TestAuth_MissingHeader(), TestAuth_RefreshToken() (+3 more)

### Community 78 - "Community 78"
Cohesion: 0.14
Nodes (8): BaseSettings, get_settings(), Application settings using Pydantic Settings., Application configuration loaded from environment variables., Get cached settings instance., Get cached settings instance., Application settings loaded from environment variables., Settings

### Community 79 - "Community 79"
Cohesion: 0.16
Nodes (11): get_langfuse(), _LangfuseSpan, _NoOpSpan, Langfuse integration for LLM observability.  Provides ``setup_langfuse`` to wire, Drop-in replacement when Langfuse is not available., Thin wrapper around a Langfuse generation for deferred output., Initialise the global Langfuse client.      Args:         app: A FastAPI (or sim, Return the global Langfuse client, or ``None``. (+3 more)

### Community 80 - "Community 80"
Cohesion: 0.16
Nodes (13): _build_evaluator(), evaluate(), EvaluateRequest, _generate_answer_and_contexts(), get_evaluation_history(), get_evaluation_summary(), API endpoints for RAG evaluation., Get evaluation history for a configuration. (+5 more)

### Community 81 - "Community 81"
Cohesion: 0.18
Nodes (3): newTestConfig(), TestHealth_AlwaysReturns200(), TestHealth_ReturnsHealthy()

### Community 82 - "Community 82"
Cohesion: 0.27
Nodes (10): setupCORSRouter(), TestCORS_AllowedOrigin(), TestCORS_DisallowedOrigin(), TestCORS_MultipleAllowedOrigins(), TestCORS_NoOriginHeader(), TestCORS_OriginWithPort(), TestCORS_PreflightDisallowedOrigin(), TestCORS_PreflightRequest() (+2 more)

### Community 83 - "Community 83"
Cohesion: 0.24
Nodes (8): setupRateLimitRouter(), TestRateLimit_AllowsNormalTraffic(), TestRateLimit_BlocksExcessiveTraffic(), TestRateLimit_BurstAllowed(), TestRateLimit_ConcurrentRequests(), TestRateLimit_DifferentIPsConcurrent(), TestRateLimit_Returns429WithCorrectBody(), TestRateLimit_SeparateLimitersPerIP()

### Community 84 - "Community 84"
Cohesion: 0.17
Nodes (11): create_access_token(), create_refresh_token(), decode_token(), get_password_hash(), Security utilities for authentication., Verify a password against its hash., Generate password hash., Create JWT access token. (+3 more)

### Community 85 - "Community 85"
Cohesion: 0.24
Nodes (3): CircuitBreaker, circuitBreakerState, CircuitBreakerTransport

### Community 86 - "Community 86"
Cohesion: 0.18
Nodes (10): generate_embeddings(), process_document(), process_ingestion(), Celery tasks for document ingestion., Main ingestion task that orchestrates the ingestion pipeline.      Args:, # TODO: Implement ingestion pipeline, Process a single document.      Args:         document_path: Path to the docu, # TODO: Implement document processing (+2 more)

### Community 87 - "Community 87"
Cohesion: 0.29
Nodes (5): createTestToken(), TestValidateAccessToken_Expired(), TestValidateAccessToken_RefreshToken(), TestValidateAccessToken_Valid(), TestValidateAccessToken_WrongSecret()

### Community 88 - "Community 88"
Cohesion: 0.24
Nodes (6): FolderService, Folder scanning service., Analyze files directly in a folder (not recursive).          Returns tuple of, Service for scanning and analyzing folders., Scan a directory and return folder structure with detected file types., Recursively scan a directory.          Returns tuple of (folder_infos, all_det

### Community 89 - "Community 89"
Cohesion: 0.2
Nodes (9): Tests for Phase 0 RAG API security hardening., Unsigned API requests should be rejected by service auth middleware., Query endpoint should reject access to someone else's config., Query endpoint should surface provider failures as 503., Streaming endpoint should reject access to someone else's config., test_query_rejects_non_owner(), test_query_requires_hmac_signature(), test_query_returns_503_on_llm_provider_failure() (+1 more)

### Community 90 - "Community 90"
Cohesion: 0.22
Nodes (0): 

### Community 91 - "Community 91"
Cohesion: 0.42
Nodes (8): BadGateway(), BadRequest(), Error(), Forbidden(), InternalError(), NotFound(), ServiceUnavailable(), Unauthorized()

### Community 92 - "Community 92"
Cohesion: 0.22
Nodes (5): ExportService, Configuration export/import service., Service for exporting and importing configurations., Export configuration as YAML., Import configuration from YAML.

### Community 93 - "Community 93"
Cohesion: 0.25
Nodes (4): User service with business logic., Service for user operations., Soft delete user (deactivate)., UserService

### Community 94 - "Community 94"
Cohesion: 0.28
Nodes (6): CommunitySummarizer, Community summarization using LLM for GraphRAG., Generate LLM summaries for detected communities., Generate summaries for each community using an LLM.          Args:             c, Generate summary for a single community., _store_summaries()

### Community 95 - "Community 95"
Cohesion: 0.43
Nodes (3): ipRateLimiter, newIPRateLimiter(), RateLimit()

### Community 96 - "Community 96"
Cohesion: 0.25
Nodes (7): delete_current_user(), get_current_user_info(), User management endpoints., Get the currently authenticated user's information., Update the current user's information., Delete (deactivate) the current user's account., update_current_user()

### Community 97 - "Community 97"
Cohesion: 0.29
Nodes (4): AuditLogger, Audit logging helpers., Best-effort audit logger for state-changing config-service operations., Persist an audit log entry.

### Community 98 - "Community 98"
Cohesion: 0.33
Nodes (3): OpenTelemetry setup helpers shared by Python services., Configure OpenTelemetry tracing for a FastAPI service., setup_tracing()

### Community 99 - "Community 99"
Cohesion: 0.33
Nodes (5): export_config(), import_config(), Configuration export/import endpoints., Export a configuration as a YAML file., Import a configuration from a YAML file.

### Community 100 - "Community 100"
Cohesion: 0.33
Nodes (5): browse_folders(), Folder scanning endpoints., Scan a directory and return its structure with detected file types.      Curre, Browse directories at a given path for folder selection.      If path is empty, scan_folders()

### Community 101 - "Community 101"
Cohesion: 0.6
Nodes (3): getEnvOrDefault(), TestMain(), waitForService()

### Community 102 - "Community 102"
Cohesion: 0.6
Nodes (4): build_updates(), main(), parse_args(), Return the v2 defaults missing from a legacy config document.

### Community 103 - "Community 103"
Cohesion: 0.83
Nodes (3): CORS(), extractHost(), isOriginAllowed()

### Community 104 - "Community 104"
Cohesion: 0.5
Nodes (3): get_current_user(), API dependencies for dependency injection., Dependency to get current authenticated user from JWT token.      Extracts the

### Community 105 - "Community 105"
Cohesion: 0.5
Nodes (3): Tests for user endpoints., Test user state changes are recorded in the audit log., test_user_update_and_delete_write_audit_logs()

### Community 106 - "Community 106"
Cohesion: 0.5
Nodes (3): get_celery_app(), Celery application configuration., Get the Celery application instance.

### Community 107 - "Community 107"
Cohesion: 1.0
Nodes (0): 

### Community 108 - "Community 108"
Cohesion: 1.0
Nodes (0): 

### Community 109 - "Community 109"
Cohesion: 1.0
Nodes (0): 

### Community 110 - "Community 110"
Cohesion: 1.0
Nodes (1): Observability utilities (tracing, Langfuse, OpenTelemetry metrics).  All integra

### Community 111 - "Community 111"
Cohesion: 1.0
Nodes (0): 

### Community 112 - "Community 112"
Cohesion: 1.0
Nodes (0): 

### Community 113 - "Community 113"
Cohesion: 1.0
Nodes (0): 

### Community 114 - "Community 114"
Cohesion: 1.0
Nodes (0): 

### Community 115 - "Community 115"
Cohesion: 1.0
Nodes (0): 

### Community 116 - "Community 116"
Cohesion: 1.0
Nodes (0): 

### Community 117 - "Community 117"
Cohesion: 1.0
Nodes (1): Return CORS origins as list.

### Community 118 - "Community 118"
Cohesion: 1.0
Nodes (1): Convert MongoDB document to serializable dict.

### Community 119 - "Community 119"
Cohesion: 1.0
Nodes (1): Backfill optional v2 fields for legacy config documents.

### Community 120 - "Community 120"
Cohesion: 1.0
Nodes (1): Create a folder service instance.

### Community 121 - "Community 121"
Cohesion: 1.0
Nodes (1): Create a temporary directory structure for testing.

### Community 122 - "Community 122"
Cohesion: 1.0
Nodes (1): Generate embeddings for a list of texts.          Args:             texts: Li

### Community 123 - "Community 123"
Cohesion: 1.0
Nodes (1): Split text into chunks.          Args:             text: The text to split

### Community 124 - "Community 124"
Cohesion: 1.0
Nodes (1): Split text at word boundaries when it exceeds max size.

### Community 125 - "Community 125"
Cohesion: 1.0
Nodes (1): Minimal k-means implementation without numpy dependency.

### Community 126 - "Community 126"
Cohesion: 1.0
Nodes (1): Parse CORS origins from comma-separated string or list.

### Community 127 - "Community 127"
Cohesion: 1.0
Nodes (1): Get Celery broker URL, falling back to Redis URL.

### Community 128 - "Community 128"
Cohesion: 1.0
Nodes (1): Get Celery result backend URL, falling back to Redis URL.

### Community 129 - "Community 129"
Cohesion: 1.0
Nodes (1): Check if running in development mode.

### Community 130 - "Community 130"
Cohesion: 1.0
Nodes (1): Create an assistant message.

### Community 131 - "Community 131"
Cohesion: 1.0
Nodes (1): Get embedding dimensions for the current model.

### Community 132 - "Community 132"
Cohesion: 1.0
Nodes (1): Get embedding dimensions.

### Community 133 - "Community 133"
Cohesion: 1.0
Nodes (1): Get embedding dimensions for the current model.

### Community 134 - "Community 134"
Cohesion: 1.0
Nodes (1): Get embedding dimensions for the current model.

### Community 135 - "Community 135"
Cohesion: 1.0
Nodes (1): Check if leidenalg is available.

### Community 136 - "Community 136"
Cohesion: 1.0
Nodes (1): Parse LLM extraction output as JSON, with fallback handling.

### Community 137 - "Community 137"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 138 - "Community 138"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 139 - "Community 139"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 140 - "Community 140"
Cohesion: 1.0
Nodes (1): Persist community summaries to MongoDB.

### Community 141 - "Community 141"
Cohesion: 1.0
Nodes (1): Process a document and extract text content.          Args:             file_

### Community 142 - "Community 142"
Cohesion: 1.0
Nodes (1): Normalize entity name for matching.

### Community 143 - "Community 143"
Cohesion: 1.0
Nodes (1): Calculate progress percentage.

### Community 144 - "Community 144"
Cohesion: 1.0
Nodes (1): Calculate job duration in seconds.

### Community 145 - "Community 145"
Cohesion: 1.0
Nodes (1): Calculate progress percentage.

### Community 146 - "Community 146"
Cohesion: 1.0
Nodes (1): Test starting ingestion without X-User-ID is rejected.

### Community 147 - "Community 147"
Cohesion: 1.0
Nodes (1): Test unsigned ingestion requests are rejected by service auth middleware.

### Community 148 - "Community 148"
Cohesion: 1.0
Nodes (1): Test starting ingestion for someone else's config is rejected.

### Community 149 - "Community 149"
Cohesion: 1.0
Nodes (1): Test starting ingestion with non-existent config.

### Community 150 - "Community 150"
Cohesion: 1.0
Nodes (1): Test duplicate starts return the existing ingestion job.

### Community 151 - "Community 151"
Cohesion: 1.0
Nodes (1): Test successfully starting ingestion.                  Note: This test uses th

### Community 152 - "Community 152"
Cohesion: 1.0
Nodes (1): Test getting status when no ingestion exists.

### Community 153 - "Community 153"
Cohesion: 1.0
Nodes (1): Test getting status for pending ingestion.

### Community 154 - "Community 154"
Cohesion: 1.0
Nodes (1): Test getting status for running ingestion.

### Community 155 - "Community 155"
Cohesion: 1.0
Nodes (1): Test getting status for completed ingestion.

### Community 156 - "Community 156"
Cohesion: 1.0
Nodes (1): Test cancelling when no ingestion is running.

### Community 157 - "Community 157"
Cohesion: 1.0
Nodes (1): Test successfully cancelling a running ingestion.

### Community 158 - "Community 158"
Cohesion: 1.0
Nodes (1): Test retrying when no ingestion exists.

### Community 159 - "Community 159"
Cohesion: 1.0
Nodes (1): Test retrying ingestion that is not failed.

### Community 160 - "Community 160"
Cohesion: 1.0
Nodes (1): Test successfully retrying a failed ingestion.

### Community 161 - "Community 161"
Cohesion: 1.0
Nodes (1): Test getting logs when no ingestion exists.

### Community 162 - "Community 162"
Cohesion: 1.0
Nodes (1): Test getting logs with errors.

### Community 163 - "Community 163"
Cohesion: 1.0
Nodes (1): Test getting stats when no ingestion exists.

### Community 164 - "Community 164"
Cohesion: 1.0
Nodes (1): Test getting stats for an ingestion.

### Community 165 - "Community 165"
Cohesion: 1.0
Nodes (1): Test that history endpoint exists.

### Community 166 - "Community 166"
Cohesion: 1.0
Nodes (1): Test that status response has expected format.

### Community 167 - "Community 167"
Cohesion: 1.0
Nodes (1): Create recursive chunker instance with small min_chunk_size for testing.

### Community 168 - "Community 168"
Cohesion: 1.0
Nodes (1): Create sample text for testing.

### Community 169 - "Community 169"
Cohesion: 1.0
Nodes (1): Create semantic chunker instance with small min_chunk_size for testing.

### Community 170 - "Community 170"
Cohesion: 1.0
Nodes (1): Create text with multiple sentences.

### Community 171 - "Community 171"
Cohesion: 1.0
Nodes (1): Create document chunker instance.

### Community 172 - "Community 172"
Cohesion: 1.0
Nodes (1): Create paragraph chunker instance.

### Community 173 - "Community 173"
Cohesion: 1.0
Nodes (1): Create fixed size chunker instance.

### Community 174 - "Community 174"
Cohesion: 1.0
Nodes (1): Test embedding a single text with Ollama.

### Community 175 - "Community 175"
Cohesion: 1.0
Nodes (1): Test embedding multiple texts with Ollama.

### Community 176 - "Community 176"
Cohesion: 1.0
Nodes (1): Test embedding with specific model configuration.

### Community 177 - "Community 177"
Cohesion: 1.0
Nodes (1): Test extracting from empty text.

### Community 178 - "Community 178"
Cohesion: 1.0
Nodes (1): Test building from empty text.

### Community 179 - "Community 179"
Cohesion: 1.0
Nodes (1): Test fallback connected-components community detection.

### Community 180 - "Community 180"
Cohesion: 1.0
Nodes (1): Test detection with no entities.

### Community 181 - "Community 181"
Cohesion: 1.0
Nodes (1): Test that entities without relations become singleton communities.

### Community 182 - "Community 182"
Cohesion: 1.0
Nodes (1): Test entity extraction from chunks using mock LLM.

### Community 183 - "Community 183"
Cohesion: 1.0
Nodes (1): Test graceful handling of LLM errors.

### Community 184 - "Community 184"
Cohesion: 1.0
Nodes (1): Test community summarization with mock LLM.

### Community 185 - "Community 185"
Cohesion: 1.0
Nodes (1): Test that empty communities are skipped.

### Community 186 - "Community 186"
Cohesion: 1.0
Nodes (1): Test MongoDB persistence.

### Community 187 - "Community 187"
Cohesion: 1.0
Nodes (1): Test graceful LLM failure handling.

### Community 188 - "Community 188"
Cohesion: 1.0
Nodes (1): Create a test configuration in the database.

### Community 189 - "Community 189"
Cohesion: 1.0
Nodes (1): Test storing and retrieving documents.

### Community 190 - "Community 190"
Cohesion: 1.0
Nodes (1): Test storing and retrieving chunks with embeddings.

### Community 191 - "Community 191"
Cohesion: 1.0
Nodes (1): Test deleting all data for a config.

### Community 192 - "Community 192"
Cohesion: 1.0
Nodes (1): Test that stats return correct counts.

### Community 193 - "Community 193"
Cohesion: 1.0
Nodes (1): Test text processor in full pipeline.

### Community 194 - "Community 194"
Cohesion: 1.0
Nodes (1): Test HuggingFace embedder can embed texts (requires model download).

### Community 195 - "Community 195"
Cohesion: 1.0
Nodes (1): Create graph store for testing.

### Community 196 - "Community 196"
Cohesion: 1.0
Nodes (1): Test storing and retrieving graph nodes.

### Community 197 - "Community 197"
Cohesion: 1.0
Nodes (1): Test storing and retrieving graph edges.

### Community 198 - "Community 198"
Cohesion: 1.0
Nodes (1): Test that re-ingestion clears old data.

### Community 199 - "Community 199"
Cohesion: 1.0
Nodes (1): Insert a test config into the database.

### Community 200 - "Community 200"
Cohesion: 1.0
Nodes (1): Test starting ingestion and checking status.

### Community 201 - "Community 201"
Cohesion: 1.0
Nodes (1): Create text processor instance.

### Community 202 - "Community 202"
Cohesion: 1.0
Nodes (1): Create a temporary text file.

### Community 203 - "Community 203"
Cohesion: 1.0
Nodes (1): Create a temporary markdown file.

### Community 204 - "Community 204"
Cohesion: 1.0
Nodes (1): Test processing a text file.

### Community 205 - "Community 205"
Cohesion: 1.0
Nodes (1): Test processing a markdown file.

### Community 206 - "Community 206"
Cohesion: 1.0
Nodes (1): Test processing a non-existent file.

### Community 207 - "Community 207"
Cohesion: 1.0
Nodes (1): Test file metadata extraction.

### Community 208 - "Community 208"
Cohesion: 1.0
Nodes (1): Get number of sources.

### Community 209 - "Community 209"
Cohesion: 1.0
Nodes (1): Run the agent on a query.          Args:             query: User query

### Community 210 - "Community 210"
Cohesion: 1.0
Nodes (1): Stream the agent response.          Args:             query: User query

### Community 211 - "Community 211"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 212 - "Community 212"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 213 - "Community 213"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 214 - "Community 214"
Cohesion: 1.0
Nodes (1): Create a configured Naive RAG agent.          Args:             db: Database

### Community 215 - "Community 215"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 216 - "Community 216"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 217 - "Community 217"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 218 - "Community 218"
Cohesion: 1.0
Nodes (1): Parse CORS origins from comma-separated string or list.

### Community 219 - "Community 219"
Cohesion: 1.0
Nodes (1): Check if running in development mode.

### Community 220 - "Community 220"
Cohesion: 1.0
Nodes (1): Check if MLflow tracking is enabled.

### Community 221 - "Community 221"
Cohesion: 1.0
Nodes (1): Evaluate a query/answer pair.          Args:             query: The user query.

### Community 222 - "Community 222"
Cohesion: 1.0
Nodes (1): Run post-response guardrail checks.          Args:             query: Original u

### Community 223 - "Community 223"
Cohesion: 1.0
Nodes (1): Parse JSON from LLM response, handling markdown code fences.

### Community 224 - "Community 224"
Cohesion: 1.0
Nodes (1): Create a system message.

### Community 225 - "Community 225"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 226 - "Community 226"
Cohesion: 1.0
Nodes (1): Generate a response from the LLM.          Args:             messages: List o

### Community 227 - "Community 227"
Cohesion: 1.0
Nodes (1): Stream a response from the LLM.          Args:             messages: List of

### Community 228 - "Community 228"
Cohesion: 1.0
Nodes (1): Create config from dictionary.

### Community 229 - "Community 229"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 230 - "Community 230"
Cohesion: 1.0
Nodes (1): Create from MongoDB document.

### Community 231 - "Community 231"
Cohesion: 1.0
Nodes (1): Retrieve relevant chunks for a query.          Args:             query: User

### Community 232 - "Community 232"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 233 - "Community 233"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 234 - "Community 234"
Cohesion: 1.0
Nodes (1): Create from dictionary.

### Community 235 - "Community 235"
Cohesion: 1.0
Nodes (1): Create a mock retriever.

### Community 236 - "Community 236"
Cohesion: 1.0
Nodes (1): Create a mock prompt manager.

### Community 237 - "Community 237"
Cohesion: 1.0
Nodes (1): Create a naive RAG agent.

### Community 238 - "Community 238"
Cohesion: 1.0
Nodes (1): Test basic agent run.

### Community 239 - "Community 239"
Cohesion: 1.0
Nodes (1): Test agent run with conversation history.

### Community 240 - "Community 240"
Cohesion: 1.0
Nodes (1): Test that run includes execution steps.

### Community 241 - "Community 241"
Cohesion: 1.0
Nodes (1): Test run without step tracking.

### Community 242 - "Community 242"
Cohesion: 1.0
Nodes (1): Test that run tracks total duration.

### Community 243 - "Community 243"
Cohesion: 1.0
Nodes (1): Test that run tracks token usage.

### Community 244 - "Community 244"
Cohesion: 1.0
Nodes (1): Test run with minimum score filtering.

### Community 245 - "Community 245"
Cohesion: 1.0
Nodes (1): Test run_with_sources convenience method.

### Community 246 - "Community 246"
Cohesion: 1.0
Nodes (1): Test streaming response.

### Community 247 - "Community 247"
Cohesion: 1.0
Nodes (1): Test handling of retrieval errors.

### Community 248 - "Community 248"
Cohesion: 1.0
Nodes (1): Test handling of generation errors.

### Community 249 - "Community 249"
Cohesion: 1.0
Nodes (1): Test closing agent resources.

### Community 250 - "Community 250"
Cohesion: 1.0
Nodes (1): Create a mock retriever.

### Community 251 - "Community 251"
Cohesion: 1.0
Nodes (1): Test that simple flow works without LangGraph.

### Community 252 - "Community 252"
Cohesion: 1.0
Nodes (1): Create a mock retriever.

### Community 253 - "Community 253"
Cohesion: 1.0
Nodes (1): Create a mock LLM that returns relevant evaluation.

### Community 254 - "Community 254"
Cohesion: 1.0
Nodes (1): Create a mock LLM that returns poor relevance initially.

### Community 255 - "Community 255"
Cohesion: 1.0
Nodes (1): Create a mock prompt manager.

### Community 256 - "Community 256"
Cohesion: 1.0
Nodes (1): Test basic run with relevant retrieval.

### Community 257 - "Community 257"
Cohesion: 1.0
Nodes (1): Test run that requires query correction.

### Community 258 - "Community 258"
Cohesion: 1.0
Nodes (1): Test that run respects max_rewrites limit.

### Community 259 - "Community 259"
Cohesion: 1.0
Nodes (1): Test that run includes evaluation in metadata.

### Community 260 - "Community 260"
Cohesion: 1.0
Nodes (1): Test that run tracks execution steps.

### Community 261 - "Community 261"
Cohesion: 1.0
Nodes (1): Test evaluate_only method.

### Community 262 - "Community 262"
Cohesion: 1.0
Nodes (1): Test streaming response.

### Community 263 - "Community 263"
Cohesion: 1.0
Nodes (1): Create agent for testing parsing.

### Community 264 - "Community 264"
Cohesion: 1.0
Nodes (1): Create agent for testing.

### Community 265 - "Community 265"
Cohesion: 1.0
Nodes (1): Create agent with score-only evaluation.

### Community 266 - "Community 266"
Cohesion: 1.0
Nodes (1): Create mock retriever.

### Community 267 - "Community 267"
Cohesion: 1.0
Nodes (1): Test evaluation using only retrieval scores.

### Community 268 - "Community 268"
Cohesion: 1.0
Nodes (1): Create a mock MongoDB collection for evaluations.

### Community 269 - "Community 269"
Cohesion: 1.0
Nodes (1): Create a mock database.

### Community 270 - "Community 270"
Cohesion: 1.0
Nodes (1): Create a retriever with mock database.

### Community 271 - "Community 271"
Cohesion: 1.0
Nodes (1): Create a mock database.

### Community 272 - "Community 272"
Cohesion: 1.0
Nodes (1): Create a hybrid retriever.

### Community 273 - "Community 273"
Cohesion: 1.0
Nodes (1): Create a mock database.

### Community 274 - "Community 274"
Cohesion: 1.0
Nodes (1): Create a mock database.

### Community 275 - "Community 275"
Cohesion: 1.0
Nodes (1): Create a mock database.

### Community 276 - "Community 276"
Cohesion: 1.0
Nodes (1): Create a retriever with mock database.

### Community 277 - "Community 277"
Cohesion: 1.0
Nodes (1): Test that empty query returns empty list.

### Community 278 - "Community 278"
Cohesion: 1.0
Nodes (1): Test that whitespace-only query returns empty list.

### Community 279 - "Community 279"
Cohesion: 1.0
Nodes (1): Create mock database with sample data.

### Community 280 - "Community 280"
Cohesion: 1.0
Nodes (1): Create a mock database.

### Community 281 - "Community 281"
Cohesion: 1.0
Nodes (1): Create a mock database.

### Community 282 - "Community 282"
Cohesion: 1.0
Nodes (1): Test health check endpoint.

### Community 283 - "Community 283"
Cohesion: 1.0
Nodes (1): Test liveness check endpoint.

### Community 284 - "Community 284"
Cohesion: 1.0
Nodes (1): Test readiness check endpoint.

### Community 285 - "Community 285"
Cohesion: 1.0
Nodes (1): Test API v1 root endpoint.

### Community 286 - "Community 286"
Cohesion: 1.0
Nodes (1): Test listing LLM providers.

### Community 287 - "Community 287"
Cohesion: 1.0
Nodes (1): Test that Ollama is always available.

### Community 288 - "Community 288"
Cohesion: 1.0
Nodes (1): Test tracking is called when getting prompts.

### Community 289 - "Community 289"
Cohesion: 1.0
Nodes (1): Create a mock retriever.

### Community 290 - "Community 290"
Cohesion: 1.0
Nodes (1): Create a mock LLM that follows ReAct format.

### Community 291 - "Community 291"
Cohesion: 1.0
Nodes (1): Create a mock prompt manager.

### Community 292 - "Community 292"
Cohesion: 1.0
Nodes (1): Create a ReAct agent.

### Community 293 - "Community 293"
Cohesion: 1.0
Nodes (1): Test basic agent run.

### Community 294 - "Community 294"
Cohesion: 1.0
Nodes (1): Test that run tracks iterations.

### Community 295 - "Community 295"
Cohesion: 1.0
Nodes (1): Test that run includes thoughts in metadata.

### Community 296 - "Community 296"
Cohesion: 1.0
Nodes (1): Test that run includes actions in metadata.

### Community 297 - "Community 297"
Cohesion: 1.0
Nodes (1): Test run respects max iterations.

### Community 298 - "Community 298"
Cohesion: 1.0
Nodes (1): Test search tool execution.

### Community 299 - "Community 299"
Cohesion: 1.0
Nodes (1): Test calculate tool with invalid expression.

### Community 300 - "Community 300"
Cohesion: 1.0
Nodes (1): Test streaming response.

### Community 301 - "Community 301"
Cohesion: 1.0
Nodes (1): Create agent for testing parsing.

### Community 302 - "Community 302"
Cohesion: 1.0
Nodes (1): Create agent for testing helpers.

### Community 303 - "Community 303"
Cohesion: 1.0
Nodes (1): Create a mock database.

### Community 304 - "Community 304"
Cohesion: 1.0
Nodes (1): Create a retriever with mock database.

### Community 305 - "Community 305"
Cohesion: 1.0
Nodes (1): Test embedding empty query returns empty list.

### Community 306 - "Community 306"
Cohesion: 1.0
Nodes (1): Test embedding empty batch returns empty list.

### Community 307 - "Community 307"
Cohesion: 1.0
Nodes (1): Test retrieve_with_stats method.

### Community 308 - "Community 308"
Cohesion: 1.0
Nodes (1): Task: List user's RAG configurations.         Weight: 1 (lower priority than que

### Community 309 - "Community 309"
Cohesion: 1.0
Nodes (1): Task: Send RAG query to the system.         Weight: 3 (higher priority - main us

### Community 310 - "Community 310"
Cohesion: 1.0
Nodes (1): Task: Get details of a specific configuration.         Weight: 1

### Community 311 - "Community 311"
Cohesion: 1.0
Nodes (1): Simulate multiple concurrent login attempts.         Tests authentication servic

### Community 312 - "Community 312"
Cohesion: 1.0
Nodes (1): Test token refresh under load.         Validates refresh token rotation and vali

### Community 313 - "Community 313"
Cohesion: 1.0
Nodes (1): Test authentication with invalid credentials.         Validates proper error han

### Community 314 - "Community 314"
Cohesion: 1.0
Nodes (1): Test token validation with concurrent API calls.         Tests middleware perfor

### Community 315 - "Community 315"
Cohesion: 1.0
Nodes (1): Rapid login attempts to simulate traffic spike.

### Community 316 - "Community 316"
Cohesion: 1.0
Nodes (1): Simple RAG query - most common operation.         Weight: 35% (of 70% = 35% tota

### Community 317 - "Community 317"
Cohesion: 1.0
Nodes (1): Detailed RAG query with context.         Weight: 20% (of 70% = 20% total)

### Community 318 - "Community 318"
Cohesion: 1.0
Nodes (1): Streaming RAG query.         Weight: 15% (of 70% = 15% total)

### Community 319 - "Community 319"
Cohesion: 1.0
Nodes (1): List all configurations.         Weight: 12% (of 20% = 12% total)

### Community 320 - "Community 320"
Cohesion: 1.0
Nodes (1): View specific configuration details.         Weight: 8% (of 20% = 8% total)

### Community 321 - "Community 321"
Cohesion: 1.0
Nodes (1): Create a new configuration.         Weight: 5% (of 10% = 5% total)

### Community 322 - "Community 322"
Cohesion: 1.0
Nodes (1): Update an existing configuration.         Weight: 3% (of 10% = 3% total)

### Community 323 - "Community 323"
Cohesion: 1.0
Nodes (1): Delete a configuration.         Weight: 2% (of 10% = 2% total)

### Community 324 - "Community 324"
Cohesion: 1.0
Nodes (1): Rapid-fire queries for power users.

### Community 325 - "Community 325"
Cohesion: 1.0
Nodes (1): Periodically check configurations.

### Community 326 - "Community 326"
Cohesion: 1.0
Nodes (1): Test with short queries.         Weight: 40%                  Short queries test

### Community 327 - "Community 327"
Cohesion: 1.0
Nodes (1): Test with medium-length queries.         Weight: 45%                  Medium que

### Community 328 - "Community 328"
Cohesion: 1.0
Nodes (1): Test with complex, long queries.         Weight: 15%                  Long queri

### Community 329 - "Community 329"
Cohesion: 1.0
Nodes (1): Test streaming response mode.         Weight: 10%                  Streaming que

### Community 330 - "Community 330"
Cohesion: 1.0
Nodes (1): Send multiple concurrent queries.         Weight: 5%                  Tests syst

### Community 331 - "Community 331"
Cohesion: 1.0
Nodes (1): Rapid-fire queries for throughput testing.

## Knowledge Gaps
- **2079 isolated node(s):** `ServiceHealth`, `HealthResponse`, `circuitBreakerState`, `Claims`, `Return the v2 defaults missing from a legacy config document.` (+2074 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 107`** (2 nodes): `test_ingestion_and_rag.ps1`, `Print-Header()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 108`** (2 nodes): `useToast.ts`, `useToast()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 109`** (2 nodes): `recovery.go`, `Recovery()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 110`** (2 nodes): `__init__.py`, `Observability utilities (tracing, Langfuse, OpenTelemetry metrics).  All integra`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 111`** (1 nodes): `create_demo_user.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 112`** (1 nodes): `postcss.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 113`** (1 nodes): `tailwind.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 114`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 115`** (1 nodes): `env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 116`** (1 nodes): `init-db.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 117`** (1 nodes): `Return CORS origins as list.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 118`** (1 nodes): `Convert MongoDB document to serializable dict.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 119`** (1 nodes): `Backfill optional v2 fields for legacy config documents.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 120`** (1 nodes): `Create a folder service instance.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 121`** (1 nodes): `Create a temporary directory structure for testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 122`** (1 nodes): `Generate embeddings for a list of texts.          Args:             texts: Li`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 123`** (1 nodes): `Split text into chunks.          Args:             text: The text to split`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 124`** (1 nodes): `Split text at word boundaries when it exceeds max size.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 125`** (1 nodes): `Minimal k-means implementation without numpy dependency.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 126`** (1 nodes): `Parse CORS origins from comma-separated string or list.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 127`** (1 nodes): `Get Celery broker URL, falling back to Redis URL.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 128`** (1 nodes): `Get Celery result backend URL, falling back to Redis URL.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 129`** (1 nodes): `Check if running in development mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 130`** (1 nodes): `Create an assistant message.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 131`** (1 nodes): `Get embedding dimensions for the current model.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 132`** (1 nodes): `Get embedding dimensions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 133`** (1 nodes): `Get embedding dimensions for the current model.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 134`** (1 nodes): `Get embedding dimensions for the current model.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 135`** (1 nodes): `Check if leidenalg is available.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 136`** (1 nodes): `Parse LLM extraction output as JSON, with fallback handling.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 137`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 138`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 139`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 140`** (1 nodes): `Persist community summaries to MongoDB.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 141`** (1 nodes): `Process a document and extract text content.          Args:             file_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 142`** (1 nodes): `Normalize entity name for matching.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 143`** (1 nodes): `Calculate progress percentage.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 144`** (1 nodes): `Calculate job duration in seconds.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 145`** (1 nodes): `Calculate progress percentage.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 146`** (1 nodes): `Test starting ingestion without X-User-ID is rejected.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 147`** (1 nodes): `Test unsigned ingestion requests are rejected by service auth middleware.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 148`** (1 nodes): `Test starting ingestion for someone else's config is rejected.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 149`** (1 nodes): `Test starting ingestion with non-existent config.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 150`** (1 nodes): `Test duplicate starts return the existing ingestion job.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 151`** (1 nodes): `Test successfully starting ingestion.                  Note: This test uses th`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 152`** (1 nodes): `Test getting status when no ingestion exists.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 153`** (1 nodes): `Test getting status for pending ingestion.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 154`** (1 nodes): `Test getting status for running ingestion.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 155`** (1 nodes): `Test getting status for completed ingestion.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 156`** (1 nodes): `Test cancelling when no ingestion is running.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 157`** (1 nodes): `Test successfully cancelling a running ingestion.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 158`** (1 nodes): `Test retrying when no ingestion exists.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 159`** (1 nodes): `Test retrying ingestion that is not failed.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 160`** (1 nodes): `Test successfully retrying a failed ingestion.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 161`** (1 nodes): `Test getting logs when no ingestion exists.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 162`** (1 nodes): `Test getting logs with errors.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 163`** (1 nodes): `Test getting stats when no ingestion exists.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 164`** (1 nodes): `Test getting stats for an ingestion.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 165`** (1 nodes): `Test that history endpoint exists.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 166`** (1 nodes): `Test that status response has expected format.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 167`** (1 nodes): `Create recursive chunker instance with small min_chunk_size for testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 168`** (1 nodes): `Create sample text for testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 169`** (1 nodes): `Create semantic chunker instance with small min_chunk_size for testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 170`** (1 nodes): `Create text with multiple sentences.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 171`** (1 nodes): `Create document chunker instance.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 172`** (1 nodes): `Create paragraph chunker instance.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 173`** (1 nodes): `Create fixed size chunker instance.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 174`** (1 nodes): `Test embedding a single text with Ollama.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 175`** (1 nodes): `Test embedding multiple texts with Ollama.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 176`** (1 nodes): `Test embedding with specific model configuration.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 177`** (1 nodes): `Test extracting from empty text.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 178`** (1 nodes): `Test building from empty text.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 179`** (1 nodes): `Test fallback connected-components community detection.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 180`** (1 nodes): `Test detection with no entities.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 181`** (1 nodes): `Test that entities without relations become singleton communities.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 182`** (1 nodes): `Test entity extraction from chunks using mock LLM.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 183`** (1 nodes): `Test graceful handling of LLM errors.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 184`** (1 nodes): `Test community summarization with mock LLM.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 185`** (1 nodes): `Test that empty communities are skipped.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 186`** (1 nodes): `Test MongoDB persistence.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 187`** (1 nodes): `Test graceful LLM failure handling.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 188`** (1 nodes): `Create a test configuration in the database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 189`** (1 nodes): `Test storing and retrieving documents.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 190`** (1 nodes): `Test storing and retrieving chunks with embeddings.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 191`** (1 nodes): `Test deleting all data for a config.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 192`** (1 nodes): `Test that stats return correct counts.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 193`** (1 nodes): `Test text processor in full pipeline.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 194`** (1 nodes): `Test HuggingFace embedder can embed texts (requires model download).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 195`** (1 nodes): `Create graph store for testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 196`** (1 nodes): `Test storing and retrieving graph nodes.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 197`** (1 nodes): `Test storing and retrieving graph edges.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 198`** (1 nodes): `Test that re-ingestion clears old data.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 199`** (1 nodes): `Insert a test config into the database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 200`** (1 nodes): `Test starting ingestion and checking status.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 201`** (1 nodes): `Create text processor instance.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 202`** (1 nodes): `Create a temporary text file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 203`** (1 nodes): `Create a temporary markdown file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 204`** (1 nodes): `Test processing a text file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 205`** (1 nodes): `Test processing a markdown file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 206`** (1 nodes): `Test processing a non-existent file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 207`** (1 nodes): `Test file metadata extraction.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 208`** (1 nodes): `Get number of sources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 209`** (1 nodes): `Run the agent on a query.          Args:             query: User query`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 210`** (1 nodes): `Stream the agent response.          Args:             query: User query`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 211`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 212`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 213`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 214`** (1 nodes): `Create a configured Naive RAG agent.          Args:             db: Database`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 215`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 216`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 217`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 218`** (1 nodes): `Parse CORS origins from comma-separated string or list.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 219`** (1 nodes): `Check if running in development mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 220`** (1 nodes): `Check if MLflow tracking is enabled.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 221`** (1 nodes): `Evaluate a query/answer pair.          Args:             query: The user query.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 222`** (1 nodes): `Run post-response guardrail checks.          Args:             query: Original u`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 223`** (1 nodes): `Parse JSON from LLM response, handling markdown code fences.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 224`** (1 nodes): `Create a system message.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 225`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 226`** (1 nodes): `Generate a response from the LLM.          Args:             messages: List o`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 227`** (1 nodes): `Stream a response from the LLM.          Args:             messages: List of`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 228`** (1 nodes): `Create config from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 229`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 230`** (1 nodes): `Create from MongoDB document.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 231`** (1 nodes): `Retrieve relevant chunks for a query.          Args:             query: User`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 232`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 233`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 234`** (1 nodes): `Create from dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 235`** (1 nodes): `Create a mock retriever.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 236`** (1 nodes): `Create a mock prompt manager.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 237`** (1 nodes): `Create a naive RAG agent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 238`** (1 nodes): `Test basic agent run.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 239`** (1 nodes): `Test agent run with conversation history.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 240`** (1 nodes): `Test that run includes execution steps.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 241`** (1 nodes): `Test run without step tracking.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 242`** (1 nodes): `Test that run tracks total duration.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 243`** (1 nodes): `Test that run tracks token usage.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 244`** (1 nodes): `Test run with minimum score filtering.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 245`** (1 nodes): `Test run_with_sources convenience method.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 246`** (1 nodes): `Test streaming response.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 247`** (1 nodes): `Test handling of retrieval errors.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 248`** (1 nodes): `Test handling of generation errors.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 249`** (1 nodes): `Test closing agent resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 250`** (1 nodes): `Create a mock retriever.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 251`** (1 nodes): `Test that simple flow works without LangGraph.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 252`** (1 nodes): `Create a mock retriever.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 253`** (1 nodes): `Create a mock LLM that returns relevant evaluation.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 254`** (1 nodes): `Create a mock LLM that returns poor relevance initially.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 255`** (1 nodes): `Create a mock prompt manager.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 256`** (1 nodes): `Test basic run with relevant retrieval.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 257`** (1 nodes): `Test run that requires query correction.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 258`** (1 nodes): `Test that run respects max_rewrites limit.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 259`** (1 nodes): `Test that run includes evaluation in metadata.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 260`** (1 nodes): `Test that run tracks execution steps.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 261`** (1 nodes): `Test evaluate_only method.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 262`** (1 nodes): `Test streaming response.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 263`** (1 nodes): `Create agent for testing parsing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 264`** (1 nodes): `Create agent for testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 265`** (1 nodes): `Create agent with score-only evaluation.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 266`** (1 nodes): `Create mock retriever.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 267`** (1 nodes): `Test evaluation using only retrieval scores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 268`** (1 nodes): `Create a mock MongoDB collection for evaluations.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 269`** (1 nodes): `Create a mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 270`** (1 nodes): `Create a retriever with mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 271`** (1 nodes): `Create a mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 272`** (1 nodes): `Create a hybrid retriever.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 273`** (1 nodes): `Create a mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 274`** (1 nodes): `Create a mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 275`** (1 nodes): `Create a mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 276`** (1 nodes): `Create a retriever with mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 277`** (1 nodes): `Test that empty query returns empty list.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 278`** (1 nodes): `Test that whitespace-only query returns empty list.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 279`** (1 nodes): `Create mock database with sample data.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 280`** (1 nodes): `Create a mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 281`** (1 nodes): `Create a mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 282`** (1 nodes): `Test health check endpoint.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 283`** (1 nodes): `Test liveness check endpoint.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 284`** (1 nodes): `Test readiness check endpoint.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 285`** (1 nodes): `Test API v1 root endpoint.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 286`** (1 nodes): `Test listing LLM providers.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 287`** (1 nodes): `Test that Ollama is always available.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 288`** (1 nodes): `Test tracking is called when getting prompts.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 289`** (1 nodes): `Create a mock retriever.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 290`** (1 nodes): `Create a mock LLM that follows ReAct format.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 291`** (1 nodes): `Create a mock prompt manager.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 292`** (1 nodes): `Create a ReAct agent.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 293`** (1 nodes): `Test basic agent run.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 294`** (1 nodes): `Test that run tracks iterations.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 295`** (1 nodes): `Test that run includes thoughts in metadata.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 296`** (1 nodes): `Test that run includes actions in metadata.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 297`** (1 nodes): `Test run respects max iterations.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 298`** (1 nodes): `Test search tool execution.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 299`** (1 nodes): `Test calculate tool with invalid expression.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 300`** (1 nodes): `Test streaming response.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 301`** (1 nodes): `Create agent for testing parsing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 302`** (1 nodes): `Create agent for testing helpers.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 303`** (1 nodes): `Create a mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 304`** (1 nodes): `Create a retriever with mock database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 305`** (1 nodes): `Test embedding empty query returns empty list.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 306`** (1 nodes): `Test embedding empty batch returns empty list.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 307`** (1 nodes): `Test retrieve_with_stats method.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 308`** (1 nodes): `Task: List user's RAG configurations.         Weight: 1 (lower priority than que`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 309`** (1 nodes): `Task: Send RAG query to the system.         Weight: 3 (higher priority - main us`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 310`** (1 nodes): `Task: Get details of a specific configuration.         Weight: 1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 311`** (1 nodes): `Simulate multiple concurrent login attempts.         Tests authentication servic`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 312`** (1 nodes): `Test token refresh under load.         Validates refresh token rotation and vali`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 313`** (1 nodes): `Test authentication with invalid credentials.         Validates proper error han`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 314`** (1 nodes): `Test token validation with concurrent API calls.         Tests middleware perfor`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 315`** (1 nodes): `Rapid login attempts to simulate traffic spike.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 316`** (1 nodes): `Simple RAG query - most common operation.         Weight: 35% (of 70% = 35% tota`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 317`** (1 nodes): `Detailed RAG query with context.         Weight: 20% (of 70% = 20% total)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 318`** (1 nodes): `Streaming RAG query.         Weight: 15% (of 70% = 15% total)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 319`** (1 nodes): `List all configurations.         Weight: 12% (of 20% = 12% total)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 320`** (1 nodes): `View specific configuration details.         Weight: 8% (of 20% = 8% total)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 321`** (1 nodes): `Create a new configuration.         Weight: 5% (of 10% = 5% total)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 322`** (1 nodes): `Update an existing configuration.         Weight: 3% (of 10% = 3% total)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 323`** (1 nodes): `Delete a configuration.         Weight: 2% (of 10% = 2% total)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 324`** (1 nodes): `Rapid-fire queries for power users.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 325`** (1 nodes): `Periodically check configurations.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 326`** (1 nodes): `Test with short queries.         Weight: 40%                  Short queries test`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 327`** (1 nodes): `Test with medium-length queries.         Weight: 45%                  Medium que`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 328`** (1 nodes): `Test with complex, long queries.         Weight: 15%                  Long queri`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 329`** (1 nodes): `Test streaming response mode.         Weight: 10%                  Streaming que`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 330`** (1 nodes): `Send multiple concurrent queries.         Weight: 5%                  Tests syst`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 331`** (1 nodes): `Rapid-fire queries for throughput testing.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MockLLM` connect `Community 25` to `Community 5`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **What connects `ServiceHealth`, `HealthResponse`, `circuitBreakerState` to the rest of the system?**
  _2079 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.01 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.01 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.01 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.01 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.02 - nodes in this community are weakly interconnected._
# Configuration Guide

This guide explains all RAG pipeline configuration options in detail.

## Table of Contents

- [Overview](#overview)
- [Configuration Schema](#configuration-schema)
- [Data Source Configuration](#data-source-configuration)
- [RBAC Configuration](#rbac-configuration)
- [Model Configuration](#model-configuration)
- [Retrieval Configuration](#retrieval-configuration)
- [Agent Configuration](#agent-configuration)
- [Prompt Configuration](#prompt-configuration)
- [Example Configurations](#example-configurations)

## Overview

A RAG configuration defines:
1. **Where** your data comes from (data source)
2. **Who** can access it (RBAC)
3. **Which** AI models to use (models)
4. **How** to retrieve information (retrieval)
5. **What** logic to apply (agent)
6. **How** to prompt the AI (prompts)

## Configuration Schema

```yaml
name: "My RAG Pipeline"           # Required: Display name
description: "Optional description"
version: "1.0"                    # Config version

# Data source settings
data_source:
  type: "local" | "s3"
  ...

# Access control
rbac:
  enabled: true | false
  ...

# AI models
model_config:
  llm_provider: "openai" | "anthropic" | "ollama" | "vllm"
  ...

# Search strategy
retrieval_config:
  retrieval_method: "vector" | "keyword" | "graph" | "hybrid"
  ...

# Agent logic
agent_config:
  agent_template: "naive" | "react" | "self_rag" | "crag" | "multi_query" | "plan_solve"
  ...

# Prompts
prompt_config:
  system_prompt: "..."
  ...
```

## Data Source Configuration

### Local File System

For documents stored on local disk or mounted volumes.

```yaml
data_source:
  type: "local"
  path: "/data/documents"           # Required: Absolute path
  file_types:                       # Optional: Filter by type
    - "pdf"
    - "txt"
    - "docx"
    - "md"
    - "html"
  recursive: true                   # Optional: Scan subdirectories
  exclude_patterns:                 # Optional: Skip matching files
    - "*.tmp"
    - "*/drafts/*"
    - "*/node_modules/*"
```

**Path Resolution**:
- Docker: Use `/data/` prefix for mounted volumes
- Local dev: Use absolute paths
- Windows: Use forward slashes or escaped backslashes

**Example Docker Compose mount**:
```yaml
volumes:
  - ./my-documents:/data/documents:ro
```

### AWS S3

For documents stored in S3 buckets.

```yaml
data_source:
  type: "s3"
  bucket: "my-rag-documents"        # Required: S3 bucket name
  prefix: "documents/2024/"         # Optional: Path prefix
  region: "us-east-1"               # Required: AWS region
  access_key_id: "AKIA..."          # Required: AWS access key
  secret_access_key: "..."          # Required: AWS secret key
  file_types:                       # Optional: Filter by type
    - "pdf"
    - "txt"
  recursive: true                   # Optional: Scan sub-prefixes
```

**Security Notes**:
- Store credentials in environment variables or secrets
- Use IAM roles when running on AWS infrastructure
- Enable bucket versioning for document updates
- Use lifecycle policies to archive old versions

**IAM Policy Example**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-rag-documents",
        "arn:aws:s3:::my-rag-documents/*"
      ]
    }
  ]
}
```

### File Type Processing

| File Type | Processor | Capabilities |
|-----------|-----------|--------------|
| **PDF** | Docling + PyMuPDF | Text, images, tables, OCR |
| **TXT** | Text processor | Plain text |
| **DOCX** | python-docx | Text, formatting |
| **MD** | Markdown parser | Headers, links, code blocks |
| **HTML** | BeautifulSoup | Text extraction, link following |
| **Image** | Tesseract OCR | OCR text extraction |

## RBAC Configuration

Role-Based Access Control for multi-tenant deployments.

```yaml
rbac:
  enabled: true                     # Enable/disable RBAC
  
  default_role: "user"              # Default role for new users
  
  roles:                            # Define custom roles
    - name: "admin"
      description: "Full access"
      permissions:
        - "read"                   # Query the pipeline
        - "write"                  # Update configuration
        - "admin"                  # Manage users
        - "ingest"                 # Run ingestion
    
    - name: "user"
      description: "Standard user"
      permissions:
        - "read"
    
    - name: "analyst"
      description: "Can query and ingest"
      permissions:
        - "read"
        - "ingest"
  
  user_roles:                       # Assign roles to specific users
    - user_id: "user-uuid-1"
      role: "admin"
    - user_id: "user-uuid-2"
      role: "user"
```

### Permission Reference

| Permission | Description | Endpoints |
|------------|-------------|-----------|
| `read` | Query the pipeline | `POST /query`, `POST /chat` |
| `write` | Modify configuration | `PUT /configs/*` |
| `admin` | Full management | All endpoints |
| `ingest` | Run ingestion jobs | `POST /ingest` |

### Role Inheritance

Roles can inherit from other roles:

```yaml
roles:
  - name: "viewer"
    permissions: ["read"]
  
  - name: "editor"
    inherits: "viewer"
    permissions: ["write", "ingest"]
  
  - name: "super_admin"
    inherits: "editor"
    permissions: ["admin"]
```

## Model Configuration

Configure LLM and embedding model providers.

### LLM Providers

#### OpenAI

```yaml
model_config:
  llm_provider: "openai"
  llm_model: "gpt-4o"               # Options: gpt-4o, gpt-4-turbo, gpt-4, gpt-3.5-turbo
  llm_api_key: "sk-..."             # Required: API key
  llm_base_url: null                # Optional: Custom base URL
  llm_temperature: 0.7              # Optional: 0.0 - 2.0
  llm_max_tokens: 2000              # Optional: Max response tokens
  llm_timeout: 60                   # Optional: Request timeout (seconds)
```

**Model Recommendations**:
- `gpt-4o` - Best overall performance, multimodal
- `gpt-4-turbo` - Fast, good for most use cases
- `gpt-4` - Highest quality, slower
- `gpt-3.5-turbo` - Cost-effective, fast

#### Anthropic

```yaml
model_config:
  llm_provider: "anthropic"
  llm_model: "claude-3-opus-20240229"  # Options: opus, sonnet, haiku
  llm_api_key: "sk-ant-..."
  llm_temperature: 0.7
  llm_max_tokens: 2000
```

**Model Recommendations**:
- `claude-3-opus` - Best reasoning, largest context
- `claude-3-sonnet` - Balanced performance
- `claude-3-haiku` - Fastest, cost-effective

#### Ollama (Local)

```yaml
model_config:
  llm_provider: "ollama"
  llm_model: "llama3.2"             # Any Ollama model
  llm_base_url: "http://localhost:11434"  # Ollama server URL
  llm_temperature: 0.7
  llm_max_tokens: 2000
```

**Setup**:
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.2
ollama pull mistral
ollama pull codellama

# Start server
ollama serve
```

**Docker Compose integration**:
```yaml
services:
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
```

#### vLLM (Self-hosted)

```yaml
model_config:
  llm_provider: "vllm"
  llm_model: "meta-llama/Llama-2-7b-chat-hf"  # HuggingFace model ID
  llm_base_url: "http://localhost:8000"        # vLLM server URL
  llm_temperature: 0.7
  llm_max_tokens: 2000
```

**Setup**:
```bash
# Install vLLM
pip install vllm

# Start server
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --port 8000
```

### Embedding Providers

#### OpenAI Embeddings

```yaml
model_config:
  embedding_provider: "openai"
  embedding_model: "text-embedding-3-small"  # Options: small, large, ada-002
  embedding_api_key: "sk-..."
  embedding_dimensions: 1536          # small: 1536, large: 3072
```

**Model Comparison**:
| Model | Dimensions | Performance | Cost |
|-------|-----------|-------------|------|
| text-embedding-3-small | 1536 | Good | Lowest |
| text-embedding-3-large | 3072 | Best | Higher |
| text-embedding-ada-002 | 1536 | Legacy | Medium |

#### Ollama Embeddings

```yaml
model_config:
  embedding_provider: "ollama"
  embedding_model: "nomic-embed-text"
  embedding_base_url: "http://localhost:11434"
  embedding_dimensions: 768
```

**Available Models**:
- `nomic-embed-text` - 768 dims, excellent performance
- `mxbai-embed-large` - 1024 dims, multilingual
- `all-minilm` - 384 dims, fast

#### HuggingFace (Local)

```yaml
model_config:
  embedding_provider: "huggingface"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
  embedding_dimensions: 384
  embedding_device: "cpu"           # cpu, cuda, mps
  embedding_batch_size: 32
```

**Performance Tips**:
- Use GPU for faster embedding generation
- Increase batch size for large datasets
- Use smaller models for faster processing

## Retrieval Configuration

Configure how documents are retrieved and ranked.

### Retrieval Methods

#### Vector Search (Semantic)

Find documents based on semantic meaning.

```yaml
retrieval_config:
  retrieval_method: "vector"
  vector_search:
    metric: "cosine"                # cosine, euclidean, dot_product
    index_type: "hnsw"              # hnsw, ivf, flat
    ef_search: 100                  # HNSW search parameter
    m: 16                           # HNSW connections per node
  
  chunk_size: 1000                  # Characters per chunk
  chunk_overlap: 200                # Overlap between chunks
  top_k: 5                          # Number of chunks to retrieve
  
  rerank:                           # Optional: Reranking
    enabled: true
    model: "cohere-rerank-v2"
    top_n: 3                        # Final chunks after reranking
```

**Chunking Strategies**:

1. **Recursive** (default):
```yaml
chunking_strategy: "recursive"
chunk_size: 1000
chunk_overlap: 200
separator: "\n\n"                  # Primary separator
```

2. **Semantic**:
```yaml
chunking_strategy: "semantic"
max_chunk_size: 2000                # Max characters
semantic_threshold: 0.8             # Similarity threshold
```

3. **Document** (structure-aware):
```yaml
chunking_strategy: "document"
respect_headers: true               # Keep headers with content
respect_paragraphs: true            # Don't split paragraphs
```

#### Keyword Search (Lexical)

Traditional text search using BM25.

```yaml
retrieval_config:
  retrieval_method: "keyword"
  keyword_search:
    algorithm: "bm25"               # Currently only BM25
    k1: 1.5                         # Term frequency saturation
    b: 0.75                         # Document length normalization
  
  top_k: 5
  highlight_matches: true           # Highlight matching terms
```

#### Graph Search

Traverse entity relationships in knowledge graphs.

```yaml
retrieval_config:
  retrieval_method: "graph"
  graph_search:
    max_depth: 3                    # Relationship hops
    max_nodes: 100                  # Max nodes to explore
    relationship_types:             # Filter by relationship
      - "mentions"
      - "belongs_to"
      - "related_to"
    
  entity_extraction:
    enabled: true
    model: "gpt-4o-mini"            # LLM for entity extraction
    entity_types:                   # Entity types to extract
      - "Person"
      - "Organization"
      - "Product"
      - "Concept"
```

#### Hybrid Search (Recommended)

Combines vector, keyword, and optionally graph search.

```yaml
retrieval_config:
  retrieval_method: "hybrid"
  
  # Component weights (must sum to 1.0)
  weights:
    vector: 0.5
    keyword: 0.3
    graph: 0.2                      # Set to 0.0 to disable graph
  
  # Individual component config
  vector_search:
    metric: "cosine"
    top_k: 10
  
  keyword_search:
    top_k: 10
  
  graph_search:
    top_k: 10
    max_depth: 2
  
  # Fusion algorithm
  fusion:
    algorithm: "rrf"                # rrf (Reciprocal Rank Fusion)
    k: 60                           # RRF constant
    top_k: 5                        # Final results
  
  # Reranking
  rerank:
    enabled: true
    model: "cohere-rerank-v2"
    top_n: 5
```

**RRF Formula**:
```
score = Σ(1 / (k + rank))
```

Where k=60 provides good balance between rank position and score magnitude.

## Agent Configuration

Choose the AI reasoning pattern for your pipeline.

### Available Templates

#### 1. Naive RAG (Simplest)

Direct retrieval → generation. Best for simple Q&A.

```yaml
agent_config:
  agent_template: "naive"
  temperature: 0.7
  max_tokens: 2000
```

**Flow**:
```
Query → Retrieve → Generate → Answer
```

**When to use**:
- Simple fact lookup
- Well-structured documents
- Quick prototyping

**Limitations**:
- No reasoning
- No error correction
- No tool use

#### 2. ReAct (Reasoning + Action)

Think step-by-step and use tools. Best for complex tasks.

```yaml
agent_config:
  agent_template: "react"
  temperature: 0.7
  max_tokens: 2000
  max_iterations: 5                 # Max reasoning steps
  
  tools:                            # Available tools
    - name: "search"
      description: "Search documents"
    - name: "calculator"
      description: "Perform calculations"
    - name: "web_search"
      description: "Search the web"
```

**Flow**:
```
Query → Thought → Action → Observation → ... → Answer
```

**When to use**:
- Multi-step problems
- Need external tools
- Complex reasoning required

**Example**:
```
Query: "What was the revenue growth in Q2 and how does it 
         compare to the industry average?"

Thought: I need to find Q2 revenue, then find industry data
Action: search("Q2 revenue 2024")
Observation: Revenue was $50M, 20% growth

Thought: Now I need industry average
Action: web_search("industry average revenue growth Q2 2024")
Observation: Industry average is 15%

Thought: I can now compare
Action: calculator("(20 - 15) / 15 * 100")
Observation: 33.3% above average

Answer: Revenue grew 20% in Q2, which is 33.3% above...
```

#### 3. Self-RAG (Self-Reflective)

Evaluate and improve retrieved context. Best when accuracy is critical.

```yaml
agent_config:
  agent_template: "self_rag"
  temperature: 0.7
  max_tokens: 2000
  max_iterations: 3                 # Max refinement loops
  
  self_eval:
    enabled: true
    criteria:                       # Evaluation criteria
      - "relevance"
      - "completeness"
      - "accuracy"
    threshold: 0.8                  # Minimum score to accept
```

**Flow**:
```
Query → Retrieve → Evaluate → If poor → Re-retrieve → Generate
```

**When to use**:
- High-stakes answers
- Low-confidence data
- Need verified responses

**Self-Evaluation**:
```
Retrieved: "The company was founded in 1995"

Evaluation:
- Relevance: 0.9 (highly relevant)
- Completeness: 0.7 (missing location)
- Confidence: 0.8 (direct statement)

Decision: Re-retrieve for more context
```

#### 4. CRAG (Corrective RAG)

Detect low-confidence retrieval and correct. Best for noisy data.

```yaml
agent_config:
  agent_template: "crag"
  temperature: 0.7
  max_tokens: 2000
  
  correction:
    enabled: true
    confidence_threshold: 0.6       # Trigger correction below this
    
    fallback_actions:
      - "re_retrieve"              # Try different search
      - "web_search"               # Search web
      - "decompose"                # Break down query
      - "fallback_llm"             # Use LLM knowledge
```

**Flow**:
```
Query → Retrieve → Score Confidence → If low → Correct → Generate
```

**Confidence Scoring**:
```
High confidence (>0.8): Use retrieved context
Medium (0.6-0.8): Supplement with web search
Low (<0.6): Use fallback strategy
```

#### 5. Multi-Query (Decomposition)

Break complex queries into sub-queries. Best for research tasks.

```yaml
agent_config:
  agent_template: "multi_query"
  temperature: 0.7
  max_tokens: 2000
  
  decomposition:
    enabled: true
    max_sub_queries: 5              # Max parallel queries
    
  aggregation:
    strategy: "synthesis"           # synthesis, concatenation, vote
    synthesis_model: "gpt-4o"       # Model for combining answers
```

**Flow**:
```
Query → Decompose → Parallel Retrieve → Aggregate → Generate
```

**Example**:
```
Query: "Compare the performance of AWS, Azure, and GCP 
         for machine learning workloads"

Sub-queries:
1. "AWS machine learning performance benchmarks"
2. "Azure machine learning performance benchmarks"
3. "GCP machine learning performance benchmarks"
4. "AWS vs Azure ML comparison"
5. "ML workload pricing comparison cloud providers"

Aggregate: Synthesize findings into comprehensive comparison
```

#### 6. Plan-Solve (Hierarchical)

Create and execute a plan. Best for analytical tasks.

```yaml
agent_config:
  agent_template: "plan_solve"
  temperature: 0.7
  max_tokens: 2000
  max_plan_depth: 3                 # Hierarchical plan levels
  
  planning:
    strategy: "hierarchical"        # hierarchical, sequential
    allow_replanning: true          # Adjust plan if needed
  
  execution:
    parallel_subtasks: true         # Execute independent tasks
    max_concurrent: 4               # Max parallel executions
```

**Flow**:
```
Query → Create Plan → Execute Steps → Synthesize → Answer
```

**Example Plan**:
```
Query: "Analyze the company's financial health"

Plan:
1. Gather financial statements
   1.1. Income statement
   1.2. Balance sheet
   1.3. Cash flow statement

2. Calculate key metrics
   2.1. Profitability ratios
   2.2. Liquidity ratios
   2.3. Debt ratios

3. Compare to industry benchmarks

4. Generate analysis report
```

### Agent Comparison

| Template | Complexity | Speed | Accuracy | Best For |
|----------|-----------|-------|----------|----------|
| Naive RAG | Low | Fastest | Good | Simple Q&A |
| ReAct | High | Slow | High | Complex reasoning |
| Self-RAG | Medium | Medium | Very High | Verified answers |
| CRAG | Medium | Medium | High | Noisy data |
| Multi-Query | High | Slow | High | Research tasks |
| Plan-Solve | Very High | Slowest | Very High | Analysis tasks |

## Prompt Configuration

Customize how the AI is instructed and how context is formatted.

### System Prompt

Defines the AI's behavior and persona.

```yaml
prompt_config:
  system_prompt: |
    You are a helpful customer support assistant for TechCorp.
    
    Guidelines:
    - Be professional and friendly
    - Answer based only on provided context
    - If unsure, say so honestly
    - Cite sources when possible
    - Keep responses concise but complete
```

**Best Practices**:
- Be specific about the AI's role
- Include domain-specific instructions
- Define tone and style
- Set boundaries (what NOT to do)
- Add examples if helpful

### RAG Template

Controls how retrieved context is formatted.

```yaml
prompt_config:
  rag_template: |
    You have access to the following context to answer the question.
    
    Context:
    {context}
    
    ---
    
    Question: {query}
    
    Instructions:
    1. Answer using only the provided context
    2. If the answer isn't in the context, say "I don't have enough information"
    3. Cite the source document when possible
    
    Answer:
```

**Template Variables**:
- `{context}` - Retrieved documents (formatted)
- `{query}` - User's question
- `{chat_history}` - Previous messages (if available)

**Context Formatting**:
```yaml
prompt_config:
  context_format: |
    [Source: {source} | Page: {page} | Score: {score}]
    {content}
    
  ---
  
  source_format: "{filename}"
  include_metadata: true
  max_context_length: 4000        # Characters
```

### Advanced Prompting

#### Few-Shot Examples

```yaml
prompt_config:
  few_shot_examples:
    - query: "What are your business hours?"
      context: "We are open Monday-Friday 9AM-5PM EST"
      answer: "Our business hours are Monday through Friday, 9 AM to 5 PM EST."
    
    - query: "Do you offer refunds?"
      context: "Refund policy: 30-day money back guarantee"
      answer: "Yes, we offer a 30-day money-back guarantee."
```

#### Chain-of-Thought

```yaml
prompt_config:
  chain_of_thought: true
  cot_prompt: |
    Let's approach this step-by-step:
    1. First, identify the key information needed
    2. Then, find relevant context
    3. Analyze the information
    4. Formulate the answer
    
    Show your reasoning process.
```

## Example Configurations

### Simple Customer Support Bot

```yaml
name: "Customer Support Bot"
description: "Simple bot for FAQs and support"

data_source:
  type: "local"
  path: "/data/support-docs"
  file_types: ["pdf", "txt", "docx"]
  recursive: true

rbac:
  enabled: false

model_config:
  llm_provider: "openai"
  llm_model: "gpt-3.5-turbo"
  llm_api_key: "${OPENAI_API_KEY}"
  llm_temperature: 0.7
  
  embedding_provider: "openai"
  embedding_model: "text-embedding-3-small"
  embedding_api_key: "${OPENAI_API_KEY}"

retrieval_config:
  retrieval_method: "hybrid"
  weights:
    vector: 0.7
    keyword: 0.3
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5

agent_config:
  agent_template: "naive"
  temperature: 0.7
  max_tokens: 1000

prompt_config:
  system_prompt: |
    You are a helpful customer support assistant.
    Answer questions based on the support documentation.
    Be concise and friendly.
  
  rag_template: |
    Context:
    {context}
    
    Question: {query}
    
    Answer helpfully based on the context:
```

### Advanced Technical Documentation

```yaml
name: "Tech Docs Assistant"
description: "Advanced RAG for technical documentation with verification"

data_source:
  type: "s3"
  bucket: "company-tech-docs"
  prefix: "docs/"
  region: "us-east-1"
  file_types: ["md", "html", "pdf"]

rbac:
  enabled: true
  default_role: "developer"
  roles:
    - name: "developer"
      permissions: ["read", "ingest"]
    - name: "tech_lead"
      permissions: ["read", "write", "ingest", "admin"]

model_config:
  llm_provider: "anthropic"
  llm_model: "claude-3-sonnet-20240229"
  llm_api_key: "${ANTHROPIC_API_KEY}"
  llm_temperature: 0.5
  llm_max_tokens: 4000
  
  embedding_provider: "openai"
  embedding_model: "text-embedding-3-large"
  embedding_api_key: "${OPENAI_API_KEY}"

retrieval_config:
  retrieval_method: "hybrid"
  weights:
    vector: 0.5
    keyword: 0.3
    graph: 0.2
  
  chunk_size: 2000
  chunk_overlap: 400
  chunking_strategy: "semantic"
  
  vector_search:
    metric: "cosine"
    top_k: 10
  
  fusion:
    algorithm: "rrf"
    k: 60
    top_k: 8
  
  rerank:
    enabled: true
    model: "cohere-rerank-v2"
    top_n: 5

agent_config:
  agent_template: "self_rag"
  temperature: 0.5
  max_tokens: 4000
  max_iterations: 3
  
  self_eval:
    enabled: true
    criteria: ["relevance", "completeness", "accuracy"]
    threshold: 0.85

prompt_config:
  system_prompt: |
    You are a technical documentation expert.
    Provide accurate, detailed answers with code examples.
    Always cite your sources and include version information.
    If multiple approaches exist, present the recommended one first.
  
  rag_template: |
    Technical Context:
    {context}
    
    User Query: {query}
    
    Provide a comprehensive technical answer:
    - Include relevant code snippets
    - Mention API versions
    - Cite specific documentation sections
    - Note any prerequisites or limitations
```

### Local Development Setup

```yaml
name: "Local Dev Pipeline"
description: "Development configuration using local models"

data_source:
  type: "local"
  path: "/data/test-docs"
  file_types: ["txt", "md"]

rbac:
  enabled: false

model_config:
  llm_provider: "ollama"
  llm_model: "llama3.2"
  llm_base_url: "http://localhost:11434"
  llm_temperature: 0.7
  
  embedding_provider: "ollama"
  embedding_model: "nomic-embed-text"
  embedding_base_url: "http://localhost:11434"

retrieval_config:
  retrieval_method: "vector"
  chunk_size: 500
  chunk_overlap: 100
  top_k: 3

agent_config:
  agent_template: "naive"
  temperature: 0.7
  max_tokens: 1000

prompt_config:
  system_prompt: "You are a helpful assistant."
  rag_template: |
    Context: {context}
    Question: {query}
    Answer:
```

---

For API usage, see [API.md](API.md)
For deployment, see [DEPLOYMENT.md](DEPLOYMENT.md)
For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

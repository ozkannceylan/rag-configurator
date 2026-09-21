# RAG Configurator

A low-code platform for building, configuring, and deploying production-ready RAG (Retrieval-Augmented Generation) pipelines. Create sophisticated AI applications without writing code.

## Key Features

### 6 Pre-built Agent Templates

Choose from six battle-tested RAG architectures, each optimized for different use cases:

| Template | Best For | Key Capabilities |
|----------|----------|------------------|
| **Naive RAG** | Simple Q&A, quick prototypes | Direct retrieval → generation |
| **ReAct** | Multi-step reasoning, tool use | Reasoning + action loops with external tools |
| **Self-RAG** | High-precision requirements | Self-evaluation and correction of retrieved context |
| **CRAG** | Low-confidence data scenarios | Corrective retrieval with fallback mechanisms |
| **Multi-Query** | Complex multi-faceted questions | Query decomposition and parallel retrieval |
| **Plan-Solve** | Research and analysis tasks | Hierarchical planning with step-by-step execution |

### Multi-LLM Support

Connect to any major LLM provider with a unified interface:

- **OpenAI** (GPT-4, GPT-4 Turbo, GPT-3.5)
- **Anthropic** (Claude 3 Opus, Sonnet, Haiku)
- **Local Models** via Ollama (Llama, Mistral, CodeLlama)
- **Self-hosted** via vLLM (any HuggingFace model)

### Hybrid Retrieval

Combine multiple retrieval strategies for maximum accuracy:

- **Vector Search** - Semantic similarity using embeddings
- **Keyword Search** - BM25/TF-IDF for exact matches
- **Graph Traversal** - Entity relationship navigation
- **Hybrid Fusion** - Reciprocal Rank Fusion (RRF) combining all methods

### Production-Ready Features

- **RBAC System** - Role-based access control for multi-tenant deployments
- **Prompt Management** - Versioned prompts with MLflow integration
- **Streaming Responses** - Real-time token streaming for chat interfaces
- **Multi-format Ingestion** - PDF, DOCX, TXT, images with OCR
- **Chunking Strategies** - Recursive, semantic, and document-aware chunking
- **Observability** - Comprehensive logging and metrics

## Quick Start

Get up and running in 5 minutes:

```bash
git clone https://github.com/your-org/rag-configurator.git
cd rag-configurator
docker-compose up
```

Then open:
- **Configurator UI**: http://localhost:5173
- **Sandbox Chat**: http://localhost:3001

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Screenshots

> Screenshots will be added here

### Configurator Wizard
*Visual pipeline configuration with step-by-step setup*

### Sandbox Chat Interface
*Test your RAG pipeline with a ChatGPT-like interface*

### Architecture Overview
*System architecture diagram*

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | Vue 3 + TypeScript | 3.4.x |
| **UI Components** | Naive UI | 2.38.x |
| **State Management** | Pinia | 2.1.x |
| **API Gateway** | Go + Gin | 1.22.x / 1.9.x |
| **Python Services** | FastAPI | 0.111.x |
| **Agent Framework** | LangGraph | 0.2.x |
| **Task Queue** | Celery + Redis | 5.4.x / 7.x |
| **Database** | MongoDB | 7.x |
| **Auth** | JWT (python-jose + passlib) | - |
| **PDF Processing** | Docling + PyMuPDF | latest |
| **Embeddings** | OpenAI / Ollama / HuggingFace | - |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  Configurator UI (Port 5173)        Sandbox UI (Port 3001)     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Go Gateway (Port 8000)                       │
├─────────────────────────────────────────────────────────────────┤
│  CORS → Logging → Rate Limit → Auth → Routing → Proxy           │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│Config Service │     │Ingestion Svc  │     │   RAG Service │
│  (Port 8001)  │     │  (Port 8002)  │     │   (Port 8003) │
├───────────────┤     ├───────────────┤     ├───────────────┤
│ • Auth        │     │ • File Upload │     │ • Query       │
│ • User Mgmt   │     │ • Processors  │     │ • Chat        │
│ • Config CRUD │     │ • Chunkers    │     │ • Streaming   │
│ • YAML Export │     │ • Embedders   │     │ • Agents      │
└───────────────┘     └───────────────┘     └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data & Queue Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  MongoDB (Documents/Vectors)        Redis (Celery Broker)      │
└─────────────────────────────────────────────────────────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## Documentation

- [Quick Start Guide](QUICKSTART.md) - Get running in minutes
- [Architecture](ARCHITECTURE.md) - System design and data flow
- [API Reference](API.md) - Complete endpoint documentation
- [Configuration](CONFIGURATION.md) - RAG pipeline configuration options
- [Deployment](DEPLOYMENT.md) - Production deployment guides
- [Development](DEVELOPMENT.md) - Contributing and local development
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Jev vs LLM-as-judge](jev-eval.md) - Frozen-trace compare harness

## License

MIT License - see [LICENSE](../LICENSE) file for details.

## Contributing

We welcome contributions! Please see [DEVELOPMENT.md](DEVELOPMENT.md) for guidelines.

## Support

- GitHub Issues: [Report bugs or request features](https://github.com/your-org/rag-configurator/issues)
- Discussions: [Community forum](https://github.com/your-org/rag-configurator/discussions)

---

Built with ❤️ for the AI engineering community

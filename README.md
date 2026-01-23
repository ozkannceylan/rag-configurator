# RAG Configurator

**A low-code platform for building and deploying custom RAG pipelines through a visual interface.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Vue](https://img.shields.io/badge/Vue-3.4+-42b883.svg)](https://vuejs.org)
[![Go](https://img.shields.io/badge/Go-1.22+-00ADD8.svg)](https://golang.org)

---

## What is RAG Configurator?

RAG Configurator eliminates the boilerplate of building Retrieval-Augmented Generation systems. Instead of writing code for each implementation, you configure your entire pipeline through a step-by-step wizard:

```
Define Data → Set Permissions → Choose Models → Configure Retrieval → Select Agent → Deploy API
```

**In 5 minutes, go from raw documents to a production-ready RAG API.**

---

## Features

- **🗂️ Multi-Source Data Ingestion** — Local files, S3, GCS, Azure Blob
- **🔐 Role-Based Access Control** — Folder-level permissions per user role
- **🔍 Flexible Retrieval** — Vector, keyword, graph, or hybrid search
- **🤖 Configurable Agents** — Naive RAG, ReAct, CRAG, Self-RAG, and more
- **📝 Prompt Management** — Version-controlled prompts with MLflow
- **🖼️ Multimodal Support** — Images, PDFs with Docling, vision LLMs
- **⚡ One-Click Deploy** — Generate REST API instantly

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐
│  Vue 3 UI    │────▶│  Go Gateway  │────▶│  Python Services (FastAPI)  │
│  Configurator│     │  Auth/Routing│     │  Config | Ingestion | RAG   │
└──────────────┘     └──────────────┘     └──────────────┬───────────────┘
                                                         │
                                          ┌──────────────▼───────────────┐
                                          │  MongoDB Atlas               │
                                          │  Vectors + Graphs + Configs  │
                                          └──────────────────────────────┘
```

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/ozkannceylan/rag-configurator.git
cd rag-configurator

# Start with Docker Compose
cp .env.example .env
docker-compose up -d

# Open the configurator
open http://localhost:3000
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vue 3, TypeScript, Naive UI, Pinia |
| Gateway | Go, Gin |
| Services | Python, FastAPI, LangGraph, Celery |
| Database | MongoDB Atlas (Vector + Graph + Search) |
| Queue | Redis |

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Configuration Schema](docs/CONFIGURATION_SCHEMA.md)
- [API Reference](docs/API_REFERENCE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Contributing](CONTRIBUTING.md)

---

## Roadmap

- [x] Core configuration wizard
- [x] Vector + keyword + graph retrieval
- [x] Predefined agent templates
- [ ] Visual agent builder (drag-and-drop)
- [ ] Multi-tenant support
- [ ] Kubernetes Helm charts
- [ ] Evaluation dashboard

---

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) before submitting a PR.

---

## License

Apache 2.0 — See [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Built for the community by developers who were tired of writing the same RAG boilerplate.</b>
</p>
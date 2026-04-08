# Quick Start Guide

Get RAG Configurator running locally in under 5 minutes.

## Prerequisites

### Required Software

| Software | Version | Installation |
|----------|---------|--------------|
| Docker | 20.10+ | [Get Docker](https://docs.docker.com/get-docker/) |
| Docker Compose | 2.20+ | Included with Docker Desktop |
| Git | 2.30+ | [Get Git](https://git-scm.com/downloads) |

### System Requirements

- **RAM**: 8GB minimum, 16GB recommended (for local LLMs)
- **Disk**: 10GB free space
- **CPU**: 4 cores recommended
- **OS**: Linux, macOS, or Windows with WSL2

### Optional: API Keys

For cloud LLM features, obtain API keys:

- [OpenAI](https://platform.openai.com/api-keys)
- [Anthropic](https://console.anthropic.com/settings/keys)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/rag-configurator.git
cd rag-configurator
```

### 2. Environment Setup

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys (optional for basic local setup):

```bash
# Optional: For cloud LLM support
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- MongoDB (database)
- Redis (queue)
- Config Service (API)
- Ingestion Service (file processing)
- RAG Service (query/retrieval)
- Gateway (API gateway)
- Configurator UI
- Sandbox UI

### 4. Verify Startup

Check all services are healthy:

```bash
docker-compose ps
```

Or test the health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "gateway": "up",
    "config_service": "up",
    "ingestion_service": "up",
    "rag_service": "up"
  }
}
```

## Accessing the UIs

Once services are running, open your browser:

### Configurator UI

**URL**: http://localhost:5173

The visual wizard for creating RAG pipeline configurations:

1. Create data source connections
2. Configure RBAC and access control
3. Select LLM providers and models
4. Set up retrieval strategies
5. Choose agent templates
6. Define prompts

### Sandbox Chat Interface

**URL**: http://localhost:3001

Test your RAG pipelines with a ChatGPT-like interface:

- Test queries against your configured pipeline
- View retrieved context and sources
- Stream responses in real-time
- Export conversation history

## Creating Your First RAG Configuration

### Step 1: Register an Account

1. Open http://localhost:5173
2. Click "Register"
3. Enter email, password, and name
4. You'll be automatically logged in

### Step 2: Start the Configuration Wizard

1. Click "New Configuration"
2. Name your pipeline (e.g., "My First RAG")

### Step 3: Configure Data Source

**For local files:**
1. Select "Local File System"
2. Enter folder path (e.g., `/data/documents`)
3. Select file types: PDF, TXT, DOCX

**For S3:**
1. Select "AWS S3"
2. Enter bucket name and credentials
3. Specify file prefix/pattern

### Step 4: Set RBAC (Optional)

Skip this step for personal use, or configure:
- Admin role: Full access
- User role: Query-only access

### Step 5: Configure Models

**For local testing (Ollama):**
1. Select "Ollama" provider
2. Base URL: `http://host.docker.internal:11434`
3. LLM Model: `llama3.2`
4. Embedding Model: `nomic-embed-text`

**For OpenAI:**
1. Select "OpenAI" provider
2. Enter your API key
3. LLM Model: `gpt-4o`
4. Embedding Model: `text-embedding-3-small`

### Step 6: Configure Retrieval

1. **Retrieval Method**: Select "Hybrid" for best results
2. **Chunk Size**: 1000 (default)
3. **Chunk Overlap**: 200 (default)
4. **Top K Results**: 5

### Step 7: Select Agent Template

Choose based on your use case:

- **Naive RAG**: Simple Q&A (fastest)
- **Self-RAG**: When accuracy is critical
- **Multi-Query**: For complex research questions

### Step 8: Configure Prompts

1. **System Prompt**: Define assistant behavior
   ```
   You are a helpful assistant specialized in technical documentation.
   Answer questions based only on the provided context.
   ```

2. **RAG Template**: Format for context injection
   ```
   Context:
   {context}

   Question: {query}

   Answer:
   ```

### Step 9: Save Configuration

Click "Save" to store your configuration. Note the configuration ID for later use.

## Running Ingestion

Once your configuration is saved:

### Method 1: Via UI

1. Go to "Ingestion" tab
2. Select your configuration
3. Upload files or select folder
4. Click "Start Ingestion"
5. Monitor progress in real-time

### Method 2: Via API

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": "your-config-id",
    "source_path": "/path/to/documents"
  }'
```

Check ingestion status:

```bash
curl http://localhost:8000/api/v1/ingest/<task-id>/status \
  -H "Authorization: Bearer <your-jwt-token>"
```

## Testing Queries

### Via Sandbox UI

1. Open http://localhost:3001
2. Select your configuration from dropdown
3. Type a question in the chat input
4. View the response with source citations

Example queries:
```
What are the main features of this product?
Explain the architecture diagram.
Summarize the installation steps.
```

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": "your-config-id",
    "query": "What is RAG?"
  }'
```

### Streaming Response

```bash
curl -X POST http://localhost:8000/api/v1/stream \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": "your-config-id",
    "query": "Explain the architecture"
  }'
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs <service-name>

# Restart specific service
docker-compose restart <service-name>

# Full reset (WARNING: clears data)
docker-compose down -v
docker-compose up -d
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | Check `lsof -i :8000` and stop conflicting service |
| MongoDB connection failed | Wait 30 seconds for MongoDB to initialize |
| Permission denied | Run `chmod +x scripts/*.sh` |
| UI not loading | Clear browser cache or try incognito mode |

### Getting JWT Token

```bash
# Login and get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "your-password"
  }'
```

### Checking Service Health

```bash
# Gateway
curl http://localhost:8000/health

# Individual services
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand system design
- Explore [CONFIGURATION.md](CONFIGURATION.md) for advanced options
- Check [API.md](API.md) for programmatic access
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed debugging

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears data)
docker-compose down -v
```

---

**Need help?** Open an issue on GitHub or check our [Troubleshooting Guide](TROUBLESHOOTING.md)

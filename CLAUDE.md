# CLAUDE.md - Project Context for Claude Code

## Project Overview

RAG Configurator is a low-code platform for building and deploying custom RAG pipelines. This document provides context for AI-assisted development.

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | Vue 3 + TypeScript | 3.4.x |
| UI Components | Naive UI | 2.38.x |
| State Management | Pinia | 2.1.x |
| API Gateway | Go + Gin | 1.22.x / 1.9.x |
| Python Services | FastAPI | 0.111.x |
| Agent Framework | LangGraph | 0.2.x |
| Task Queue | Celery + Redis | 5.4.x / 7.x |
| Database | MongoDB | 7.x |
| Auth | JWT (python-jose + passlib) | - |

## Project Structure

```
rag-configurator/
├── gateway/                 # Go API Gateway (Gin)
├── services/
│   ├── config-service/      # FastAPI - Config CRUD, Auth, User management
│   ├── ingestion-service/   # FastAPI + Celery - Data processing
│   └── rag-service/         # FastAPI + LangGraph - RAG runtime
├── ui/
│   ├── configurator/        # Vue 3 - Config wizard
│   └── sandbox/             # Vue 3 - Test chat UI
├── shared/
│   ├── python/              # Shared Pydantic models (rag-config-common)
│   ├── typescript/          # Shared TypeScript types
│   └── schemas/             # JSON schemas (source of truth)
└── infrastructure/          # Docker, MongoDB init scripts
```

## Coding Standards

### Python (FastAPI Services)

- **Python version**: 3.11+
- **Package manager**: pip with requirements.txt
- **Formatting**: Black (line-length=88)
- **Linting**: Ruff
- **Type hints**: Required for all functions
- **Docstrings**: Google style
- **Testing**: pytest with pytest-asyncio for async tests

**File organization pattern:**
```
service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependency injection
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py    # Main router aggregating all routes
│   │       └── {resource}.py # Resource endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── settings.py      # Pydantic Settings
│   │   ├── security.py      # Auth utilities
│   │   └── exceptions.py    # Custom exceptions
│   ├── models/              # MongoDB document models (if service-specific)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic
│   └── db/
│       ├── __init__.py
│       ├── mongodb.py       # MongoDB connection
│       └── repositories/    # Data access layer
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   └── test_{module}.py
├── requirements.txt
├── Dockerfile
└── pyproject.toml
```

**Import order:**
1. Standard library
2. Third-party packages
3. Local imports (absolute)

**Example FastAPI endpoint:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_user, get_db
from app.schemas.config import ConfigCreate, ConfigResponse
from app.services.config_service import ConfigService

router = APIRouter(prefix="/configs", tags=["configs"])

@router.post("/", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    config_in: ConfigCreate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
) -> ConfigResponse:
    """Create a new RAG pipeline configuration."""
    service = ConfigService(db)
    return await service.create(config_in, current_user.id)
```

### Go (Gateway)

- **Go version**: 1.22+
- **Framework**: Gin
- **Project layout**: Standard Go project layout
- **Error handling**: Always check and handle errors explicitly
- **Logging**: Use structured logging (zerolog or slog)

### TypeScript/Vue

- **Node version**: 20 LTS
- **Package manager**: npm
- **Vue**: Composition API with `<script setup>`
- **State**: Pinia stores
- **Styling**: Tailwind CSS + Naive UI components

## Database Patterns

### MongoDB Connection (Python)
```python
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.settings import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    
    async def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URI)
        
    async def disconnect(self):
        self.client.close()
        
    def get_database(self):
        return self.client[settings.MONGODB_DATABASE]

mongodb = MongoDB()
```

### Repository Pattern
```python
from typing import Optional, List
from bson import ObjectId

class BaseRepository:
    def __init__(self, db, collection_name: str):
        self.collection = db[collection_name]
    
    async def find_by_id(self, id: str) -> Optional[dict]:
        return await self.collection.find_one({"_id": ObjectId(id)})
    
    async def find_many(self, filter: dict, skip: int = 0, limit: int = 100) -> List[dict]:
        cursor = self.collection.find(filter).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def insert_one(self, document: dict) -> str:
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)
    
    async def update_one(self, id: str, update: dict) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update}
        )
        return result.modified_count > 0
    
    async def delete_one(self, id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
```

## Authentication Pattern

### JWT Token Flow
1. User registers/logs in via `/api/v1/auth/login`
2. Server returns `access_token` (30min) and `refresh_token` (7 days)
3. Client sends `Authorization: Bearer {access_token}` header
4. Server validates token via `get_current_user` dependency

### Security Implementation
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: str, expires_delta: timedelta = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode = {"exp": expire, "sub": subject, "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

## Shared Models

**IMPORTANT**: Always import configuration models from the shared package:
```python
from rag_config_common.models import (
    RAGPipelineConfig,
    DataSourceConfig,
    ModelConfig,
    RetrievalConfig,
    AgentConfig,
    PromptConfig,
)
from rag_config_common.models.enums import (
    IngestionStatus,
    DataSourceType,
    LLMProvider,
)
```

## API Response Format

All API responses follow this structure:
```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[APIError] = None
    meta: Optional[ResponseMeta] = None

class APIError(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None

class ResponseMeta(BaseModel):
    request_id: str
    timestamp: str
    version: str = "1.0.0"
```

## Environment Variables

Services read from these environment variables:
- `MONGODB_URI` - MongoDB connection string
- `MONGODB_DATABASE` - Database name (default: `rag_configurator`)
- `REDIS_URL` - Redis connection string
- `JWT_SECRET_KEY` - Secret for JWT signing
- `JWT_ALGORITHM` - JWT algorithm (default: `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Access token lifetime (default: 30)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token lifetime (default: 7)

## Testing Patterns

```python
# conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def test_user():
    return {"email": "test@example.com", "password": "testpassword", "name": "Test User"}
```

```python
# test_auth.py
import pytest

@pytest.mark.asyncio
async def test_register(client, test_user):
    response = await client.post("/api/v1/auth/register", json=test_user)
    assert response.status_code == 201
    assert "access_token" in response.json()["data"]
```

## Common Commands

```bash
# Start development environment
make dev

# Run tests
make test-python

# Lint code
make lint-python

# Install shared package (from repo root)
pip install -e shared/python
```

## Current Phase: Phase 1 - Config Service

We are building the Config Service which handles:
- User authentication (register, login, refresh, logout)
- User management (CRUD)
- Configuration management (CRUD)
- Folder scanning
- YAML export/import

The service runs on port 8001 and all endpoints are prefixed with `/api/v1/`.


# CLAUDE.md Addendum - Phase 2: Go Gateway

Add this section to your existing CLAUDE.md file in the repository root.

---

## Phase 2: Go Gateway

### Project Status
- ✅ Phase 1 complete: Config Service running on port 8001
- ✅ 46 tests passing
- ✅ Go 1.22 installed
- ✅ Dependencies ready: gin, jwt, zerolog
- ✅ `.env` synchronized with Phase 1 JWT settings

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Go Gateway (Port 8000)                       │
├─────────────────────────────────────────────────────────────────┤
│  Request Flow:                                                  │
│  Client → CORS → Logging → Recovery → [Auth] → Proxy → Service │
├─────────────────────────────────────────────────────────────────┤
│  Route Mapping:                                                 │
│  /health              → Gateway (direct)      [NO AUTH]         │
│  /api/v1/auth/*       → Config Service:8001   [NO AUTH]         │
│  /api/v1/users/*      → Config Service:8001   [REQUIRES AUTH]   │
│  /api/v1/configs/*    → Config Service:8001   [REQUIRES AUTH]   │
│  /api/v1/folders/*    → Config Service:8001   [REQUIRES AUTH]   │
│  /api/v1/ingest/*     → Ingestion Svc:8002    [REQUIRES AUTH]   │
│  /api/v1/query/*      → RAG Service:8003      [REQUIRES AUTH]   │
│  /api/v1/chat/*       → RAG Service:8003      [REQUIRES AUTH]   │
│  /api/v1/stream/*     → RAG Service:8003      [REQUIRES AUTH]   │
└─────────────────────────────────────────────────────────────────┘
```

### Go Project Structure

```
gateway/
├── cmd/server/
│   └── main.go              # Entry point, server lifecycle
├── internal/
│   ├── config/
│   │   └── config.go        # Environment configuration
│   ├── middleware/
│   │   ├── auth.go          # JWT validation middleware
│   │   ├── cors.go          # CORS handling
│   │   ├── ratelimit.go     # Rate limiting per IP
│   │   ├── logging.go       # Request/response logging
│   │   └── recovery.go      # Panic recovery
│   ├── handlers/
│   │   ├── health.go        # Health check endpoints
│   │   └── websocket.go     # WebSocket proxy for streaming
│   ├── router/
│   │   └── router.go        # Route definitions and grouping
│   └── proxy/
│       └── proxy.go         # Reverse proxy to backend services
├── pkg/
│   ├── jwt/
│   │   └── jwt.go           # JWT parsing and validation
│   └── response/
│       └── response.go      # Standardized API responses
├── go.mod
├── go.sum
└── Dockerfile
```

### Go Coding Standards

**Imports Order:**
1. Standard library
2. Third-party packages
3. Internal packages

**Error Handling:**
```go
// Always wrap errors with context
if err != nil {
    return fmt.Errorf("failed to do X: %w", err)
}
```

**Logging with zerolog:**
```go
log.Info().
    Str("method", c.Request.Method).
    Str("path", c.Request.URL.Path).
    Int("status", status).
    Dur("latency", latency).
    Msg("request completed")
```

**Gin Middleware Pattern:**
```go
func MyMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        // Before request
        c.Next()
        // After request
    }
}
```

### JWT Compatibility with Phase 1

**Critical:** The gateway must validate JWTs exactly as Phase 1 creates them.

Phase 1 JWT Structure:
```json
{
  "sub": "user_id_here",
  "type": "access",
  "exp": 1234567890,
  "iat": 1234567800
}
```

Validation Rules:
- Algorithm: HS256 (from `JWT_ALGORITHM` env var)
- Secret: from `JWT_SECRET_KEY` env var
- Must check `type` == "access" (reject refresh tokens)
- Must check `exp` > current time

### Environment Variables

```bash
# Gateway
GATEWAY_PORT=8000
ENVIRONMENT=development
LOG_LEVEL=info

# JWT (must match Phase 1)
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# Backend Services
CONFIG_SERVICE_URL=http://localhost:8001
INGESTION_SERVICE_URL=http://localhost:8002
RAG_SERVICE_URL=http://localhost:8003

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Rate Limiting
RATE_LIMIT_RPS=100
RATE_LIMIT_BURST=200
```

### Dependencies (go.mod)

```
github.com/gin-gonic/gin v1.10.0
github.com/golang-jwt/jwt/v5 v5.2.1
github.com/rs/zerolog v1.33.0
github.com/joho/godotenv v1.5.1
github.com/caarlos0/env/v10 v10.0.0
golang.org/x/time v0.5.0  // For rate limiting
```

### Testing Pattern

```go
func TestMiddleware(t *testing.T) {
    gin.SetMode(gin.TestMode)
    router := gin.New()
    router.Use(MyMiddleware())
    router.GET("/test", func(c *gin.Context) {
        c.JSON(200, gin.H{"status": "ok"})
    })

    w := httptest.NewRecorder()
    req, _ := http.NewRequest("GET", "/test", nil)
    router.ServeHTTP(w, req)

    assert.Equal(t, 200, w.Code)
}
```

### Verification Commands

```bash
# Compile check
cd gateway && go build ./...

# Run tests
cd gateway && go test ./... -v

# Run gateway
cd gateway && go run cmd/server/main.go

# Test health endpoint
curl http://localhost:8000/health

# Test proxy to config service
curl http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}'
```

# CLAUDE.md Addendum - Phase 3: Ingestion Service

## Phase 3 Context

- ✅ Phase 1: Config Service (port 8001) - Running
- ✅ Phase 2: Go Gateway (port 8000) - Running
- 🔨 Phase 3: Ingestion Service (port 8002) - Building now

## Architecture

```
Gateway:8000 → Ingestion Service:8002
                      │
                      ├── Celery Workers (async processing)
                      │      ├── Text Processor
                      │      ├── PDF Processor (Docling)
                      │      ├── Image Processor
                      │      └── DOCX Processor
                      │
                      ├── Chunkers
                      │      ├── Recursive
                      │      ├── Semantic
                      │      └── Document
                      │
                      ├── Embedders
                      │      ├── OpenAI
                      │      ├── Ollama
                      │      └── HuggingFace
                      │
                      ├── Graph Builder (optional)
                      │      └── LLM-based entity extraction
                      │
                      └── Storage
                             ├── MongoDB (chunks, vectors, graph)
                             └── Redis (Celery broker)
```

## Tech Stack

- **Framework**: FastAPI
- **Task Queue**: Celery + Redis
- **PDF Processing**: Docling, PyMuPDF
- **Embeddings**: OpenAI, Ollama, sentence-transformers
- **Database**: MongoDB (motor async driver)

## Project Structure

```
services/ingestion-service/
├── app/
│   ├── main.py
│   ├── api/v1/
│   │   ├── router.py
│   │   └── ingest.py
│   ├── core/
│   │   ├── settings.py
│   │   └── celery_app.py
│   ├── tasks/
│   │   └── ingestion_task.py
│   ├── processors/
│   │   ├── factory.py
│   │   ├── text.py
│   │   ├── pdf.py
│   │   ├── image.py
│   │   └── docx.py
│   ├── chunkers/
│   │   ├── factory.py
│   │   ├── recursive.py
│   │   ├── semantic.py
│   │   └── document.py
│   ├── embedders/
│   │   ├── factory.py
│   │   ├── openai.py
│   │   ├── ollama.py
│   │   └── huggingface.py
│   ├── graph/
│   │   ├── extractor.py
│   │   └── builder.py
│   └── storage/
│       ├── vector_store.py
│       └── graph_store.py
├── tests/
├── requirements.txt
└── Dockerfile
```

## Key Patterns

### Factory Pattern for Components
```python
def get_processor(file_type: DataType) -> BaseProcessor:
    processors = {
        DataType.TEXT: TextProcessor,
        DataType.PDF: PDFProcessor,
        DataType.IMAGE: ImageProcessor,
        DataType.DOCX: DOCXProcessor,
    }
    return processors[file_type]()
```

### Celery Task Pattern
```python
@celery_app.task(bind=True)
def run_ingestion(self, config_id: str):
    # Update status to processing
    # Process files
    # Update progress
    # Store results
    # Update status to completed
```

## Environment Variables

```bash
# Service
INGESTION_SERVICE_PORT=8002

# MongoDB (same as Phase 1)
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=rag_configurator

# Redis
REDIS_URL=redis://localhost:6379/0

# Embeddings
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```
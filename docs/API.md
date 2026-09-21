# API Documentation

Complete reference for all API endpoints. All requests go through the Gateway at `http://localhost:8000` unless otherwise specified.

## Base URL

```
Development: http://localhost:8000
Production: https://your-domain.com
```

## Authentication

RAG Configurator uses JWT Bearer tokens for authentication.

### Token Types

| Token | Lifetime | Usage |
|-------|----------|-------|
| Access Token | 30 minutes | API requests |
| Refresh Token | 7 days | Get new access token |

### Obtaining Tokens

**Register** (no auth required):
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "name": "John Doe"
    }
  }
}
```

**Login**:
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}
```

Response same as register.

**Refresh Token**:
```bash
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Response:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

### Using Tokens

Include the access token in the Authorization header:

```bash
curl http://localhost:8000/api/v1/configs \
  -H "Authorization: Bearer <your-access-token>"
```

### Token Structure

Decoded JWT payload:
```json
{
  "sub": "507f1f77bcf86cd799439011",  // User ID
  "type": "access",                   // Token type
  "exp": 1234567890,                  // Expiration timestamp
  "iat": 1234567800                   // Issued at timestamp
}
```

## Response Format

All API responses follow a standard format:

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "error": "Invalid email format"
    }
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid input data |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Backend service down |
| `INGESTION_FAILED` | 400 | Document processing error |
| `QUERY_ERROR` | 400 | RAG query failed |

## Auth Endpoints

### POST /api/v1/auth/register

Register a new user account.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "name": "John Doe"
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "name": "John Doe",
      "created_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

**Errors**:
- `409 CONFLICT` - Email already registered
- `422 VALIDATION_ERROR` - Invalid email or weak password

### POST /api/v1/auth/login

Authenticate and get tokens.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response** (200 OK): Same as register

**Errors**:
- `401 UNAUTHORIZED` - Invalid credentials

### POST /api/v1/auth/refresh

Get a new access token using refresh token.

**Request**:
```json
{
  "refresh_token": "eyJ..."
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Errors**:
- `401 UNAUTHORIZED` - Invalid or expired refresh token

### POST /api/v1/auth/logout

Invalidate the current session.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "message": "Logged out successfully"
  }
}
```

### GET /api/v1/auth/me

Get current user info.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

## User Endpoints

### GET /api/v1/users

List all users (admin only).

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `skip` (int, optional): Offset for pagination (default: 0)
- `limit` (int, optional): Max results (default: 100, max: 1000)

**Response** (200 OK):
```json
{
  "success": true,
  "data": [
    {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "name": "John Doe",
      "is_admin": false,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "meta": {
    "total": 1,
    "skip": 0,
    "limit": 100
  }
}
```

**Errors**:
- `403 FORBIDDEN` - Not an admin

### GET /api/v1/users/{id}

Get user by ID.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "name": "John Doe",
    "is_admin": false,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Errors**:
- `403 FORBIDDEN` - Can only view own profile (non-admin)
- `404 NOT_FOUND` - User not found

### PUT /api/v1/users/{id}

Update user profile.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "name": "Jane Doe",
  "password": "newpassword123"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "name": "Jane Doe",
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

**Errors**:
- `403 FORBIDDEN` - Can only update own profile
- `422 VALIDATION_ERROR` - Invalid input

### DELETE /api/v1/users/{id}

Delete user account.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "message": "User deleted successfully"
  }
}
```

**Errors**:
- `403 FORBIDDEN` - Can only delete own account (non-admin)

## Configuration Endpoints

### GET /api/v1/configs

List all configurations for current user.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `skip` (int, optional): Offset (default: 0)
- `limit` (int, optional): Limit (default: 100)
- `search` (string, optional): Search by name

**Response** (200 OK):
```json
{
  "success": true,
  "data": [
    {
      "id": "507f1f77bcf86cd799439012",
      "name": "Technical Docs RAG",
      "data_source": {
        "type": "local",
        "path": "/data/docs"
      },
      "model_config": {
        "llm_provider": "openai",
        "llm_model": "gpt-4"
      },
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "meta": {
    "total": 1,
    "skip": 0,
    "limit": 100
  }
}
```

### POST /api/v1/configs

Create a new RAG configuration.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "name": "Customer Support Bot",
  "data_source": {
    "type": "local",
    "path": "/data/kb",
    "file_types": ["pdf", "txt", "docx"]
  },
  "rbac": {
    "enabled": true,
    "roles": [
      {
        "name": "admin",
        "permissions": ["read", "write", "admin"]
      },
      {
        "name": "user",
        "permissions": ["read"]
      }
    ]
  },
  "model_config": {
    "llm_provider": "openai",
    "llm_model": "gpt-4",
    "llm_api_key": "sk-...",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "embedding_api_key": "sk-..."
  },
  "retrieval_config": {
    "retrieval_method": "hybrid",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "top_k": 5
  },
  "agent_config": {
    "agent_template": "self_rag",
    "temperature": 0.7,
    "max_iterations": 3
  },
  "prompt_config": {
    "system_prompt": "You are a helpful customer support assistant.",
    "rag_template": "Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
  }
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "id": "507f1f77bcf86cd799439013",
    "name": "Customer Support Bot",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Errors**:
- `422 VALIDATION_ERROR` - Invalid configuration

### GET /api/v1/configs/{id}

Get configuration by ID.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK): Full configuration object

**Errors**:
- `403 FORBIDDEN` - No access to this config
- `404 NOT_FOUND` - Config not found

### PUT /api/v1/configs/{id}

Update configuration.

**Headers**: `Authorization: Bearer <token>`

**Request**: Same as POST (all fields optional)

**Response** (200 OK): Updated configuration

**Errors**:
- `403 FORBIDDEN` - No write access

### DELETE /api/v1/configs/{id}

Delete configuration.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "message": "Configuration deleted successfully"
  }
}
```

### GET /api/v1/configs/{id}/export

Export configuration as YAML.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```yaml
name: Customer Support Bot
data_source:
  type: local
  path: /data/kb
  file_types:
    - pdf
    - txt
    - docx
rbac:
  enabled: true
  roles:
    - name: admin
      permissions:
        - read
        - write
        - admin
model_config:
  llm_provider: openai
  llm_model: gpt-4
retrieval_config:
  retrieval_method: hybrid
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5
agent_config:
  agent_template: self_rag
  temperature: 0.7
  max_iterations: 3
prompt_config:
  system_prompt: "You are a helpful customer support assistant."
  rag_template: "Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
```

### POST /api/v1/configs/import

Import configuration from YAML.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/configs/import \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: text/yaml" \
  --data-binary @config.yaml
```

**Response** (201 Created): Created configuration

## Ingestion Endpoints

### POST /api/v1/ingest

Start document ingestion job.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "config_id": "507f1f77bcf86cd799439013",
  "source_path": "/data/documents",
  "file_types": ["pdf", "txt"],
  "recursive": true
}
```

**Response** (202 Accepted):
```json
{
  "success": true,
  "data": {
    "task_id": "celery-task-uuid",
    "status": "queued",
    "message": "Ingestion job queued successfully"
  }
}
```

### GET /api/v1/ingest/{task_id}

Get ingestion job status.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "task_id": "celery-task-uuid",
    "config_id": "507f1f77bcf86cd799439013",
    "status": "processing",
    "progress": {
      "total_files": 10,
      "processed_files": 5,
      "failed_files": 0,
      "chunks_created": 150
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z"
  }
}
```

**Status Values**: `queued`, `processing`, `completed`, `failed`

### GET /api/v1/ingest

List ingestion jobs for user's configurations.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `config_id` (string, optional): Filter by config
- `status` (string, optional): Filter by status
- `skip`, `limit` (int, optional): Pagination

**Response** (200 OK): Array of job objects

### DELETE /api/v1/ingest/{task_id}

Cancel a queued or running ingestion job.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "message": "Job cancelled successfully"
  }
}
```

### POST /api/v1/ingest/{task_id}/retry

Retry a failed ingestion job.

**Headers**: `Authorization: Bearer <token>`

**Response** (202 Accepted): New task queued

## Evaluation Endpoints

RAG evaluation is implemented in rag-service and proxied by the gateway.

### POST /api/v1/evaluation/evaluate

Score a query/answer pair. `evaluator_type` may be `ragas` (default), `judge` (existing 0–1 rubrics), `quality` (1–5 + `does_pass` LLM judge), or `jev` (TypeSafe System One).

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "config_id": "config-id",
  "query": "How many PTO days for a 1-year employee?",
  "answer": "15 days (0–2 years tenure).",
  "contexts": ["0-2 years: 15 days (3 weeks)"],
  "evaluator_type": "jev"
}
```

If `answer` or `contexts` are omitted, the configured RAG pipeline generates them first.

### GET /api/v1/evaluation/jev-compare/latest

Return the last Jev vs LLM compare summary written by `scripts/jev_eval_compare.py`. Does not call providers. See [jev-eval.md](jev-eval.md).

### GET /api/v1/evaluation/{config_id}

Evaluation history for a configuration.

### GET /api/v1/evaluation/{config_id}/summary

Aggregated RAGAS/judge scores for a configuration.

## Query Endpoints

### POST /api/v1/query

Execute a RAG query (non-streaming).

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "config_id": "507f1f77bcf86cd799439013",
  "query": "What are the refund policies?",
  "context_filter": {
    "source_ids": ["doc-123"],
    "date_range": {
      "from": "2024-01-01",
      "to": "2024-12-31"
    }
  },
  "options": {
    "include_context": true,
    "include_sources": true
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "query": "What are the refund policies?",
    "answer": "According to our policy, refunds are available within 30 days...",
    "context": [
      {
        "content": "Refund Policy: Customers may request a refund within 30 days...",
        "source": "policies.pdf",
        "score": 0.95,
        "metadata": {
          "page": 5,
          "chunk_index": 12
        }
      }
    ],
    "sources": [
      {
        "id": "chunk-uuid",
        "document": "policies.pdf",
        "relevance_score": 0.95
      }
    ],
    "model": "gpt-4",
    "tokens_used": 150,
    "processing_time_ms": 2500,
    "retrieval_method": "hybrid"
  }
}
```

### POST /api/v1/chat

Execute a chat completion with conversation history.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "config_id": "507f1f77bcf86cd799439013",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "What are the refund policies?"
    },
    {
      "role": "assistant",
      "content": "According to our policy..."
    },
    {
      "role": "user",
      "content": "Can I get a partial refund?"
    }
  ],
  "options": {
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "message": {
      "role": "assistant",
      "content": "Yes, partial refunds are available depending on the usage..."
    },
    "context": [...],
    "sources": [...],
    "usage": {
      "prompt_tokens": 500,
      "completion_tokens": 150,
      "total_tokens": 650
    }
  }
}
```

### GET /api/v1/stream

Stream RAG response via Server-Sent Events (SSE).

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `config_id` (required): Configuration ID
- `query` (required): User query
- `include_context` (optional): Include context in response

**Response** (text/event-stream):
```
event: start
data: {"message": "Processing query..."}

event: context
data: {"sources": [{"document": "policies.pdf", "score": 0.95}]}

event: token
data: {"token": "According"}

event: token
data: {"token": " to"}

event: token
data: {"token": " our"}
...

event: complete
data: {"full_response": "According to our policy...", "tokens_used": 150}

event: error
data: {"error": "Something went wrong"}
```

### WebSocket /api/v1/stream/ws

WebSocket endpoint for bidirectional streaming.

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/stream/ws');

// Send auth and query
ws.send(JSON.stringify({
  token: 'Bearer <jwt>',
  config_id: '507f1f77bcf86cd799439013',
  query: 'What are the refund policies?'
}));

// Receive responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.token); // Streamed tokens
};
```

### POST /api/v1/query/similar

Find similar chunks to a given text.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "config_id": "507f1f77bcf86cd799439013",
  "text": "refund policy for software",
  "top_k": 5
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "similar_chunks": [
      {
        "content": "Software Refund Policy: Due to the digital nature...",
        "score": 0.92,
        "source": "software_policies.pdf"
      }
    ]
  }
}
```

## Folder Management Endpoints

### POST /api/v1/folders/scan

Scan a folder for documents.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "path": "/data/documents",
  "recursive": true,
  "file_types": ["pdf", "txt", "docx"]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "path": "/data/documents",
    "total_files": 150,
    "files_by_type": {
      "pdf": 50,
      "txt": 80,
      "docx": 20
    },
    "total_size_bytes": 104857600,
    "files": [
      {
        "path": "/data/documents/guide.pdf",
        "size": 2048576,
        "modified": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

### GET /api/v1/folders/validate

Validate folder accessibility.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `path` (required): Folder path to validate

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "path": "/data/documents",
    "exists": true,
    "readable": true,
    "writable": false,
    "file_count": 150
  }
}
```

## Health Endpoints

### GET /health

Gateway health check (no auth required).

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "gateway": "up",
    "config_service": "up",
    "ingestion_service": "up",
    "rag_service": "up"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /api/v1/health

Config Service health check.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Rate Limiting

Rate limits are enforced per IP address:

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Auth (login, register) | 5 | 1 minute |
| Query | 100 | 1 minute |
| Stream | 50 | 1 minute |
| Ingestion | 10 | 1 minute |
| Other | 1000 | 1 minute |

**Rate Limit Response** (429):
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Try again in 45 seconds."
  }
}
```

## Pagination

List endpoints support pagination:

**Query Parameters**:
- `skip`: Number of items to skip (default: 0)
- `limit`: Maximum items to return (default: 100, max: 1000)

**Response Meta**:
```json
{
  "success": true,
  "data": [...],
  "meta": {
    "total": 1000,
    "skip": 0,
    "limit": 100,
    "has_more": true
  }
}
```

---

For authentication details, see [Authentication section](#authentication)
For error handling, see [Error Codes table](#error-codes)
For example usage, see [QUICKSTART.md](QUICKSTART.md)

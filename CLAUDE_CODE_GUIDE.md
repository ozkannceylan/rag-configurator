# Claude Code Usage Guide

## Quick Start

```bash
# Navigate to your project root
cd /path/to/rag-configurator

# Start Claude Code
claude

# Or start with a specific task
claude "Implement the Config Service for Phase 1"
```

---

## Best Practices for Minimal Hallucination

### 1. Always Have CLAUDE.md in Repository Root

Claude Code automatically reads `CLAUDE.md` from your project root. This file should contain:
- Tech stack with versions
- Project structure
- Coding standards
- Common patterns
- Current phase/task context

**Copy the `CLAUDE.md` file I created to your repo root.**

### 2. Use Specific, Scoped Prompts

**Bad (vague):**
```
Build the backend
```

**Good (specific):**
```
Create the user authentication endpoints in services/config-service/app/api/v1/auth.py following the FastAPI patterns in CLAUDE.md. Include register, login, refresh, and logout endpoints.
```

### 3. Reference Existing Files

```
Look at shared/python/rag_config_common/models/config.py and create matching Pydantic schemas in services/config-service/app/schemas/config.py for API request/response.
```

### 4. Break Down Large Tasks

Instead of:
```
Implement Phase 1
```

Use sequential prompts:
```
# First
Create the FastAPI scaffold in services/config-service/app/main.py

# Then
Implement MongoDB connection in services/config-service/app/db/mongodb.py

# Then
Create the user repository in services/config-service/app/db/repositories/user_repo.py

# And so on...
```

### 5. Use Claude Code Commands

| Command | Purpose |
|---------|---------|
| `/help` | Show available commands |
| `/clear` | Clear conversation context |
| `/compact` | Summarize conversation to save context |
| `/cost` | Show token usage |
| `/doctor` | Check Claude Code health |
| `/init` | Initialize CLAUDE.md |
| `/review` | Review code changes |
| `/add <file>` | Add file to context |

### 6. Add Relevant Files to Context

Before asking Claude to modify something, add related files:

```
/add shared/python/rag_config_common/models/config.py
/add services/config-service/app/core/settings.py

Now create the config service that uses these models
```

### 7. Ask for Verification

```
After creating the file, show me how to test it works
```

```
Generate a curl command to test this endpoint
```

### 8. Request Incremental Changes

```
First, create just the file structure with empty files and docstrings.
Then I'll ask you to implement each function.
```

---

## Recommended Workflow for Phase 1

### Step 1: Setup Context Files

```bash
# Copy CLAUDE.md to your repo root
cp /path/to/CLAUDE.md ./CLAUDE.md

# Verify it's there
cat CLAUDE.md
```

### Step 2: Start Claude Code

```bash
cd /path/to/rag-configurator
claude
```

### Step 3: Execute Tasks Sequentially

Copy-paste these prompts one at a time:

#### Task P1-1: FastAPI Scaffold
```
Create the Config Service FastAPI scaffold. Create these files:
- services/config-service/app/main.py (FastAPI app with lifespan, CORS, health check)
- services/config-service/app/core/settings.py (Pydantic Settings)
- services/config-service/app/core/exceptions.py (Custom HTTP exceptions)
- services/config-service/app/api/v1/router.py (API router aggregator)
- services/config-service/requirements.txt
- services/config-service/pyproject.toml

Follow the patterns in CLAUDE.md. The service runs on port 8001.
```

#### Task P1-2: MongoDB Connection
```
Create the MongoDB connection handler in services/config-service/app/db/mongodb.py

Use motor for async MongoDB. Include:
- MongoDB class with connect/disconnect methods
- get_db dependency function
- Connection verification on startup

Follow async patterns from CLAUDE.md.
```

#### Task P1-3: User Repository
```
Create the repository layer for users:
- services/config-service/app/db/repositories/base.py (BaseRepository with CRUD)
- services/config-service/app/db/repositories/user_repo.py (UserRepository)

Include methods: find_by_id, find_by_email, create_user, update_user, deactivate_user
Use ObjectId from bson. Include serialize_doc helper.
```

#### Task P1-4: Auth Endpoints
```
Implement authentication:
1. services/config-service/app/core/security.py (JWT, password hashing)
2. services/config-service/app/schemas/auth.py (Request/Response schemas)
3. services/config-service/app/services/auth_service.py (Business logic)
4. services/config-service/app/api/v1/auth.py (Endpoints)

Endpoints: POST /auth/register, POST /auth/login, POST /auth/refresh, POST /auth/logout
Use python-jose for JWT, passlib for bcrypt.
```

#### Task P1-5: JWT Dependency
```
Create the authentication dependency in services/config-service/app/api/deps.py

Include:
- get_current_user function that extracts and validates JWT from Authorization header
- CurrentUser type alias for dependency injection
- Proper error handling with UnauthorizedException
```

#### Task P1-6: Config Repository
```
Create services/config-service/app/db/repositories/config_repo.py

Include methods:
- find_by_user (with pagination and sorting)
- count_by_user
- find_by_name
- create_config
- update_config
- is_owner (ownership check)
```

#### Task P1-7: Config Endpoints
```
Implement configuration CRUD:
1. services/config-service/app/schemas/config.py (Import from rag_config_common)
2. services/config-service/app/services/config_service.py (Business logic)
3. services/config-service/app/api/v1/configs.py (Endpoints)

Endpoints: GET/POST /configs, GET/PUT/DELETE /configs/{id}, POST /configs/{id}/duplicate
All endpoints require authentication. Include ownership validation.
```

#### Task P1-8 & P1-9: Folder Scanner
```
Implement folder scanning:
1. services/config-service/app/schemas/folder.py
2. services/config-service/app/services/folder_service.py
3. services/config-service/app/api/v1/folders.py

The scanner should:
- Recursively scan local directories
- Detect file types (txt, pdf, image, docx, etc.)
- Return folder tree structure
- Flag if multimodal content exists
```

#### Task P1-10: YAML Export/Import
```
Implement configuration export/import:
1. services/config-service/app/services/export_service.py
2. services/config-service/app/api/v1/export.py

GET /configs/{id}/export - returns YAML file
POST /configs/import - accepts YAML file upload

Use PyYAML. Include metadata in export.
```

#### Task P1-11: Tests
```
Create tests for the Config Service:
1. services/config-service/tests/conftest.py (Fixtures)
2. services/config-service/tests/test_auth.py
3. services/config-service/tests/test_configs.py

Use pytest-asyncio. Create test database fixtures.
Test: register, login, refresh, CRUD operations, authorization.
```

### Step 4: Verify Each Task

After each task, verify:

```bash
# Check syntax
cd services/config-service
python -c "from app.main import app; print('OK')"

# Run specific tests
pytest tests/test_auth.py -v
```

### Step 5: Run Full Service

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e ../../shared/python

# Start service
uvicorn app.main:app --reload --port 8001

# Test health
curl http://localhost:8001/health

# Open docs
open http://localhost:8001/docs
```

---

## Troubleshooting

### "Module not found" errors

```bash
# Make sure shared package is installed
pip install -e shared/python

# Verify
python -c "from rag_config_common.models import RAGPipelineConfig; print('OK')"
```

### MongoDB connection errors

```bash
# Check MongoDB is running
docker-compose ps

# If not, start it
docker-compose up -d mongodb
```

### Claude Code context issues

```
/clear
/add CLAUDE.md
/add services/config-service/app/main.py

Let's continue with [specific task]
```

### Request too large

```
/compact

# Then continue with smaller, focused prompts
```

---

## Tips for Better Results

1. **Start fresh each session** - Use `/clear` if context gets messy

2. **One file at a time** - Don't ask for multiple complex files at once

3. **Show examples** - "Similar to how auth.py does it, create..."

4. **Specify imports** - "Import from rag_config_common.models, not define new models"

5. **Request tests** - "Also write a test for this function"

6. **Verify understanding** - "Before writing code, explain your approach"

7. **Use file references** - `/add` files before asking to modify them

8. **Check generated code** - Always review before accepting

---

## Sample Session

```
$ claude
╭─────────────────────────────────────────╮
│ Claude Code                             │
╰─────────────────────────────────────────╯

> /add CLAUDE.md
Added CLAUDE.md to context

> /add shared/python/rag_config_common/models/config.py
Added config.py to context

> Create services/config-service/app/schemas/config.py that defines ConfigCreate, ConfigUpdate, ConfigResponse schemas. Import the model definitions from rag_config_common instead of redefining them.

[Claude generates the file]

> Show me how to test this works

[Claude shows test code or curl commands]

> /review
[Claude reviews recent changes]

> Looks good, now create the ConfigService in services/config-service/app/services/config_service.py
```

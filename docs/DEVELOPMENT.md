# Development Guide

This guide covers setting up the development environment, running tests, and contributing to RAG Configurator.

## Table of Contents

- [Local Setup (No Docker)](#local-setup-no-docker)
- [Running Services Individually](#running-services-individually)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Contributing Guidelines](#contributing-guidelines)
- [PR Process](#pr-process)

## Local Setup (No Docker)

For development without Docker, you'll need to install services directly on your machine.

### Prerequisites

| Software | Version | Installation |
|----------|---------|--------------|
| Python | 3.11+ | [python.org](https://python.org) |
| Go | 1.22+ | [golang.org](https://golang.org) |
| Node.js | 20 LTS | [nodejs.org](https://nodejs.org) |
| MongoDB | 7.0+ | [mongodb.com](https://mongodb.com) |
| Redis | 7.0+ | [redis.io](https://redis.io) |

### macOS Setup

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 go node mongodb-community redis

# Start services
brew services start mongodb-community
brew services start redis

# Install Python packages
pip3 install virtualenv
```

### Ubuntu/Debian Setup

```bash
# Update packages
sudo apt update

# Install Python
sudo apt install python3.11 python3.11-venv python3-pip

# Install Go
wget https://go.dev/dl/go1.22.0.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.22.0.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod

# Install Redis
sudo apt install redis-server
sudo systemctl start redis
```

### Windows Setup (WSL2 Recommended)

Use WSL2 with Ubuntu, then follow the Ubuntu instructions above.

Alternatively, with native Windows:

1. Install Python from python.org
2. Install Go from golang.org
3. Install Node.js from nodejs.org
4. Install MongoDB Community Server
5. Install Redis (or use Redis on WSL2)
6. Use Git Bash or PowerShell

### Repository Setup

```bash
# Clone repository
git clone https://github.com/your-org/rag-configurator.git
cd rag-configurator

# Install shared Python package
cd shared/python
pip install -e .
cd ../..

# Install Python dependencies for each service
cd services/config-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cd ../..

# Repeat for other services
for service in ingestion-service rag-service; do
  cd services/$service
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  pip install -r requirements-dev.txt
  cd ../..
done

# Install Go dependencies
cd gateway
go mod download
cd ..

# Install Node dependencies
for ui in configurator sandbox; do
  cd ui/$ui
  npm install
  cd ../..
done
```

## Running Services Individually

### 1. Start Infrastructure

```bash
# macOS
brew services start mongodb-community
brew services start redis

# Ubuntu
sudo systemctl start mongod
sudo systemctl start redis

# Verify
mongosh --eval "db.adminCommand('ping')"
redis-cli ping
```

### 2. Start Config Service

```bash
cd services/config-service
source venv/bin/activate

# Create .env file
cat > .env << EOF
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=rag_configurator
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
CONFIG_SERVICE_PORT=8001
EOF

# Run with auto-reload
uvicorn app.main:app --reload --port 8001
```

### 3. Start Ingestion Service

```bash
cd services/ingestion-service
source venv/bin/activate

# Create .env file
cat > .env << EOF
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=rag_configurator
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
INGESTION_SERVICE_PORT=8002
EOF

# Start service
uvicorn app.main:app --reload --port 8002

# In another terminal, start Celery worker
cd services/ingestion-service
source venv/bin/activate
celery -A app.core.celery_app worker -l info
```

### 4. Start RAG Service

```bash
cd services/rag-service
source venv/bin/activate

# Create .env file
cat > .env << EOF
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=rag_configurator
RAG_SERVICE_PORT=8003
OPENAI_API_KEY=your-key-here
EOF

# Run with auto-reload
uvicorn app.main:app --reload --port 8003
```

### 5. Start Gateway

```bash
cd gateway

# Create .env file
cat > .env << EOF
GATEWAY_PORT=8000
CONFIG_SERVICE_URL=http://localhost:8001
INGESTION_SERVICE_URL=http://localhost:8002
RAG_SERVICE_URL=http://localhost:8003
JWT_SECRET_KEY=dev-secret-key-change-in-production
ENVIRONMENT=development
LOG_LEVEL=debug
EOF

# Run
go run cmd/server/main.go
```

### 6. Start Frontend UIs

```bash
# Configurator UI
cd ui/configurator
npm run dev
# Opens on http://localhost:5173

# In another terminal - Sandbox UI
cd ui/sandbox
npm run dev
# Opens on http://localhost:3001
```

### Service Port Summary

| Service | Port | URL |
|---------|------|-----|
| Config Service | 8001 | http://localhost:8001 |
| Ingestion Service | 8002 | http://localhost:8002 |
| RAG Service | 8003 | http://localhost:8003 |
| Gateway | 8000 | http://localhost:8000 |
| Configurator UI | 5173 | http://localhost:5173 |
| Sandbox UI | 3001 | http://localhost:3001 |
| MongoDB | 27017 | mongodb://localhost:27017 |
| Redis | 6379 | redis://localhost:6379 |

## Running Tests

### Python Services Tests

All Python services use pytest with pytest-asyncio.

```bash
# Config Service
cd services/config-service
source venv/bin/activate
pytest -v

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_auth.py -v

# With debugging
pytest tests/test_auth.py -v --pdb

# Parallel execution
pytest -n auto
```

### Go Gateway Tests

```bash
cd gateway

# Run all tests
go test ./...

# Verbose output
go test ./... -v

# Coverage
go test ./... -cover

# Race detection
go test ./... -race

# Specific package
go test ./internal/middleware -v
```

### Frontend Tests

```bash
# Configurator UI
cd ui/configurator

# Unit tests
npm test

# With coverage
npm run test:coverage

# E2E tests (if configured)
npm run test:e2e

# Same for Sandbox
cd ui/sandbox
npm test
```

### Integration Tests

```bash
# Start all services first, then:
cd tests/integration

# Python integration tests
pytest -v

# Or use a test script
./run-integration-tests.sh
```

### Test Data

Create test fixtures:

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def test_user():
    return {
        "email": "test@example.com",
        "password": "testpass123",
        "name": "Test User"
    }

@pytest.fixture
async def auth_token(client, test_user):
    # Register and login
    await client.post("/api/v1/auth/register", json=test_user)
    response = await client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"]
    })
    return response.json()["data"]["access_token"]
```

## Code Style

### Python (Black + Ruff)

**Configuration** (`pyproject.toml`):
```toml
[tool.black]
line-length = 88
target-version = ['py311']

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]

[tool.ruff.pydocstyle]
convention = "google"
```

**Running Linters**:
```bash
# Format code
black services/*/app

# Check style
ruff check services/*/app

# Fix auto-fixable issues
ruff check services/*/app --fix

# Check specific file
black services/config-service/app/api/v1/auth.py
ruff check services/config-service/app/api/v1/auth.py
```

**Pre-commit Hook**:
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Manual run
pre-commit run --all-files
```

### Go (gofmt + golint)

**Formatting**:
```bash
cd gateway

# Format all files
go fmt ./...

# Vet for issues
go vet ./...

# Lint (requires golint)
golint ./...

# All checks
make lint
```

### TypeScript/Vue (ESLint + Prettier)

**Configuration** (`.eslintrc.cjs`):
```javascript
module.exports = {
  root: true,
  env: {
    node: true,
  },
  extends: [
    'plugin:vue/vue3-essential',
    'eslint:recommended',
    '@vue/typescript/recommended',
    'prettier',
  ],
  parserOptions: {
    ecmaVersion: 2020,
  },
  rules: {
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
  },
}
```

**Running Linters**:
```bash
cd ui/configurator

# Check code
npm run lint

# Fix auto-fixable issues
npm run lint:fix

# Format with Prettier
npx prettier --write "src/**/*.{ts,vue,css}"
```

### Git Hooks

Setup pre-commit hooks for all languages:

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit checks..."

# Python
for service in services/*; do
  if [ -d "$service" ]; then
    echo "Checking $service..."
    (cd "$service" && black --check app && ruff check app) || exit 1
  fi
done

# Go
(cd gateway && go fmt ./... && go vet ./...) || exit 1

# TypeScript
for ui in ui/*; do
  if [ -d "$ui" ]; then
    echo "Checking $ui..."
    (cd "$ui" && npm run lint) || exit 1
  fi
done

echo "All checks passed!"
```

## Contributing Guidelines

### Getting Started

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make your changes**
4. **Run tests and linting**
5. **Commit with clear messages**
6. **Push to your fork**
7. **Open a Pull Request**

### Code Standards

**Python**:
- Use type hints for all function signatures
- Follow Google docstring style
- Maximum line length: 88 characters
- Write tests for new features
- Maintain >80% test coverage

**Go**:
- Follow standard Go formatting (gofmt)
- Use meaningful variable names
- Handle all errors explicitly
- Add comments for exported functions

**TypeScript/Vue**:
- Use Composition API with `<script setup>`
- Add TypeScript types for all props and emits
- Use Pinia for state management
- Follow Vue 3 style guide

### Commit Message Format

Use conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(api): add support for multi-tenant configurations

fix(ingestion): resolve PDF parsing error for large files

docs(readme): update quickstart instructions

refactor(gateway): simplify JWT middleware
```

### Branch Naming

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical production fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

**Examples**:
- `feature/hybrid-retrieval`
- `bugfix/auth-token-refresh`
- `docs/api-examples`

### Documentation

Update documentation for all changes:

- **Code changes**: Add/update docstrings
- **API changes**: Update API.md
- **New features**: Add to README.md
- **Breaking changes**: Document in CHANGELOG.md

### Testing Requirements

All contributions must include:

1. **Unit tests** for new functionality
2. **Integration tests** for API endpoints
3. **Updated existing tests** if behavior changes

```python
# Example test structure
def test_new_feature(client, auth_token):
    """Test description of what this tests."""
    # Arrange
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Act
    response = client.post("/api/v1/new-endpoint", 
                          headers=headers, 
                          json={"key": "value"})
    
    # Assert
    assert response.status_code == 201
    assert response.json()["success"] is True
```

## PR Process

### Before Submitting

1. **Run all tests**
```bash
# Python services
pytest services/*/tests

# Go gateway
go test ./gateway/...

# Frontend
npm test --prefix ui/configurator
npm test --prefix ui/sandbox
```

2. **Run linters**
```bash
make lint  # or equivalent for your changes
```

3. **Update documentation**
4. **Add CHANGELOG.md entry**

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally

## Screenshots (if UI changes)

## Related Issues
Fixes #123
```

### Review Process

1. **Automated checks** must pass:
   - CI/CD pipeline
   - Linting
   - Tests
   - Coverage thresholds

2. **Code review** by maintainers:
   - At least 1 approval required
   - All comments resolved
   - No merge conflicts

3. **Merge requirements**:
   - Squash and merge preferred
   - Clean commit history
   - Up-to-date with main branch

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=app --cov-report=xml
      - run: black --check .
      - run: ruff check .

  test-go:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
        with:
          go-version: '1.22'
      - run: cd gateway && go test ./...
      - run: cd gateway && go vet ./...

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: cd ui/configurator && npm ci && npm test
      - run: cd ui/sandbox && npm ci && npm test
```

### Release Process

1. **Version bump**: Update version in relevant files
2. **Update CHANGELOG.md**: Document all changes
3. **Create Git tag**: `git tag -a v1.2.0 -m "Release v1.2.0"`
4. **Push tag**: `git push origin v1.2.0`
5. **Create GitHub release** with release notes
6. **Deploy** to production environment

---

For quick start, see [QUICKSTART.md](QUICKSTART.md)
For deployment, see [DEPLOYMENT.md](DEPLOYMENT.md)
For API docs, see [API.md](API.md)

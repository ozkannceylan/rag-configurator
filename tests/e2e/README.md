# E2E Tests

End-to-end tests for the RAG Configurator platform.

## Prerequisites

Ensure all services are running:
- Gateway: http://localhost:8000
- Config Service: http://localhost:8001
- Ingestion Service: http://localhost:8002
- RAG Service: http://localhost:8003
- MongoDB
- Redis

## Installation

```bash
cd tests/e2e
pip install -r requirements.txt
```

## Running Tests

Run all E2E tests:
```bash
pytest tests/e2e/ -v
```

Run specific test file:
```bash
pytest tests/e2e/test_auth_flow.py -v
```

Run with more verbosity:
```bash
pytest tests/e2e/ -vv --tb=short
```

## Test Files

- `conftest.py` - pytest fixtures (client, auth_headers, sample_config)
- `test_auth_flow.py` - Authentication tests (register, login, refresh, logout)
- `test_config_crud.py` - Configuration CRUD operations
- `test_ingestion_flow.py` - Ingestion job lifecycle
- `test_query_flow.py` - Query and chat endpoints
- `test_full_scenario.py` - Complete user journeys

## Test Design

- All tests are independent and clean up after themselves
- Unique test data prevents conflicts between parallel runs
- Tests use `pytest-asyncio` for async support
- Fixtures provide reusable setup/teardown

.PHONY: help dev dev-up dev-down dev-logs build test lint clean install jev-eval-compare jev-eval-compare-live

# Default target
help:
	@echo "RAG Configurator - Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  dev          Start development environment (docker + services)"
	@echo "  dev-up       Start Docker containers only"
	@echo "  dev-down     Stop Docker containers"
	@echo "  dev-logs     View Docker container logs"
	@echo "  build        Build all Docker images"
	@echo "  test         Run all tests"
	@echo "  jev-eval-compare  Jev vs LLM-as-judge on frozen RAG traces (mock/demo)"
	@echo "  jev-eval-compare-live  Same compare with live TypeSafe + Ollama Cloud keys"
	@echo "  lint         Run linters"
	@echo "  clean        Clean up generated files"
	@echo "  install      Install all dependencies"
	@echo ""

# Development
dev: dev-up
	@echo "Development environment started!"
	@echo ""
	@echo "Services:"
	@echo "  MongoDB:         localhost:27017"
	@echo "  Redis:           localhost:6379"
	@echo "  Mongo Express:   http://localhost:8081"
	@echo "  Redis Commander: http://localhost:8082"

dev-up:
	docker compose up -d

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f

# Build
build:
	docker compose build

# Testing
test: test-python test-go test-ui

test-python:
	@echo "Running Python tests..."
	cd services/config-service && python -m pytest tests/ -v
	cd services/ingestion-service && python -m pytest tests/ -v
	cd services/rag-service && python -m pytest tests/ -v

test-go:
	@echo "Running Go tests..."
	cd gateway && go test ./... -v

test-ui:
	@echo "Running UI tests..."
	cd apps/configurator-ui && npm run test
	cd apps/sandbox-ui && npm run test

# Jev vs LLM-as-judge compare (offline mock by default)
jev-eval-compare:
	PYTHONPATH=services/rag-service python scripts/jev_eval_compare.py --mock

jev-eval-compare-live:
	PYTHONPATH=services/rag-service python scripts/jev_eval_compare.py --live

# Linting
lint: lint-python lint-go lint-ui

lint-python:
	@echo "Linting Python..."
	cd services/config-service && python -m ruff check .
	cd services/ingestion-service && python -m ruff check .
	cd services/rag-service && python -m ruff check .

lint-go:
	@echo "Linting Go..."
	cd gateway && golangci-lint run

lint-ui:
	@echo "Linting UI..."
	cd apps/configurator-ui && npm run lint
	cd apps/sandbox-ui && npm run lint

# Install dependencies
install: install-python install-go install-ui install-shared

install-python:
	@echo "Installing Python dependencies..."
	pip install -e shared/python
	cd services/config-service && pip install -r requirements.txt
	cd services/ingestion-service && pip install -r requirements.txt
	cd services/rag-service && pip install -r requirements.txt

install-go:
	@echo "Installing Go dependencies..."
	cd gateway && go mod download

install-ui:
	@echo "Installing UI dependencies..."
	cd apps/configurator-ui && npm install
	cd apps/sandbox-ui && npm install

install-shared:
	@echo "Installing shared TypeScript package..."
	cd shared/typescript && npm install && npm run build

# Clean
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	docker compose down -v --remove-orphans

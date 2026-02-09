# RAG Configurator Deployment Guide

## Quick Start

### Development
```bash
cd docker
docker-compose up -d
```

### Production
```bash
cd docker

# 1. Create secrets
echo "admin" > secrets/mongodb_root_username.txt
echo "your-secure-password" > secrets/mongodb_root_password.txt
echo "your-redis-password" > secrets/redis_password.txt
openssl rand -hex 32 > secrets/jwt_secret_key.txt
echo "your-openai-key" > secrets/openai_api_key.txt
echo "your-anthropic-key" > secrets/anthropic_api_key.txt

# 2. Setup SSL certificates
mkdir -p nginx/ssl
cp /path/to/cert.pem nginx/ssl/
cp /path/to/key.pem nginx/ssl/
cp /path/to/chain.pem nginx/ssl/

# 3. Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## File Structure

```
docker/
├── docker-compose.yml          # Development stack
├── docker-compose.prod.yml     # Production stack
├── nginx/
│   ├── nginx.conf             # Production nginx config
│   ├── nginx.dev.conf         # Development nginx config
│   └── ssl/                   # SSL certificates (prod only)
└── secrets/                   # Docker secrets (prod only)
    ├── mongodb_root_username.txt
    ├── mongodb_root_password.txt
    ├── redis_password.txt
    ├── jwt_secret_key.txt
    ├── openai_api_key.txt
    └── anthropic_api_key.txt
```

## Environment Variables

See `.env.example` in the project root for all available options.

## Services

| Service | Port | Description |
|---------|------|-------------|
| nginx | 80/443 | Reverse proxy |
| gateway | 8000 | API Gateway (Go) |
| config-service | 8001 | Configuration & Auth API |
| ingestion-service | 8002 | Document processing |
| rag-service | 8003 | RAG runtime |
| celery-worker | - | Background task processor |
| configurator-ui | 80 | Admin UI |
| sandbox-ui | 80 | Chat test UI |
| mongodb | 27017 | Database |
| redis | 6379 | Cache & queue |

## Production Checklist

- [ ] Change all default passwords
- [ ] Generate secure JWT secret key
- [ ] Setup SSL certificates
- [ ] Configure proper CORS origins
- [ ] Enable MongoDB/Redis authentication
- [ ] Set resource limits appropriate for your hardware
- [ ] Configure backups for MongoDB
- [ ] Setup log aggregation
- [ ] Enable monitoring (Prometheus/Grafana)
- [ ] Configure alerts

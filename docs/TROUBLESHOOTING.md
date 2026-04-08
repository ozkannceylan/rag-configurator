# Troubleshooting Guide

Common issues and solutions for RAG Configurator.

## Table of Contents

- [Common Errors](#common-errors)
- [Service-Specific Issues](#service-specific-issues)
- [Log Locations](#log-locations)
- [Health Checks](#health-checks)
- [Debug Mode](#debug-mode)
- [FAQ](#faq)

## Common Errors

### Installation & Startup

| Error | Cause | Solution |
|-------|-------|----------|
| `Port already in use` | Another service using port | Find process: `lsof -i :8000`, kill it or change port |
| `Connection refused` | Service not running | Check `docker-compose ps`, restart service |
| `Permission denied` | File permissions | Run `chmod +x scripts/*.sh` or check Docker permissions |
| `Module not found` | Missing dependencies | Run `pip install -r requirements.txt` in service directory |
| `MongoDB connection failed` | MongoDB not ready | Wait 30s, check `docker-compose logs mongodb` |
| `Redis connection error` | Redis not running | Check `redis-cli ping`, restart Redis service |

### Authentication Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Missing/invalid token | Check Authorization header format: `Bearer <token>` |
| `Token expired` | JWT expired | Use refresh token to get new access token |
| `Invalid credentials` | Wrong email/password | Check credentials, reset password if needed |
| `403 Forbidden` | Insufficient permissions | Check RBAC configuration, request access |

### Ingestion Failures

| Error | Cause | Solution |
|-------|-------|----------|
| `File not found` | Wrong path or permissions | Verify path exists and is readable |
| `Unsupported file type` | File extension not recognized | Add to `file_types` in config or convert file |
| `PDF parsing failed` | Corrupted or scanned PDF | Try OCR version or convert to text |
| `Out of memory` | Large file or too many chunks | Increase container memory limit or reduce chunk size |
| `Timeout` | Processing taking too long | Increase timeout, split into smaller files |
| `Embedding failed` | API error or rate limit | Check API key, wait and retry |

### Query & Chat Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `No results found` | No matching documents | Check ingestion completed, verify data source |
| `Empty context` | Retrieved chunks empty | Increase `top_k`, check retrieval config |
| `LLM timeout` | Slow model or long query | Use faster model, reduce max_tokens, increase timeout |
| `Rate limit exceeded` | Too many requests | Implement client-side rate limiting, upgrade plan |
| `Streaming interrupted` | Connection closed | Check network, reduce timeout, retry |

## Service-Specific Issues

### Gateway (Port 8000)

**Issue**: Gateway returns `502 Bad Gateway`

**Diagnosis**:
```bash
curl http://localhost:8000/health
```

**Solutions**:
1. Check backend services are running:
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

2. Restart gateway:
```bash
docker-compose restart gateway
```

3. Check gateway logs:
```bash
docker-compose logs gateway
```

**Issue**: CORS errors in browser

**Solution**: Update CORS origins in gateway config:
```bash
# .env or docker-compose.yml
CORS_ORIGINS=http://localhost:5173,http://localhost:3001
```

### Config Service (Port 8001)

**Issue**: User registration fails

**Check**:
```bash
# Check MongoDB connection
docker-compose exec config-service python -c "
from motor.motor_asyncio import AsyncIOMotorClient
client = AsyncIOMotorClient('mongodb://mongodb:27017')
print(client.server_info())
"
```

**Issue**: JWT validation fails

**Causes**:
- Mismatched JWT secret between services
- Clock skew between servers
- Wrong algorithm

**Fix**:
1. Ensure `JWT_SECRET_KEY` matches across all services
2. Verify `JWT_ALGORITHM` is consistent (default: HS256)
3. Check system time is synchronized

### Ingestion Service (Port 8002)

**Issue**: Celery tasks not processing

**Diagnosis**:
```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Check Celery worker logs
docker-compose logs celery-worker

# Check queue length
docker-compose exec redis redis-cli LLEN celery
```

**Solutions**:
1. Restart Celery worker:
```bash
docker-compose restart celery-worker
```

2. Clear stuck tasks:
```bash
docker-compose exec redis redis-cli FLUSHDB
```

**Issue**: PDF processing fails with Unicode errors

**Solution**: Install additional dependencies:
```bash
docker-compose exec ingestion-service pip install \
  pdfplumber \
  pytesseract \
  pdf2image
```

### RAG Service (Port 8003)

**Issue**: Query returns no results

**Diagnosis**:
```bash
# Check if chunks exist in MongoDB
docker-compose exec mongodb mongosh --eval "
use rag_configurator
db.chunks.countDocuments({config_id: 'your-config-id'})
"
```

**Solutions**:
1. Verify ingestion completed successfully
2. Check vector search index exists:
```bash
docker-compose exec mongodb mongosh --eval "
use rag_configurator
db.chunks.getIndexes()
"
```

3. Re-run ingestion if needed

**Issue**: LLM responses are slow

**Solutions**:
1. Use faster model (GPT-3.5 instead of GPT-4)
2. Reduce `max_tokens` in agent config
3. Enable caching for common queries
4. Use streaming for better perceived performance

### Frontend Issues

**Issue**: Configurator UI blank page

**Diagnosis**:
```bash
# Check browser console for errors
# Check API connectivity
curl http://localhost:8000/health
```

**Solutions**:
1. Clear browser cache and hard reload (Ctrl+Shift+R)
2. Check API URL in UI config:
```bash
docker-compose exec configurator-ui cat .env
```

3. Rebuild UI:
```bash
docker-compose up -d --build configurator-ui
```

## Log Locations

### Docker Compose

```bash
# All services logs
docker-compose logs -f

# Specific service
docker-compose logs -f <service-name>

# Follow logs (live)
docker-compose logs -f --tail=100 gateway

# Last N lines
docker-compose logs --tail=500 config-service
```

### Service Logs Inside Containers

| Service | Log Location |
|---------|-------------|
| Gateway | `/var/log/gateway/` or stdout |
| Config Service | stdout (configured via logging) |
| Ingestion Service | stdout + Celery logs |
| RAG Service | stdout |
| MongoDB | `/var/log/mongodb/` |
| Redis | stdout |

### Log Levels

Configure via environment variables:

```bash
# Gateway
LOG_LEVEL=debug    # debug, info, warn, error

# Python services (in .env)
LOG_LEVEL=DEBUG
LOG_FORMAT=json    # json, text
```

### Viewing Logs

**Real-time monitoring**:
```bash
# Watch all services
watch -n 1 'docker-compose ps'

# Watch specific logs
tail -f logs/gateway.log
```

**Export logs**:
```bash
# Save to file
docker-compose logs > all-logs.txt

# Specific time range
docker-compose logs --since="2024-01-15T10:00:00" --until="2024-01-15T11:00:00"
```

## Health Checks

### Gateway Health

```bash
curl http://localhost:8000/health
```

Expected response:
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

### Service Health

```bash
# Config Service
curl http://localhost:8001/health

# Ingestion Service
curl http://localhost:8002/health

# RAG Service
curl http://localhost:8003/health
```

### Database Health

**MongoDB**:
```bash
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

**Redis**:
```bash
docker-compose exec redis redis-cli ping
```

### Celery Health

```bash
# Check worker status
docker-compose exec celery-worker celery -A app.core.celery_app inspect active

# Check queue
docker-compose exec celery-worker celery -A app.core.celery_app inspect stats
```

## Debug Mode

### Enable Debug Logging

**Gateway**:
```bash
# In docker-compose.yml or .env
LOG_LEVEL=debug
```

**Python Services**:
```yaml
# In config or .env
LOG_LEVEL=DEBUG
DEBUG=True
```

### Verbose API Responses

Add `?debug=true` to API calls:

```bash
curl "http://localhost:8000/api/v1/query?debug=true" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": "...",
    "query": "test"
  }'
```

Response includes:
```json
{
  "success": true,
  "data": { ... },
  "debug": {
    "retrieval_time_ms": 150,
    "chunks_retrieved": 5,
    "llm_tokens": 250,
    "llm_time_ms": 1200,
    "query_reformulated": "..."
  }
}
```

### Tracing Requests

Each request gets a unique ID:

```bash
# Request
curl -i http://localhost:8000/api/v1/configs \
  -H "Authorization: Bearer <token>"

# Response headers
X-Request-ID: abc-123-def-456
```

Search logs by request ID:
```bash
docker-compose logs | grep "abc-123-def-456"
```

### Database Inspection

```bash
# Enter MongoDB shell
docker-compose exec mongodb mongosh

# Show databases
show dbs

# Use database
use rag_configurator

# Show collections
show collections

# Query documents
db.configurations.findOne()
db.chunks.find({config_id: "your-id"}).limit(5)
db.users.find({email: "test@example.com"})

# Count documents
db.chunks.countDocuments()

# Check indexes
db.chunks.getIndexes()
```

### Python Debugging

Add breakpoint in code:
```python
import pdb; pdb.set_trace()
```

Or use `ipdb` for better debugging:
```python
import ipdb; ipdb.set_trace()
```

Run service with debug flag:
```bash
cd services/config-service
python -m pdb -m uvicorn app.main:app
```

## FAQ

### General Questions

**Q: How do I reset everything and start fresh?**

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Remove all data
rm -rf data/mongodb/*
rm -rf data/redis/*

# Start fresh
docker-compose up -d
```

**Q: How do I update to the latest version?**

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose up -d --build

# Run migrations if needed
docker-compose exec config-service python migrate.py
```

**Q: Can I use GPU for embeddings?**

Yes, for HuggingFace embeddings:
```yaml
model_config:
  embedding_provider: "huggingface"
  embedding_device: "cuda"  # or "mps" for Mac
```

### Performance Questions

**Q: Queries are too slow, how do I speed them up?**

1. Use faster LLM (GPT-3.5 instead of GPT-4)
2. Reduce `top_k` in retrieval config
3. Enable caching
4. Use streaming responses
5. Optimize chunk size (smaller = faster retrieval)

**Q: Ingestion is taking too long**

1. Increase Celery workers:
```yaml
services:
  celery-worker:
    deploy:
      replicas: 8  # Increase from default
```

2. Use smaller chunk sizes
3. Process files in parallel
4. Use local embedding models

**Q: High memory usage**

1. Reduce chunk size and overlap
2. Limit `top_k` in retrieval
3. Reduce `max_tokens` for LLM
4. Add memory limits in docker-compose:
```yaml
services:
  rag-service:
    deploy:
      resources:
        limits:
          memory: 2G
```

### Configuration Questions

**Q: How do I use different LLMs for different configs?**

Each configuration has its own `model_config`:
```yaml
# Config 1 - OpenAI
model_config:
  llm_provider: "openai"
  llm_model: "gpt-4"

# Config 2 - Local Ollama
model_config:
  llm_provider: "ollama"
  llm_model: "llama3.2"
```

**Q: Can I have multiple data sources?**

Currently one data source per config. Create multiple configs:
```yaml
# Config for product docs
config_1:
  data_source:
    type: "local"
    path: "/data/product-docs"

# Config for API docs
config_2:
  data_source:
    type: "s3"
    bucket: "api-docs"
```

**Q: How do I schedule regular ingestion?**

Use external scheduler like cron:
```bash
# Add to crontab
0 2 * * * curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer <token>" \
  -d '{"config_id": "...", "source_path": "/data"}'
```

### Integration Questions

**Q: Can I use my own MongoDB/Redis?**

Yes, update connection strings:
```bash
MONGODB_URI=mongodb://your-host:27017
REDIS_URL=redis://your-host:6379/0
```

**Q: How do I integrate with external auth (OAuth, SSO)?**

Modify the Config Service auth module or use the Gateway to handle OAuth before proxying.

**Q: Can I export data?**

Yes, configurations export as YAML:
```bash
curl http://localhost:8000/api/v1/configs/{id}/export \
  -H "Authorization: Bearer <token>"
```

For full data export from MongoDB:
```bash
docker-compose exec mongodb mongodump \
  --out /backup/$(date +%Y%m%d)
```

### Error Messages Reference

| Error Code | Meaning | Action |
|------------|---------|--------|
| `E001` | Database connection failed | Check MongoDB is running |
| `E002` | Redis connection failed | Check Redis is running |
| `E003` | Authentication failed | Check JWT token |
| `E004` | Rate limit exceeded | Wait and retry |
| `E005` | Service unavailable | Check service health |
| `E006` | Invalid configuration | Validate config schema |
| `E007` | Ingestion failed | Check file permissions |
| `E008` | Query timeout | Increase timeout or simplify |
| `E009` | LLM API error | Check API key and limits |
| `E010` | Vector search failed | Check index exists |

## Getting Help

If issues persist:

1. **Check logs**: `docker-compose logs -f`
2. **Health checks**: Test all `/health` endpoints
3. **Documentation**: Review relevant docs
4. **GitHub Issues**: [github.com/your-org/rag-configurator/issues](https://github.com/your-org/rag-configurator/issues)

Include in bug reports:
- Error message
- Steps to reproduce
- Service logs
- Configuration (redact secrets)
- Environment details (OS, versions)

---

For quick start, see [QUICKSTART.md](QUICKSTART.md)
For deployment, see [DEPLOYMENT.md](DEPLOYMENT.md)
For API docs, see [API.md](API.md)

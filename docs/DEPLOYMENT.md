# Deployment Guide

This guide covers deploying RAG Configurator in development and production environments.

## Table of Contents

- [Docker Compose (Development)](#docker-compose-development)
- [Docker Compose (Production)](#docker-compose-production)
- [Environment Variables](#environment-variables)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Kubernetes (Optional)](#kubernetes-optional)
- [Scaling Considerations](#scaling-considerations)

## Docker Compose (Development)

The simplest way to get started locally.

### Prerequisites

- Docker 20.10+
- Docker Compose 2.20+
- 8GB RAM minimum

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/rag-configurator.git
cd rag-configurator

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f gateway
```

### Development Compose File

```yaml
version: '3.8'

services:
  # Databases
  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Backend Services
  config-service:
    build: ./services/config-service
    ports:
      - "8001:8001"
    environment:
      - MONGODB_URI=mongodb://admin:password@mongodb:27017
      - MONGODB_DATABASE=rag_configurator
      - JWT_SECRET_KEY=dev-secret-key
    depends_on:
      - mongodb

  ingestion-service:
    build: ./services/ingestion-service
    ports:
      - "8002:8002"
    environment:
      - MONGODB_URI=mongodb://admin:password@mongodb:27017
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - mongodb
      - redis

  rag-service:
    build: ./services/rag-service
    ports:
      - "8003:8003"
    environment:
      - MONGODB_URI=mongodb://admin:password@mongodb:27017
    depends_on:
      - mongodb

  # Gateway
  gateway:
    build: ./gateway
    ports:
      - "8000:8000"
    environment:
      - GATEWAY_PORT=8000
      - CONFIG_SERVICE_URL=http://config-service:8001
      - INGESTION_SERVICE_URL=http://ingestion-service:8002
      - RAG_SERVICE_URL=http://rag-service:8003
      - JWT_SECRET_KEY=dev-secret-key
    depends_on:
      - config-service
      - ingestion-service
      - rag-service

  # Frontend
  configurator-ui:
    build: ./ui/configurator
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000

  sandbox-ui:
    build: ./ui/sandbox
    ports:
      - "3001:3001"
    environment:
      - VITE_API_URL=http://localhost:8000

volumes:
  mongodb_data:
```

### Useful Commands

```bash
# Rebuild after code changes
docker-compose up -d --build

# View specific service logs
docker-compose logs -f config-service

# Restart a service
docker-compose restart gateway

# Stop everything
docker-compose down

# Stop and remove volumes (clears data!)
docker-compose down -v

# Execute commands in containers
docker-compose exec config-service python -m pytest
```

## Docker Compose (Production)

For production deployments with security and performance optimizations.

### Production Compose File

```yaml
version: '3.8'

services:
  # Databases with persistence
  mongodb:
    image: mongo:7.0
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME_FILE: /run/secrets/mongo_root_username
      MONGO_INITDB_ROOT_PASSWORD_FILE: /run/secrets/mongo_root_password
    volumes:
      - mongodb_data:/data/db
      - ./backups:/backups
    networks:
      - backend
    secrets:
      - mongo_root_username
      - mongo_root_password
    command: mongod --auth --bind_ip_all

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - backend

  # Services (no exposed ports, only internal)
  config-service:
    build: ./services/config-service
    restart: always
    environment:
      - MONGODB_URI=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@mongodb:27017/rag_configurator?authSource=admin
      - JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret_key
      - ENVIRONMENT=production
    networks:
      - backend
    secrets:
      - jwt_secret_key
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

  ingestion-service:
    build: ./services/ingestion-service
    restart: always
    environment:
      - MONGODB_URI=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@mongodb:27017/rag_configurator?authSource=admin
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_WORKERS=4
    networks:
      - backend
    deploy:
      replicas: 2

  rag-service:
    build: ./services/rag-service
    restart: always
    environment:
      - MONGODB_URI=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@mongodb:27017/rag_configurator?authSource=admin
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key
      - ANTHROPIC_API_KEY_FILE=/run/secrets/anthropic_api_key
    networks:
      - backend
    secrets:
      - openai_api_key
      - anthropic_api_key
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 2G

  # Gateway (only externally exposed service)
  gateway:
    build: ./gateway
    restart: always
    ports:
      - "8000:8000"
    environment:
      - GATEWAY_PORT=8000
      - CONFIG_SERVICE_URL=http://config-service:8001
      - INGESTION_SERVICE_URL=http://ingestion-service:8002
      - RAG_SERVICE_URL=http://rag-service:8003
      - JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret_key
      - ENVIRONMENT=production
      - RATE_LIMIT_RPS=100
      - CORS_ORIGINS=${CORS_ORIGINS}
    networks:
      - backend
    secrets:
      - jwt_secret_key
    deploy:
      replicas: 2

  # Frontend behind Nginx
  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./ui/configurator/dist:/usr/share/nginx/html/configurator:ro
      - ./ui/sandbox/dist:/usr/share/nginx/html/sandbox:ro
    depends_on:
      - gateway
    networks:
      - backend

  # Celery Worker
  celery-worker:
    build: ./services/ingestion-service
    restart: always
    command: celery -A app.core.celery_app worker -l info -c 4
    environment:
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - MONGODB_URI=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@mongodb:27017/rag_configurator?authSource=admin
    networks:
      - backend
    deploy:
      replicas: 2

  # Celery Flower (monitoring)
  flower:
    build: ./services/ingestion-service
    restart: always
    command: celery -A app.core.celery_app flower --port=5555
    environment:
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    ports:
      - "5555:5555"
    networks:
      - backend

volumes:
  mongodb_data:
  redis_data:

networks:
  backend:
    driver: bridge

secrets:
  jwt_secret_key:
    file: ./secrets/jwt_secret_key.txt
  mongo_root_username:
    file: ./secrets/mongo_root_username.txt
  mongo_root_password:
    file: ./secrets/mongo_root_password.txt
  openai_api_key:
    file: ./secrets/openai_api_key.txt
  anthropic_api_key:
    file: ./secrets/anthropic_api_key.txt
```

### Production Deployment Steps

1. **Create secrets directory**:
```bash
mkdir -p secrets
echo "your-strong-jwt-secret" > secrets/jwt_secret_key.txt
echo "admin" > secrets/mongo_root_username.txt
echo "strong-password" > secrets/mongo_root_password.txt
echo "sk-..." > secrets/openai_api_key.txt
echo "sk-ant-..." > secrets/anthropic_api_key.txt
chmod 600 secrets/*
```

2. **Create environment file**:
```bash
cat > .env.production << EOF
MONGO_USER=admin
MONGO_PASSWORD=strong-password
REDIS_PASSWORD=redis-strong-password
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
EOF
```

3. **Deploy**:
```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | Secret for JWT signing | `your-256-bit-secret` |
| `MONGODB_URI` | MongoDB connection string | `mongodb://user:pass@host:27017/db` |
| `MONGODB_DATABASE` | Database name | `rag_configurator` |

### Service-Specific Variables

#### Gateway
| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_PORT` | `8000` | Gateway listen port |
| `CONFIG_SERVICE_URL` | - | Config service URL |
| `INGESTION_SERVICE_URL` | - | Ingestion service URL |
| `RAG_SERVICE_URL` | - | RAG service URL |
| `RATE_LIMIT_RPS` | `100` | Requests per second limit |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

#### Config Service
| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

#### Ingestion Service
| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | - | Redis connection |
| `CELERY_BROKER_URL` | - | Celery broker URL |
| `CELERY_WORKERS` | `4` | Number of Celery workers |

#### RAG Service
| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `OLLAMA_BASE_URL` | - | Ollama server URL |
| `VLLM_BASE_URL` | - | vLLM server URL |
| `MLFLOW_TRACKING_URI` | - | MLflow server URL |

### Frontend Variables

#### Configurator UI
| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL |

#### Sandbox UI
| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL |

## SSL/TLS Configuration

### Using Let's Encrypt

1. **Install certbot**:
```bash
sudo apt-get install certbot
```

2. **Obtain certificates**:
```bash
sudo certbot certonly --standalone -d yourdomain.com
```

3. **Update nginx configuration**:
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://gateway:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

4. **Auto-renewal**:
```bash
# Add to crontab
0 12 * * * /usr/bin/certbot renew --quiet
```

### Using Self-Signed Certificates (Development)

```bash
# Generate certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/nginx.key \
  -out nginx/ssl/nginx.crt \
  -subj "/CN=localhost"
```

## Kubernetes (Optional)

Basic Kubernetes manifests for production deployment.

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rag-configurator
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-config
  namespace: rag-configurator
data:
  GATEWAY_PORT: "8000"
  ENVIRONMENT: "production"
  MONGODB_DATABASE: "rag_configurator"
  JWT_ALGORITHM: "HS256"
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES: "30"
```

### Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-secrets
  namespace: rag-configurator
type: Opaque
stringData:
  JWT_SECRET_KEY: "your-secret-key"
  MONGODB_URI: "mongodb://user:pass@mongodb:27017/rag_configurator"
  OPENAI_API_KEY: "sk-..."
```

### MongoDB Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mongodb
  namespace: rag-configurator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mongodb
  template:
    metadata:
      labels:
        app: mongodb
    spec:
      containers:
      - name: mongodb
        image: mongo:7.0
        ports:
        - containerPort: 27017
        env:
        - name: MONGO_INITDB_ROOT_USERNAME
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: MONGO_USER
        - name: MONGO_INITDB_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: MONGO_PASSWORD
        volumeMounts:
        - name: mongodb-storage
          mountPath: /data/db
      volumes:
      - name: mongodb-storage
        persistentVolumeClaim:
          claimName: mongodb-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: mongodb
  namespace: rag-configurator
spec:
  selector:
    app: mongodb
  ports:
  - port: 27017
    targetPort: 27017
```

### Gateway Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
  namespace: rag-configurator
spec:
  replicas: 2
  selector:
    matchLabels:
      app: gateway
  template:
    metadata:
      labels:
        app: gateway
    spec:
      containers:
      - name: gateway
        image: your-registry/rag-gateway:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: rag-config
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: JWT_SECRET_KEY
        - name: CONFIG_SERVICE_URL
          value: "http://config-service:8001"
        - name: INGESTION_SERVICE_URL
          value: "http://ingestion-service:8002"
        - name: RAG_SERVICE_URL
          value: "http://rag-service:8003"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: gateway
  namespace: rag-configurator
spec:
  type: LoadBalancer
  selector:
    app: gateway
  ports:
  - port: 80
    targetPort: 8000
```

### Ingress (with SSL)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rag-ingress
  namespace: rag-configurator
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: rag-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: gateway
            port:
              number: 80
```

## Scaling Considerations

### Horizontal Pod Autoscaling (K8s)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gateway-hpa
  namespace: rag-configurator
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### MongoDB Scaling

**Vertical Scaling**:
```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

**Sharding** (for very large datasets):
```bash
# Enable sharding
mongosh --eval "sh.enableSharding('rag_configurator')"

# Shard collections
mongosh --eval "sh.shardCollection('rag_configurator.chunks', { config_id: 1, _id: 1 })"
```

### Redis Scaling

**Redis Cluster**:
```yaml
# Use Redis Cluster for production
image: redis:7-alpine
command: redis-server --cluster-enabled yes
```

### Performance Tuning

| Service | Bottleneck | Solution |
|---------|------------|----------|
| Gateway | CPU | Scale horizontally, use connection pooling |
| Config Service | DB connections | Use connection pooling, cache configs |
| Ingestion Service | Memory | Limit concurrent workers, use streaming |
| RAG Service | LLM latency | Cache responses, use faster models for simple queries |
| MongoDB | Disk I/O | Use SSD, create proper indexes |

### Monitoring Setup

**Prometheus + Grafana**:
```yaml
# Add to docker-compose.prod.yml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus:/etc/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
```

**Key Metrics to Monitor**:
- Request latency (p50, p95, p99)
- Error rates by endpoint
- LLM token usage and costs
- MongoDB query performance
- Celery queue depth
- Memory and CPU usage

---

For development setup, see [DEVELOPMENT.md](DEVELOPMENT.md)
For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

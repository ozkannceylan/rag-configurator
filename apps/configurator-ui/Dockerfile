# Configurator UI Dockerfile
# Multi-stage build for Vue.js application

# ==========================================
# Stage 1: Dependencies
# ==========================================
FROM node:20-alpine AS dependencies

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# ==========================================
# Stage 2: Builder
# ==========================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependencies from previous stage
COPY --from=dependencies /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build the application
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# ==========================================
# Stage 3: Development
# ==========================================
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including dev)
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 5173

# Command for development
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ==========================================
# Stage 4: Production
# ==========================================
FROM nginx:alpine AS production

# Copy custom nginx config for SPA
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --spider -q http://localhost:80/ || exit 1

# Expose port
EXPOSE 80

# Run nginx
CMD ["nginx", "-g", "daemon off;"]

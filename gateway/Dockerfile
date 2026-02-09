# Gateway Dockerfile
# Multi-stage build for Go application

# ==========================================
# Stage 1: Builder
# ==========================================
FROM golang:1.24-alpine AS builder

# Install git and ca-certificates for fetching dependencies
RUN apk add --no-cache git ca-certificates

# Set working directory
WORKDIR /app

# Copy go mod files first for better caching
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
# CGO_ENABLED=0 creates a static binary
# -ldflags "-w -s" strips debug info for smaller binary
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags "-w -s -X main.Version=${VERSION:-dev} -X main.BuildTime=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    -o gateway \
    cmd/server/main.go

# ==========================================
# Stage 2: Development
# ==========================================
FROM golang:1.24-alpine AS development

WORKDIR /app

# Install air for hot reload (optional)
RUN go install github.com/cosmtrek/air@latest

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Expose port
EXPOSE 8000

# Command with hot reload
CMD ["air", "-c", ".air.toml"]

# ==========================================
# Stage 3: Production
# ==========================================
FROM scratch AS production

# Copy CA certificates for HTTPS requests
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy the binary from builder
COPY --from=builder /app/gateway /gateway

# Set non-root user (use numeric UID for scratch compatibility)
USER 1000:1000

# Expose port
EXPOSE 8000

# Health check
# Note: scratch image doesn't have curl/wget, so we use a TCP check
# Or you can use a minimal distroless image with health check support
# For now, we'll skip the healthcheck in scratch and rely on orchestrator

# Run the binary
ENTRYPOINT ["/gateway"]

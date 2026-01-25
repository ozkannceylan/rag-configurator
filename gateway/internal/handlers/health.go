package handlers

import (
	"context"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"

	"gateway/internal/config"
)

// ServiceHealth represents the health status of a backend service
type ServiceHealth struct {
	Name    string `json:"name"`
	URL     string `json:"url"`
	Status  string `json:"status"`
	Latency string `json:"latency,omitempty"`
}

// HealthResponse represents the full health check response
type HealthResponse struct {
	Status      string          `json:"status"`
	Service     string          `json:"service"`
	Environment string          `json:"environment"`
	Backends    []ServiceHealth `json:"backends,omitempty"`
}

// HTTP client with timeout for health checks
var healthCheckClient = &http.Client{
	Timeout: 5 * time.Second,
}

// Health returns a handler for basic health check endpoint
// Fast liveness check - always returns 200 if gateway is running
func Health(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, HealthResponse{
			Status:      "healthy",
			Service:     "gateway",
			Environment: cfg.Environment,
		})
	}
}

// HealthDetailed returns a handler that checks all backend services
func HealthDetailed(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Check all backend services
		backends := checkBackends(healthCheckClient, cfg)

		// Determine overall status
		status := "healthy"
		httpStatus := http.StatusOK

		for _, backend := range backends {
			if backend.Status == "unhealthy" {
				status = "degraded"
				httpStatus = http.StatusServiceUnavailable
				break
			}
		}

		c.JSON(httpStatus, HealthResponse{
			Status:      status,
			Service:     "gateway",
			Environment: cfg.Environment,
			Backends:    backends,
		})
	}
}

// checkBackends checks all backend services concurrently
func checkBackends(client *http.Client, cfg *config.Config) []ServiceHealth {
	services := []struct {
		name string
		url  string
	}{
		{"config-service", cfg.ConfigServiceURL + "/health"},
		{"ingestion-service", cfg.IngestionServiceURL + "/health"},
		{"rag-service", cfg.RAGServiceURL + "/health"},
	}

	results := make([]ServiceHealth, len(services))
	var wg sync.WaitGroup

	for i, svc := range services {
		wg.Add(1)
		go func(idx int, name, url string) {
			defer wg.Done()
			results[idx] = checkService(client, name, url)
		}(i, svc.name, svc.url)
	}

	wg.Wait()
	return results
}

// checkService checks a single backend service health
func checkService(client *http.Client, name, url string) ServiceHealth {
	result := ServiceHealth{
		Name:   name,
		URL:    url,
		Status: "unhealthy",
	}

	// Create context with timeout for individual check
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	// Create request with context
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		log.Warn().
			Err(err).
			Str("service", name).
			Str("url", url).
			Msg("Failed to create health check request")
		return result
	}

	// Measure latency
	start := time.Now()
	resp, err := client.Do(req)
	latency := time.Since(start)

	if err != nil {
		log.Warn().
			Err(err).
			Str("service", name).
			Str("url", url).
			Msg("Backend health check failed")
		return result
	}
	defer resp.Body.Close()

	// Check for successful status code
	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		result.Status = "healthy"
		result.Latency = fmt.Sprintf("%dms", latency.Milliseconds())
	} else {
		log.Warn().
			Str("service", name).
			Str("url", url).
			Int("status_code", resp.StatusCode).
			Msg("Backend returned non-2xx status")
	}

	return result
}

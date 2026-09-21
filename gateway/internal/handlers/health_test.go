package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"gateway/internal/config"
)

func init() {
	gin.SetMode(gin.TestMode)
}

func newTestConfig() *config.Config {
	return &config.Config{
		Environment:         "test",
		ConfigServiceURL:    "http://localhost:8001",
		IngestionServiceURL: "http://localhost:8002",
		RAGServiceURL:       "http://localhost:8003",
	}
}

func TestHealth_ReturnsHealthy(t *testing.T) {
	cfg := newTestConfig()

	router := gin.New()
	router.GET("/health", Health(cfg))

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)

	assert.Equal(t, 200, w.Code)

	var response HealthResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.Equal(t, "healthy", response.Status)
	assert.Equal(t, "gateway", response.Service)
	assert.Equal(t, "test", response.Environment)
	assert.Nil(t, response.Backends)
}

func TestHealth_AlwaysReturns200(t *testing.T) {
	cfg := newTestConfig()

	router := gin.New()
	router.GET("/health", Health(cfg))

	// Multiple requests should all succeed
	for i := 0; i < 5; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/health", nil)
		router.ServeHTTP(w, req)
		assert.Equal(t, 200, w.Code)
	}
}

func TestHealthDetailed_AllHealthy(t *testing.T) {
	// Create mock backend servers that return healthy
	configBackend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
		_, _ = w.Write([]byte(`{"status":"healthy"}`))
	}))
	defer configBackend.Close()

	ingestionBackend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
		_, _ = w.Write([]byte(`{"status":"healthy"}`))
	}))
	defer ingestionBackend.Close()

	ragBackend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
		_, _ = w.Write([]byte(`{"status":"healthy"}`))
	}))
	defer ragBackend.Close()

	cfg := &config.Config{
		Environment:         "test",
		ConfigServiceURL:    configBackend.URL,
		IngestionServiceURL: ingestionBackend.URL,
		RAGServiceURL:       ragBackend.URL,
	}

	router := gin.New()
	router.GET("/health/detailed", HealthDetailed(cfg))

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health/detailed", nil)
	router.ServeHTTP(w, req)

	assert.Equal(t, 200, w.Code)

	var response HealthResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.Equal(t, "healthy", response.Status)
	assert.Equal(t, "gateway", response.Service)
	assert.Len(t, response.Backends, 3)

	for _, backend := range response.Backends {
		assert.Equal(t, "healthy", backend.Status)
		assert.NotEmpty(t, backend.Latency)
	}
}

func TestHealthDetailed_SomeDegraded(t *testing.T) {
	// Create one healthy backend and two unhealthy
	configBackend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
		_, _ = w.Write([]byte(`{"status":"healthy"}`))
	}))
	defer configBackend.Close()

	cfg := &config.Config{
		Environment:         "test",
		ConfigServiceURL:    configBackend.URL,
		IngestionServiceURL: "http://localhost:59998", // Non-existent
		RAGServiceURL:       "http://localhost:59999", // Non-existent
	}

	router := gin.New()
	router.GET("/health/detailed", HealthDetailed(cfg))

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health/detailed", nil)
	router.ServeHTTP(w, req)

	// Should return 503 Service Unavailable
	assert.Equal(t, 503, w.Code)

	var response HealthResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.Equal(t, "degraded", response.Status)
	assert.Len(t, response.Backends, 3)

	// Count healthy and unhealthy
	healthyCount := 0
	unhealthyCount := 0
	for _, backend := range response.Backends {
		if backend.Status == "healthy" {
			healthyCount++
		} else {
			unhealthyCount++
		}
	}

	assert.Equal(t, 1, healthyCount)
	assert.Equal(t, 2, unhealthyCount)
}

func TestHealthDetailed_AllUnhealthy(t *testing.T) {
	cfg := &config.Config{
		Environment:         "test",
		ConfigServiceURL:    "http://localhost:59997",
		IngestionServiceURL: "http://localhost:59998",
		RAGServiceURL:       "http://localhost:59999",
	}

	router := gin.New()
	router.GET("/health/detailed", HealthDetailed(cfg))

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health/detailed", nil)
	router.ServeHTTP(w, req)

	assert.Equal(t, 503, w.Code)

	var response HealthResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.Equal(t, "degraded", response.Status)

	for _, backend := range response.Backends {
		assert.Equal(t, "unhealthy", backend.Status)
		assert.Empty(t, backend.Latency)
	}
}

func TestHealthDetailed_BackendReturnsNon2xx(t *testing.T) {
	// Create a backend that returns 500
	unhealthyBackend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(500)
		_, _ = w.Write([]byte(`{"status":"error"}`))
	}))
	defer unhealthyBackend.Close()

	cfg := &config.Config{
		Environment:         "test",
		ConfigServiceURL:    unhealthyBackend.URL,
		IngestionServiceURL: unhealthyBackend.URL,
		RAGServiceURL:       unhealthyBackend.URL,
	}

	router := gin.New()
	router.GET("/health/detailed", HealthDetailed(cfg))

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health/detailed", nil)
	router.ServeHTTP(w, req)

	assert.Equal(t, 503, w.Code)

	var response HealthResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.Equal(t, "degraded", response.Status)

	for _, backend := range response.Backends {
		assert.Equal(t, "unhealthy", backend.Status)
	}
}

func TestCheckService_Healthy(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
		_, _ = w.Write([]byte(`{"status":"healthy"}`))
	}))
	defer backend.Close()

	client := &http.Client{}
	result := checkService(client, "test-service", backend.URL+"/health")

	assert.Equal(t, "test-service", result.Name)
	assert.Equal(t, backend.URL+"/health", result.URL)
	assert.Equal(t, "healthy", result.Status)
	assert.NotEmpty(t, result.Latency)
}

func TestCheckService_Unhealthy(t *testing.T) {
	client := &http.Client{}
	result := checkService(client, "test-service", "http://localhost:59999/health")

	assert.Equal(t, "test-service", result.Name)
	assert.Equal(t, "unhealthy", result.Status)
	assert.Empty(t, result.Latency)
}

func TestCheckService_Returns500(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(500)
	}))
	defer backend.Close()

	client := &http.Client{}
	result := checkService(client, "test-service", backend.URL+"/health")

	assert.Equal(t, "unhealthy", result.Status)
	assert.Empty(t, result.Latency)
}

func TestCheckBackends_Concurrent(t *testing.T) {
	// Create three backends that all return healthy
	createHealthyBackend := func() *httptest.Server {
		return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(200)
			_, _ = w.Write([]byte(`{"status":"healthy"}`))
		}))
	}

	b1 := createHealthyBackend()
	b2 := createHealthyBackend()
	b3 := createHealthyBackend()
	defer b1.Close()
	defer b2.Close()
	defer b3.Close()

	cfg := &config.Config{
		ConfigServiceURL:    b1.URL,
		IngestionServiceURL: b2.URL,
		RAGServiceURL:       b3.URL,
	}

	client := &http.Client{}
	results := checkBackends(client, cfg)

	assert.Len(t, results, 3)

	// All should be healthy
	for _, result := range results {
		assert.Equal(t, "healthy", result.Status)
	}
}

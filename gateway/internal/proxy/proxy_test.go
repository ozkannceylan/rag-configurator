package proxy

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"gateway/internal/config"
)

func init() {
	gin.SetMode(gin.TestMode)
}

func setupMockBackend(t *testing.T) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Echo back request details for verification
		response := map[string]interface{}{
			"method":       r.Method,
			"path":         r.URL.Path,
			"query":        r.URL.RawQuery,
			"auth_header":  r.Header.Get("Authorization"),
			"content_type": r.Header.Get("Content-Type"),
			"x_forwarded":  r.Header.Get("X-Forwarded-For"),
		}

		// Read body if present
		if r.Body != nil && r.ContentLength > 0 {
			var body map[string]interface{}
			if err := json.NewDecoder(r.Body).Decode(&body); err == nil {
				response["body"] = body
			}
		}

		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("X-Backend-Header", "test-value")
		json.NewEncoder(w).Encode(response)
	}))
}

// setupGateway creates a test server with the proxy router
func setupGateway(t *testing.T, cfg *config.Config) *httptest.Server {
	proxy := New(cfg)

	router := gin.New()
	router.GET("/api/v1/configs", proxy.ToConfigService())
	router.GET("/api/v1/configs/:id", proxy.ToConfigService())
	router.POST("/api/v1/configs", proxy.ToConfigService())
	router.PUT("/api/v1/configs/:id", proxy.ToConfigService())
	router.DELETE("/api/v1/configs/:id", proxy.ToConfigService())
	router.POST("/api/v1/ingest/:config_id/start", proxy.ToIngestionService())
	router.GET("/api/v1/ingest/:config_id/status", proxy.ToIngestionService())
	router.POST("/api/v1/query", proxy.ToRAGService())
	router.GET("/test", proxy.ToConfigService())
	router.Handle("PATCH", "/test", proxy.ToConfigService())
	router.GET("/search", proxy.ToConfigService())

	return httptest.NewServer(router)
}

func TestProxy_ForwardsPath(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	resp, err := http.Get(gateway.URL + "/api/v1/configs/abc123")
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.Equal(t, "GET", response["method"])
	assert.Equal(t, "/api/v1/configs/abc123", response["path"])
}

func TestProxy_ForwardsQueryParams(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	resp, err := http.Get(gateway.URL + "/api/v1/configs?page=2&limit=10")
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.Equal(t, "page=2&limit=10", response["query"])
}

func TestProxy_ForwardsAuthorizationHeader(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	req, _ := http.NewRequest("GET", gateway.URL+"/api/v1/configs", nil)
	req.Header.Set("Authorization", "Bearer test-token-123")

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.Equal(t, "Bearer test-token-123", response["auth_header"])
}

func TestProxy_ForwardsBody(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	body := `{"name":"test config","description":"test"}`
	req, _ := http.NewRequest("POST", gateway.URL+"/api/v1/configs", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.Equal(t, "POST", response["method"])
	assert.Equal(t, "application/json", response["content_type"])

	bodyData, ok := response["body"].(map[string]interface{})
	require.True(t, ok)
	assert.Equal(t, "test config", bodyData["name"])
}

func TestProxy_AddsForwardedHeaders(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	resp, err := http.Get(gateway.URL + "/test")
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	// X-Forwarded-For should contain client IP (127.0.0.1 in tests)
	assert.NotEmpty(t, response["x_forwarded"])
}

func TestProxy_CopiesResponseHeaders(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	resp, err := http.Get(gateway.URL + "/test")
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)
	assert.Equal(t, "test-value", resp.Header.Get("X-Backend-Header"))
}

func TestProxy_HandlesBackendDown(t *testing.T) {
	cfg := &config.Config{
		ConfigServiceURL:    "http://localhost:59999", // Non-existent service
		IngestionServiceURL: "http://localhost:59999",
		RAGServiceURL:       "http://localhost:59999",
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	resp, err := http.Get(gateway.URL + "/test")
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, 502, resp.StatusCode)

	body, _ := io.ReadAll(resp.Body)
	assert.Contains(t, string(body), "Service unavailable")
}

func TestProxy_ToIngestionService(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	req, _ := http.NewRequest("POST", gateway.URL+"/api/v1/ingest/config123/start", nil)
	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.Equal(t, "POST", response["method"])
	assert.Equal(t, "/api/v1/ingest/config123/start", response["path"])
}

func TestProxy_ToRAGService(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	body := `{"query":"What is RAG?","config_id":"abc123"}`
	req, _ := http.NewRequest("POST", gateway.URL+"/api/v1/query", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.Equal(t, "POST", response["method"])
	assert.Equal(t, "/api/v1/query", response["path"])
}

func TestProxy_PreservesAllHTTPMethods(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	client := &http.Client{}

	tests := []struct {
		method string
		path   string
	}{
		{"GET", "/test"},
		{"PATCH", "/test"},
	}

	for _, tt := range tests {
		t.Run(tt.method, func(t *testing.T) {
			req, _ := http.NewRequest(tt.method, gateway.URL+tt.path, nil)
			resp, err := client.Do(req)
			require.NoError(t, err)
			defer resp.Body.Close()

			require.Equal(t, 200, resp.StatusCode)

			var response map[string]interface{}
			err = json.NewDecoder(resp.Body).Decode(&response)
			require.NoError(t, err)

			assert.Equal(t, tt.method, response["method"])
		})
	}
}

func TestProxy_HandlesMultipleQueryParams(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	resp, err := http.Get(gateway.URL + "/search?q=test&page=1&sort=desc&filter=active")
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	// Query params should be preserved
	query := response["query"].(string)
	assert.Contains(t, query, "q=test")
	assert.Contains(t, query, "page=1")
	assert.Contains(t, query, "sort=desc")
	assert.Contains(t, query, "filter=active")
}

func TestProxy_PUT_Method(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	body := `{"name":"updated config"}`
	req, _ := http.NewRequest("PUT", gateway.URL+"/api/v1/configs/abc123", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.Equal(t, "PUT", response["method"])
	assert.Equal(t, "/api/v1/configs/abc123", response["path"])
}

func TestProxy_DELETE_Method(t *testing.T) {
	backend := setupMockBackend(t)
	defer backend.Close()

	cfg := &config.Config{
		ConfigServiceURL:    backend.URL,
		IngestionServiceURL: backend.URL,
		RAGServiceURL:       backend.URL,
	}

	gateway := setupGateway(t, cfg)
	defer gateway.Close()

	req, _ := http.NewRequest("DELETE", gateway.URL+"/api/v1/configs/abc123", nil)

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, 200, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.Equal(t, "DELETE", response["method"])
	assert.Equal(t, "/api/v1/configs/abc123", response["path"])
}

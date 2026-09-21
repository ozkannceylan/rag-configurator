package router

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"

	"gateway/internal/config"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// createTestToken creates a valid JWT token for testing
func createTestToken(cfg *config.Config) string {
	claims := jwt.MapClaims{
		"sub":  "test-user-123",
		"type": "access",
		"exp":  time.Now().Add(1 * time.Hour).Unix(),
		"iat":  time.Now().Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, _ := token.SignedString([]byte(cfg.JWTSecretKey))
	return tokenString
}

func newTestConfig() *config.Config {
	return &config.Config{
		Port:                8000,
		Environment:         "test",
		LogLevel:            "info",
		JWTSecretKey:        "test-secret-key",
		JWTAlgorithm:        "HS256",
		InterServiceSecret:  "test-inter-service-secret",
		ConfigServiceURL:    "http://localhost:8001",
		IngestionServiceURL: "http://localhost:8002",
		RAGServiceURL:       "http://localhost:8003",
		CORSOrigins:         []string{"http://localhost:3000"},
		RateLimitRPS:        100,
		RateLimitBurst:      200,
	}
}

// setupMockBackend creates a mock backend that echoes request info
func setupMockBackend() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		response := map[string]interface{}{
			"method":      r.Method,
			"path":        r.URL.Path,
			"query":       r.URL.RawQuery,
			"auth_header": r.Header.Get("Authorization"),
			"x_user_id":   r.Header.Get("X-User-ID"),
		}
		w.Header().Set("Content-Type", "application/json")
		// Header is already sent; nothing useful to do with an encode failure.
		_ = json.NewEncoder(w).Encode(response)
	}))
}

// setupGatewayServer creates a test server with the router
func setupGatewayServer(cfg *config.Config) *httptest.Server {
	router := New(cfg)
	return httptest.NewServer(router)
}

func TestHealthEndpoint(t *testing.T) {
	cfg := newTestConfig()
	router := New(cfg)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status code %d, got %d", http.StatusOK, w.Code)
	}

	var response map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	if response["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got %v", response["status"])
	}

	if response["service"] != "gateway" {
		t.Errorf("Expected service 'gateway', got %v", response["service"])
	}

	if response["environment"] != "test" {
		t.Errorf("Expected environment 'test', got %v", response["environment"])
	}
}

func TestAuthRoutesExist(t *testing.T) {
	backend := setupMockBackend()
	defer backend.Close()

	cfg := newTestConfig()
	cfg.ConfigServiceURL = backend.URL

	gateway := setupGatewayServer(cfg)
	defer gateway.Close()

	routes := []struct {
		method string
		path   string
	}{
		{"POST", "/api/v1/auth/register"},
		{"POST", "/api/v1/auth/login"},
		{"POST", "/api/v1/auth/refresh"},
		{"POST", "/api/v1/auth/logout"},
	}

	client := &http.Client{}
	for _, route := range routes {
		req, _ := http.NewRequest(route.method, gateway.URL+route.path, nil)
		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("%s %s: Request failed: %v", route.method, route.path, err)
		}
		defer func() { _ = resp.Body.Close() }()

		// Route exists and proxies successfully to mock backend (200)
		if resp.StatusCode != 200 {
			t.Errorf("%s %s: Expected status code 200, got %d", route.method, route.path, resp.StatusCode)
		}
	}
}

func TestProtectedRoutesExist(t *testing.T) {
	backend := setupMockBackend()
	defer backend.Close()

	cfg := newTestConfig()
	cfg.ConfigServiceURL = backend.URL
	token := createTestToken(cfg)

	gateway := setupGatewayServer(cfg)
	defer gateway.Close()

	routes := []struct {
		method string
		path   string
	}{
		{"GET", "/api/v1/users/me"},
		{"PUT", "/api/v1/users/me"},
		{"DELETE", "/api/v1/users/me"},
		{"GET", "/api/v1/configs"},
		{"POST", "/api/v1/configs"},
		{"GET", "/api/v1/configs/123"},
		{"PUT", "/api/v1/configs/123"},
		{"DELETE", "/api/v1/configs/123"},
		{"POST", "/api/v1/folders/scan"},
	}

	client := &http.Client{}
	for _, route := range routes {
		req, _ := http.NewRequest(route.method, gateway.URL+route.path, nil)
		req.Header.Set("Authorization", "Bearer "+token)
		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("%s %s: Request failed: %v", route.method, route.path, err)
		}
		defer func() { _ = resp.Body.Close() }()

		// With valid auth, route exists and proxies successfully to mock backend (200)
		if resp.StatusCode != 200 {
			t.Errorf("%s %s: Expected status code 200, got %d", route.method, route.path, resp.StatusCode)
		}
	}
}

func TestProtectedRoutesRequireAuth(t *testing.T) {
	cfg := newTestConfig()
	router := New(cfg)

	routes := []struct {
		method string
		path   string
	}{
		{"GET", "/api/v1/users/me"},
		{"GET", "/api/v1/configs/"},
		{"POST", "/api/v1/ingest/123/start"},
		{"POST", "/api/v1/query"},
		{"POST", "/api/v1/evaluation/evaluate"},
	}

	for _, route := range routes {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest(route.method, route.path, nil)
		// No Authorization header
		router.ServeHTTP(w, req)

		// Should return 401 Unauthorized
		if w.Code != 401 {
			t.Errorf("%s %s: Expected status code 401, got %d", route.method, route.path, w.Code)
		}
	}
}

func TestIngestionRoutesExist(t *testing.T) {
	backend := setupMockBackend()
	defer backend.Close()

	cfg := newTestConfig()
	cfg.IngestionServiceURL = backend.URL
	token := createTestToken(cfg)

	gateway := setupGatewayServer(cfg)
	defer gateway.Close()

	routes := []struct {
		method string
		path   string
	}{
		{"POST", "/api/v1/ingest/123/start"},
		{"GET", "/api/v1/ingest/123/status"},
		{"POST", "/api/v1/ingest/123/cancel"},
		{"POST", "/api/v1/ingest/123/retry"},
		{"GET", "/api/v1/ingest/123/logs"},
		{"GET", "/api/v1/ingest/123/stats"},
	}

	client := &http.Client{}
	for _, route := range routes {
		req, _ := http.NewRequest(route.method, gateway.URL+route.path, nil)
		req.Header.Set("Authorization", "Bearer "+token)
		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("%s %s: Request failed: %v", route.method, route.path, err)
		}
		defer func() { _ = resp.Body.Close() }()

		if resp.StatusCode != 200 {
			t.Errorf("%s %s: Expected status code 200, got %d", route.method, route.path, resp.StatusCode)
		}
	}
}

func TestRAGServiceRoutesExist(t *testing.T) {
	backend := setupMockBackend()
	defer backend.Close()

	cfg := newTestConfig()
	cfg.RAGServiceURL = backend.URL
	token := createTestToken(cfg)

	gateway := setupGatewayServer(cfg)
	defer gateway.Close()

	// Note: /api/v1/stream uses WebSocket handler (P2-8), tested separately
	routes := []struct {
		method string
		path   string
	}{
		{"POST", "/api/v1/query"},
		{"POST", "/api/v1/chat"},
		{"POST", "/api/v1/evaluation/evaluate"},
		{"GET", "/api/v1/evaluation/jev-compare/latest"},
	}

	client := &http.Client{}
	for _, route := range routes {
		req, _ := http.NewRequest(route.method, gateway.URL+route.path, nil)
		req.Header.Set("Authorization", "Bearer "+token)
		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("%s %s: Request failed: %v", route.method, route.path, err)
		}
		defer func() { _ = resp.Body.Close() }()

		if resp.StatusCode != 200 {
			t.Errorf("%s %s: Expected status code 200, got %d", route.method, route.path, resp.StatusCode)
		}
	}
}

func TestWebSocketRouteExists(t *testing.T) {
	backend := setupMockBackend()
	defer backend.Close()

	cfg := newTestConfig()
	cfg.RAGServiceURL = backend.URL
	token := createTestToken(cfg)

	gateway := setupGatewayServer(cfg)
	defer gateway.Close()

	req, _ := http.NewRequest("GET", gateway.URL+"/api/v1/stream", nil)
	req.Header.Set("Authorization", "Bearer "+token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Request failed: %v", err)
	}
	defer func() { _ = resp.Body.Close() }()

	// Stream route proxies to the RAG service over HTTP/SSE in Phase 0.
	if resp.StatusCode != 200 {
		t.Errorf("Expected status code 200, got %d", resp.StatusCode)
	}
}

func TestNotFoundRoute(t *testing.T) {
	cfg := newTestConfig()
	router := New(cfg)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/nonexistent", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status code %d, got %d", http.StatusNotFound, w.Code)
	}
}

func TestCORSHeaders(t *testing.T) {
	cfg := newTestConfig()
	router := New(cfg)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("OPTIONS", "/health", nil)
	req.Header.Set("Origin", "http://localhost:3000")
	router.ServeHTTP(w, req)

	// OPTIONS should return 204
	if w.Code != 204 {
		t.Errorf("Expected status code 204 for OPTIONS, got %d", w.Code)
	}

	// Check CORS headers
	if w.Header().Get("Access-Control-Allow-Origin") != "http://localhost:3000" {
		t.Errorf("Expected Access-Control-Allow-Origin header")
	}
}

func TestProxyBackendUnavailable(t *testing.T) {
	cfg := newTestConfig()
	cfg.ConfigServiceURL = "http://localhost:59999" // Non-existent backend

	gateway := setupGatewayServer(cfg)
	defer gateway.Close()

	resp, err := http.Post(gateway.URL+"/api/v1/auth/login", "application/json", nil)
	if err != nil {
		t.Fatalf("Request failed: %v", err)
	}
	defer func() { _ = resp.Body.Close() }()

	// When backend is down, proxy returns 502
	if resp.StatusCode != 502 {
		t.Errorf("Expected status code 502, got %d", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	var response map[string]interface{}
	if err := json.Unmarshal(body, &response); err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	if response["error"] != "Service unavailable" {
		t.Errorf("Expected 'Service unavailable' error message, got %v", response["error"])
	}
}

func TestProxyForwardsAuthorizationHeader(t *testing.T) {
	backend := setupMockBackend()
	defer backend.Close()

	cfg := newTestConfig()
	cfg.ConfigServiceURL = backend.URL
	token := createTestToken(cfg)

	gateway := setupGatewayServer(cfg)
	defer gateway.Close()

	req, _ := http.NewRequest("GET", gateway.URL+"/api/v1/configs", nil)
	req.Header.Set("Authorization", "Bearer "+token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Request failed: %v", err)
	}
	defer func() { _ = resp.Body.Close() }()

	var response map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode gateway response body: %v", err)
	}

	// Verify authorization header was forwarded to backend
	if response["auth_header"] != "Bearer "+token {
		t.Errorf("Expected authorization header to be forwarded, got %v", response["auth_header"])
	}
	if response["x_user_id"] != "test-user-123" {
		t.Errorf("Expected X-User-ID to be forwarded, got %v", response["x_user_id"])
	}
}

func TestProxyForwardsPathParams(t *testing.T) {
	backend := setupMockBackend()
	defer backend.Close()

	cfg := newTestConfig()
	cfg.ConfigServiceURL = backend.URL
	token := createTestToken(cfg)

	gateway := setupGatewayServer(cfg)
	defer gateway.Close()

	req, _ := http.NewRequest("GET", gateway.URL+"/api/v1/configs/my-config-id", nil)
	req.Header.Set("Authorization", "Bearer "+token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Request failed: %v", err)
	}
	defer func() { _ = resp.Body.Close() }()

	var response map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode gateway response body: %v", err)
	}

	// Verify path was correctly forwarded with parameter
	if response["path"] != "/api/v1/configs/my-config-id" {
		t.Errorf("Expected path '/api/v1/configs/my-config-id', got %v", response["path"])
	}
}

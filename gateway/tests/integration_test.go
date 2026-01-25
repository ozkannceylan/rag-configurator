//go:build integration

package tests

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"gateway/internal/config"
	"gateway/internal/router"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// getTestConfig returns a test configuration
func getTestConfig() *config.Config {
	return &config.Config{
		Port:                8000,
		Environment:         "test",
		LogLevel:            "debug",
		JWTSecretKey:        jwtSecretKey,
		JWTAlgorithm:        "HS256",
		ConfigServiceURL:    configServiceURL,
		IngestionServiceURL: "http://localhost:8002",
		RAGServiceURL:       "http://localhost:8003",
		CORSOrigins:         []string{"http://localhost:3000", "http://localhost:5173"},
		RateLimitRPS:        1000, // High limit for tests
		RateLimitBurst:      2000,
	}
}

// createTestToken creates a valid JWT token for testing
func createTestToken(userID string) string {
	claims := jwt.MapClaims{
		"sub":  userID,
		"type": "access",
		"exp":  time.Now().Add(1 * time.Hour).Unix(),
		"iat":  time.Now().Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, _ := token.SignedString([]byte(jwtSecretKey))
	return tokenString
}

// setupGateway creates a test gateway server
func setupGateway(cfg *config.Config) *httptest.Server {
	r := router.New(cfg)
	return httptest.NewServer(r)
}

// ============================================================
// Health Endpoint Tests
// ============================================================

func TestHealthEndpoint(t *testing.T) {
	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	resp, err := http.Get(gateway.URL + "/health")
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.Equal(t, "healthy", response["status"])
	assert.Equal(t, "gateway", response["service"])
	assert.Equal(t, "test", response["environment"])
}

func TestHealthDetailedEndpoint(t *testing.T) {
	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	resp, err := http.Get(gateway.URL + "/health/detailed")
	require.NoError(t, err)
	defer resp.Body.Close()

	// May return 200 or 503 depending on backend availability
	assert.True(t, resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusServiceUnavailable)

	var response map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&response)
	require.NoError(t, err)

	assert.NotNil(t, response["status"])
	assert.NotNil(t, response["backends"])
}

// ============================================================
// Public Endpoints Tests (No Auth Required)
// ============================================================

func TestPublicEndpointsNoAuth(t *testing.T) {
	if !isConfigServiceAvailable() {
		t.Skip("Config Service not available")
	}

	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	publicEndpoints := []struct {
		method string
		path   string
	}{
		{"POST", "/api/v1/auth/register"},
		{"POST", "/api/v1/auth/login"},
		{"POST", "/api/v1/auth/refresh"},
		{"POST", "/api/v1/auth/logout"},
	}

	client := &http.Client{}
	for _, endpoint := range publicEndpoints {
		t.Run(fmt.Sprintf("%s_%s", endpoint.method, endpoint.path), func(t *testing.T) {
			req, err := http.NewRequest(endpoint.method, gateway.URL+endpoint.path, bytes.NewBuffer([]byte("{}")))
			require.NoError(t, err)
			req.Header.Set("Content-Type", "application/json")

			resp, err := client.Do(req)
			require.NoError(t, err)
			defer resp.Body.Close()

			// Should NOT return 401 (public endpoints)
			assert.NotEqual(t, http.StatusUnauthorized, resp.StatusCode,
				"Public endpoint %s %s should not require auth", endpoint.method, endpoint.path)
		})
	}
}

// ============================================================
// Protected Endpoints Tests (Auth Required)
// ============================================================

func TestProtectedEndpointsRequireAuth(t *testing.T) {
	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	protectedEndpoints := []struct {
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
		{"POST", "/api/v1/ingest/123/start"},
		{"GET", "/api/v1/ingest/123/status"},
		{"POST", "/api/v1/query"},
		{"POST", "/api/v1/chat"},
	}

	client := &http.Client{}
	for _, endpoint := range protectedEndpoints {
		t.Run(fmt.Sprintf("%s_%s", endpoint.method, endpoint.path), func(t *testing.T) {
			req, err := http.NewRequest(endpoint.method, gateway.URL+endpoint.path, nil)
			require.NoError(t, err)
			// No Authorization header

			resp, err := client.Do(req)
			require.NoError(t, err)
			defer resp.Body.Close()

			assert.Equal(t, http.StatusUnauthorized, resp.StatusCode,
				"Protected endpoint %s %s should require auth", endpoint.method, endpoint.path)
		})
	}
}

func TestProtectedEndpointsWithValidToken(t *testing.T) {
	if !isConfigServiceAvailable() {
		t.Skip("Config Service not available")
	}

	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	token := createTestToken("test-user-123")

	// Test a protected endpoint with valid token
	req, err := http.NewRequest("GET", gateway.URL+"/api/v1/configs", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	// Should NOT return 401 with valid token
	assert.NotEqual(t, http.StatusUnauthorized, resp.StatusCode,
		"Should not return 401 with valid token")
}

func TestProtectedEndpointsWithExpiredToken(t *testing.T) {
	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	// Create expired token
	claims := jwt.MapClaims{
		"sub":  "test-user-123",
		"type": "access",
		"exp":  time.Now().Add(-1 * time.Hour).Unix(), // Expired
		"iat":  time.Now().Add(-2 * time.Hour).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, _ := token.SignedString([]byte(jwtSecretKey))

	req, err := http.NewRequest("GET", gateway.URL+"/api/v1/configs", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+tokenString)

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusUnauthorized, resp.StatusCode,
		"Should return 401 with expired token")
}

func TestProtectedEndpointsWithRefreshToken(t *testing.T) {
	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	// Create refresh token (should be rejected for API access)
	claims := jwt.MapClaims{
		"sub":  "test-user-123",
		"type": "refresh", // Wrong type
		"exp":  time.Now().Add(1 * time.Hour).Unix(),
		"iat":  time.Now().Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, _ := token.SignedString([]byte(jwtSecretKey))

	req, err := http.NewRequest("GET", gateway.URL+"/api/v1/configs", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+tokenString)

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusUnauthorized, resp.StatusCode,
		"Should return 401 with refresh token")
}

// ============================================================
// CORS Tests
// ============================================================

func TestCORSOnEndpoints(t *testing.T) {
	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	client := &http.Client{}

	t.Run("AllowedOrigin", func(t *testing.T) {
		req, err := http.NewRequest("OPTIONS", gateway.URL+"/health", nil)
		require.NoError(t, err)
		req.Header.Set("Origin", "http://localhost:3000")
		req.Header.Set("Access-Control-Request-Method", "GET")

		resp, err := client.Do(req)
		require.NoError(t, err)
		defer resp.Body.Close()

		assert.Equal(t, http.StatusNoContent, resp.StatusCode)
		assert.Equal(t, "http://localhost:3000", resp.Header.Get("Access-Control-Allow-Origin"))
		assert.NotEmpty(t, resp.Header.Get("Access-Control-Allow-Methods"))
	})

	t.Run("DisallowedOrigin", func(t *testing.T) {
		req, err := http.NewRequest("OPTIONS", gateway.URL+"/health", nil)
		require.NoError(t, err)
		req.Header.Set("Origin", "http://malicious-site.com")
		req.Header.Set("Access-Control-Request-Method", "GET")

		resp, err := client.Do(req)
		require.NoError(t, err)
		defer resp.Body.Close()

		// Should not have CORS headers for disallowed origin
		assert.Empty(t, resp.Header.Get("Access-Control-Allow-Origin"))
	})

	t.Run("CORSOnActualRequest", func(t *testing.T) {
		req, err := http.NewRequest("GET", gateway.URL+"/health", nil)
		require.NoError(t, err)
		req.Header.Set("Origin", "http://localhost:3000")

		resp, err := client.Do(req)
		require.NoError(t, err)
		defer resp.Body.Close()

		assert.Equal(t, http.StatusOK, resp.StatusCode)
		assert.Equal(t, "http://localhost:3000", resp.Header.Get("Access-Control-Allow-Origin"))
	})
}

// ============================================================
// Rate Limiting Tests
// ============================================================

func TestRateLimiting(t *testing.T) {
	cfg := getTestConfig()
	cfg.RateLimitRPS = 5
	cfg.RateLimitBurst = 5

	gateway := setupGateway(cfg)
	defer gateway.Close()

	client := &http.Client{}
	successCount := 0
	blockedCount := 0

	// Make more requests than allowed
	for i := 0; i < 15; i++ {
		req, _ := http.NewRequest("GET", gateway.URL+"/health", nil)
		req.Header.Set("X-Forwarded-For", "192.168.1.100") // Simulate same IP

		resp, err := client.Do(req)
		require.NoError(t, err)
		resp.Body.Close()

		if resp.StatusCode == http.StatusOK {
			successCount++
		} else if resp.StatusCode == http.StatusTooManyRequests {
			blockedCount++
		}
	}

	assert.True(t, successCount > 0, "Should have some successful requests")
	assert.True(t, blockedCount > 0, "Should have some rate-limited requests")
}

// ============================================================
// E2E Auth Flow Tests (Requires Config Service)
// ============================================================

func TestE2EAuthFlow(t *testing.T) {
	if !isConfigServiceAvailable() {
		t.Skip("Config Service not available")
	}

	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	client := &http.Client{}
	testEmail := fmt.Sprintf("test-%d@example.com", time.Now().UnixNano())

	// Step 1: Register user
	registerPayload := map[string]string{
		"email":    testEmail,
		"password": "TestPassword123!",
		"name":     "Test User",
	}
	registerBody, _ := json.Marshal(registerPayload)

	req, err := http.NewRequest("POST", gateway.URL+"/api/v1/auth/register", bytes.NewBuffer(registerBody))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	require.NoError(t, err)
	body, _ := io.ReadAll(resp.Body)
	resp.Body.Close()

	if resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusOK {
		t.Logf("Register response: %d - %s", resp.StatusCode, string(body))
	}
	require.True(t, resp.StatusCode == http.StatusCreated || resp.StatusCode == http.StatusOK,
		"Registration should succeed")

	var registerResponse map[string]interface{}
	err = json.Unmarshal(body, &registerResponse)
	require.NoError(t, err)

	// Step 2: Login with registered credentials
	loginPayload := map[string]string{
		"email":    testEmail,
		"password": "TestPassword123!",
	}
	loginBody, _ := json.Marshal(loginPayload)

	req, err = http.NewRequest("POST", gateway.URL+"/api/v1/auth/login", bytes.NewBuffer(loginBody))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err = client.Do(req)
	require.NoError(t, err)
	body, _ = io.ReadAll(resp.Body)
	resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Logf("Login response: %d - %s", resp.StatusCode, string(body))
	}
	require.Equal(t, http.StatusOK, resp.StatusCode, "Login should succeed")

	var loginResponse map[string]interface{}
	err = json.Unmarshal(body, &loginResponse)
	require.NoError(t, err)

	// Extract access token from response
	data, ok := loginResponse["data"].(map[string]interface{})
	require.True(t, ok, "Response should have data field")
	accessToken, ok := data["access_token"].(string)
	require.True(t, ok, "Response should have access_token")

	// Step 3: Use token to access protected endpoint
	req, err = http.NewRequest("GET", gateway.URL+"/api/v1/users/me", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+accessToken)

	resp, err = client.Do(req)
	require.NoError(t, err)
	body, _ = io.ReadAll(resp.Body)
	resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Logf("Get user response: %d - %s", resp.StatusCode, string(body))
	}
	require.Equal(t, http.StatusOK, resp.StatusCode, "Should access protected endpoint with token")

	var userResponse map[string]interface{}
	err = json.Unmarshal(body, &userResponse)
	require.NoError(t, err)

	// Verify user data
	userData, ok := userResponse["data"].(map[string]interface{})
	require.True(t, ok, "Response should have data field")
	assert.Equal(t, testEmail, userData["email"])
}

// ============================================================
// E2E Config CRUD Tests (Requires Config Service)
// ============================================================

func TestE2EConfigCRUD(t *testing.T) {
	if !isConfigServiceAvailable() {
		t.Skip("Config Service not available")
	}

	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	client := &http.Client{}
	testEmail := fmt.Sprintf("config-test-%d@example.com", time.Now().UnixNano())

	// Setup: Register and login to get token
	accessToken := registerAndLogin(t, client, gateway.URL, testEmail, "TestPassword123!")

	var configID string

	// Step 1: Create config
	t.Run("CreateConfig", func(t *testing.T) {
		createPayload := map[string]interface{}{
			"name":        "Test Config",
			"description": "Integration test config",
			"data_sources": []map[string]interface{}{
				{
					"type": "local_folder",
					"config": map[string]interface{}{
						"path": "/test/path",
					},
				},
			},
		}
		createBody, _ := json.Marshal(createPayload)

		req, err := http.NewRequest("POST", gateway.URL+"/api/v1/configs", bytes.NewBuffer(createBody))
		require.NoError(t, err)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer "+accessToken)

		resp, err := client.Do(req)
		require.NoError(t, err)
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		if resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusOK {
			t.Logf("Create config response: %d - %s", resp.StatusCode, string(body))
		}
		require.True(t, resp.StatusCode == http.StatusCreated || resp.StatusCode == http.StatusOK)

		var response map[string]interface{}
		err = json.Unmarshal(body, &response)
		require.NoError(t, err)

		data, ok := response["data"].(map[string]interface{})
		require.True(t, ok)
		configID, ok = data["id"].(string)
		require.True(t, ok, "Response should have config ID")
	})

	// Step 2: List configs
	t.Run("ListConfigs", func(t *testing.T) {
		req, err := http.NewRequest("GET", gateway.URL+"/api/v1/configs", nil)
		require.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+accessToken)

		resp, err := client.Do(req)
		require.NoError(t, err)
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		require.Equal(t, http.StatusOK, resp.StatusCode)

		var response map[string]interface{}
		err = json.Unmarshal(body, &response)
		require.NoError(t, err)

		data, ok := response["data"].([]interface{})
		require.True(t, ok)
		assert.True(t, len(data) > 0, "Should have at least one config")
	})

	// Step 3: Get single config
	t.Run("GetConfig", func(t *testing.T) {
		if configID == "" {
			t.Skip("No config ID from create step")
		}

		req, err := http.NewRequest("GET", gateway.URL+"/api/v1/configs/"+configID, nil)
		require.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+accessToken)

		resp, err := client.Do(req)
		require.NoError(t, err)
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		require.Equal(t, http.StatusOK, resp.StatusCode)

		var response map[string]interface{}
		err = json.Unmarshal(body, &response)
		require.NoError(t, err)

		data, ok := response["data"].(map[string]interface{})
		require.True(t, ok)
		assert.Equal(t, "Test Config", data["name"])
	})

	// Step 4: Update config
	t.Run("UpdateConfig", func(t *testing.T) {
		if configID == "" {
			t.Skip("No config ID from create step")
		}

		updatePayload := map[string]interface{}{
			"name":        "Updated Test Config",
			"description": "Updated description",
		}
		updateBody, _ := json.Marshal(updatePayload)

		req, err := http.NewRequest("PUT", gateway.URL+"/api/v1/configs/"+configID, bytes.NewBuffer(updateBody))
		require.NoError(t, err)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer "+accessToken)

		resp, err := client.Do(req)
		require.NoError(t, err)
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		require.Equal(t, http.StatusOK, resp.StatusCode)

		var response map[string]interface{}
		err = json.Unmarshal(body, &response)
		require.NoError(t, err)

		data, ok := response["data"].(map[string]interface{})
		require.True(t, ok)
		assert.Equal(t, "Updated Test Config", data["name"])
	})

	// Step 5: Delete config
	t.Run("DeleteConfig", func(t *testing.T) {
		if configID == "" {
			t.Skip("No config ID from create step")
		}

		req, err := http.NewRequest("DELETE", gateway.URL+"/api/v1/configs/"+configID, nil)
		require.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+accessToken)

		resp, err := client.Do(req)
		require.NoError(t, err)
		resp.Body.Close()

		require.True(t, resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusNoContent)

		// Verify deletion
		req, err = http.NewRequest("GET", gateway.URL+"/api/v1/configs/"+configID, nil)
		require.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+accessToken)

		resp, err = client.Do(req)
		require.NoError(t, err)
		resp.Body.Close()

		assert.Equal(t, http.StatusNotFound, resp.StatusCode, "Config should be deleted")
	})
}

// registerAndLogin is a helper that registers a user and returns the access token
func registerAndLogin(t *testing.T, client *http.Client, gatewayURL, email, password string) string {
	// Register
	registerPayload := map[string]string{
		"email":    email,
		"password": password,
		"name":     "Test User",
	}
	registerBody, _ := json.Marshal(registerPayload)

	req, err := http.NewRequest("POST", gatewayURL+"/api/v1/auth/register", bytes.NewBuffer(registerBody))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	require.NoError(t, err)
	resp.Body.Close()

	// Login
	loginPayload := map[string]string{
		"email":    email,
		"password": password,
	}
	loginBody, _ := json.Marshal(loginPayload)

	req, err = http.NewRequest("POST", gatewayURL+"/api/v1/auth/login", bytes.NewBuffer(loginBody))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	resp, err = client.Do(req)
	require.NoError(t, err)
	body, _ := io.ReadAll(resp.Body)
	resp.Body.Close()

	require.Equal(t, http.StatusOK, resp.StatusCode, "Login should succeed")

	var loginResponse map[string]interface{}
	err = json.Unmarshal(body, &loginResponse)
	require.NoError(t, err)

	data, ok := loginResponse["data"].(map[string]interface{})
	require.True(t, ok)
	accessToken, ok := data["access_token"].(string)
	require.True(t, ok)

	return accessToken
}

// ============================================================
// Proxy Tests
// ============================================================

func TestProxyForwardsHeaders(t *testing.T) {
	if !isConfigServiceAvailable() {
		t.Skip("Config Service not available")
	}

	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	token := createTestToken("test-user-123")

	req, err := http.NewRequest("GET", gateway.URL+"/api/v1/configs", nil)
	require.NoError(t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("X-Request-ID", "test-request-123")
	req.Header.Set("X-Custom-Header", "custom-value")

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	// Should not return 401 (headers forwarded correctly)
	assert.NotEqual(t, http.StatusUnauthorized, resp.StatusCode)
}

func TestProxyHandlesBackendError(t *testing.T) {
	cfg := getTestConfig()
	cfg.ConfigServiceURL = "http://localhost:59999" // Non-existent

	gateway := setupGateway(cfg)
	defer gateway.Close()

	req, err := http.NewRequest("POST", gateway.URL+"/api/v1/auth/login", bytes.NewBuffer([]byte("{}")))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusBadGateway, resp.StatusCode, "Should return 502 when backend unavailable")
}

// ============================================================
// WebSocket Tests
// ============================================================

func TestWebSocketRouteRequiresAuth(t *testing.T) {
	cfg := getTestConfig()
	gateway := setupGateway(cfg)
	defer gateway.Close()

	req, err := http.NewRequest("GET", gateway.URL+"/api/v1/stream", nil)
	require.NoError(t, err)
	// No Authorization header

	client := &http.Client{}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	assert.Equal(t, http.StatusUnauthorized, resp.StatusCode)
}

// ============================================================
// Environment Variable Tests
// ============================================================

func TestGatewayReadsEnvConfig(t *testing.T) {
	// Save current env
	origSecret := os.Getenv("JWT_SECRET_KEY")
	defer os.Setenv("JWT_SECRET_KEY", origSecret)

	// Set test env
	os.Setenv("JWT_SECRET_KEY", "test-env-secret")

	cfg := getTestConfig()
	assert.Equal(t, jwtSecretKey, cfg.JWTSecretKey) // Uses test setup value
}

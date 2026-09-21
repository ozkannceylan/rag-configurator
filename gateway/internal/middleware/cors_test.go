package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func setupCORSRouter(allowedOrigins []string) *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(CORS(allowedOrigins))
	r.GET("/test", func(c *gin.Context) {
		c.JSON(200, gin.H{"message": "ok"})
	})
	r.POST("/test", func(c *gin.Context) {
		c.JSON(200, gin.H{"message": "ok"})
	})
	return r
}

func TestCORS_AllowedOrigin(t *testing.T) {
	allowedOrigins := []string{"http://localhost:3000", "http://localhost:3001"}
	router := setupCORSRouter(allowedOrigins)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Origin", "http://localhost:3000")
	router.ServeHTTP(w, req)

	assert.Equal(t, 200, w.Code)
	assert.Equal(t, "http://localhost:3000", w.Header().Get("Access-Control-Allow-Origin"))
	assert.Equal(t, "GET, POST, PUT, PATCH, DELETE, OPTIONS", w.Header().Get("Access-Control-Allow-Methods"))
	assert.Equal(t, "Authorization, Content-Type, Accept, Origin, X-Requested-With", w.Header().Get("Access-Control-Allow-Headers"))
	assert.Equal(t, "Content-Length, Content-Type", w.Header().Get("Access-Control-Expose-Headers"))
	assert.Equal(t, "true", w.Header().Get("Access-Control-Allow-Credentials"))
	assert.Equal(t, "86400", w.Header().Get("Access-Control-Max-Age"))
}

func TestCORS_DisallowedOrigin(t *testing.T) {
	allowedOrigins := []string{"http://localhost:3000"}
	router := setupCORSRouter(allowedOrigins)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Origin", "http://evil.com")
	router.ServeHTTP(w, req)

	// Request still succeeds (server-side), but no CORS headers
	assert.Equal(t, 200, w.Code)
	assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
	assert.Empty(t, w.Header().Get("Access-Control-Allow-Methods"))
	assert.Empty(t, w.Header().Get("Access-Control-Allow-Credentials"))
}

func TestCORS_PreflightRequest(t *testing.T) {
	allowedOrigins := []string{"http://localhost:3000"}
	router := setupCORSRouter(allowedOrigins)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("OPTIONS", "/test", nil)
	req.Header.Set("Origin", "http://localhost:3000")
	req.Header.Set("Access-Control-Request-Method", "POST")
	req.Header.Set("Access-Control-Request-Headers", "Authorization, Content-Type")
	router.ServeHTTP(w, req)

	assert.Equal(t, 204, w.Code)
	assert.Equal(t, "http://localhost:3000", w.Header().Get("Access-Control-Allow-Origin"))
	assert.Equal(t, "GET, POST, PUT, PATCH, DELETE, OPTIONS", w.Header().Get("Access-Control-Allow-Methods"))
	assert.Equal(t, "Authorization, Content-Type, Accept, Origin, X-Requested-With", w.Header().Get("Access-Control-Allow-Headers"))
	assert.Equal(t, "true", w.Header().Get("Access-Control-Allow-Credentials"))
	assert.Equal(t, "86400", w.Header().Get("Access-Control-Max-Age"))
}

func TestCORS_PreflightDisallowedOrigin(t *testing.T) {
	allowedOrigins := []string{"http://localhost:3000"}
	router := setupCORSRouter(allowedOrigins)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("OPTIONS", "/test", nil)
	req.Header.Set("Origin", "http://evil.com")
	req.Header.Set("Access-Control-Request-Method", "POST")
	router.ServeHTTP(w, req)

	// OPTIONS still returns 204, but no CORS headers for disallowed origin
	assert.Equal(t, 204, w.Code)
	assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
}

func TestCORS_WildcardOrigin(t *testing.T) {
	allowedOrigins := []string{"*"}
	router := setupCORSRouter(allowedOrigins)

	testCases := []string{
		"http://localhost:3000",
		"http://example.com",
		"https://any-domain.org",
	}

	for _, origin := range testCases {
		t.Run(origin, func(t *testing.T) {
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("GET", "/test", nil)
			req.Header.Set("Origin", origin)
			router.ServeHTTP(w, req)

			assert.Equal(t, 200, w.Code)
			assert.Equal(t, origin, w.Header().Get("Access-Control-Allow-Origin"))
		})
	}
}

func TestCORS_NoOriginHeader(t *testing.T) {
	allowedOrigins := []string{"http://localhost:3000"}
	router := setupCORSRouter(allowedOrigins)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	// No Origin header set
	router.ServeHTTP(w, req)

	// Request passes through, no CORS headers
	assert.Equal(t, 200, w.Code)
	assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
}

func TestCORS_SubdomainWildcard(t *testing.T) {
	allowedOrigins := []string{"*.example.com"}
	router := setupCORSRouter(allowedOrigins)

	testCases := []struct {
		origin  string
		allowed bool
	}{
		{"http://app.example.com", true},
		{"https://api.example.com", true},
		{"http://sub.domain.example.com", true},
		{"http://example.com", false},          // Root domain not matched by *.example.com
		{"http://notexample.com", false},       // Different domain
		{"http://app.other.com", false},        // Different domain
		{"http://example.com.evil.com", false}, // Shouldn't match
	}

	for _, tc := range testCases {
		t.Run(tc.origin, func(t *testing.T) {
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("GET", "/test", nil)
			req.Header.Set("Origin", tc.origin)
			router.ServeHTTP(w, req)

			if tc.allowed {
				assert.Equal(t, tc.origin, w.Header().Get("Access-Control-Allow-Origin"))
			} else {
				assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
			}
		})
	}
}

func TestCORS_MultipleAllowedOrigins(t *testing.T) {
	allowedOrigins := []string{
		"http://localhost:3000",
		"http://localhost:3001",
		"https://app.example.com",
	}
	router := setupCORSRouter(allowedOrigins)

	for _, origin := range allowedOrigins {
		t.Run(origin, func(t *testing.T) {
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("GET", "/test", nil)
			req.Header.Set("Origin", origin)
			router.ServeHTTP(w, req)

			assert.Equal(t, 200, w.Code)
			assert.Equal(t, origin, w.Header().Get("Access-Control-Allow-Origin"))
		})
	}
}

func TestCORS_OriginWithPort(t *testing.T) {
	allowedOrigins := []string{"http://localhost:3000"}
	router := setupCORSRouter(allowedOrigins)

	// Exact match with port
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Origin", "http://localhost:3000")
	router.ServeHTTP(w, req)

	assert.Equal(t, "http://localhost:3000", w.Header().Get("Access-Control-Allow-Origin"))

	// Different port should not match
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/test", nil)
	req.Header.Set("Origin", "http://localhost:4000")
	router.ServeHTTP(w, req)

	assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
}

func TestIsOriginAllowed(t *testing.T) {
	tests := []struct {
		name           string
		origin         string
		allowedOrigins []string
		expected       bool
	}{
		{"exact match", "http://localhost:3000", []string{"http://localhost:3000"}, true},
		{"no match", "http://localhost:3000", []string{"http://localhost:4000"}, false},
		{"wildcard", "http://any.domain.com", []string{"*"}, true},
		{"subdomain wildcard match", "http://app.example.com", []string{"*.example.com"}, true},
		{"subdomain wildcard no match", "http://example.com", []string{"*.example.com"}, false},
		{"empty origins", "http://localhost:3000", []string{}, false},
		{"multiple origins first match", "http://localhost:3000", []string{"http://localhost:3000", "http://localhost:3001"}, true},
		{"multiple origins second match", "http://localhost:3001", []string{"http://localhost:3000", "http://localhost:3001"}, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := isOriginAllowed(tt.origin, tt.allowedOrigins)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestExtractHost(t *testing.T) {
	tests := []struct {
		origin   string
		expected string
	}{
		{"http://example.com", "example.com"},
		{"https://example.com", "example.com"},
		{"http://example.com:3000", "example.com"},
		{"https://app.example.com:443", "app.example.com"},
		{"http://sub.domain.example.com", "sub.domain.example.com"},
		{"http://localhost:3000", "localhost"},
		{"http://127.0.0.1:8080", "127.0.0.1"},
	}

	for _, tt := range tests {
		t.Run(tt.origin, func(t *testing.T) {
			result := extractHost(tt.origin)
			assert.Equal(t, tt.expected, result)
		})
	}
}

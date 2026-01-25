package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
)

const testSecret = "test-secret-key-for-testing"

func createTestToken(userID string, tokenType string, expired bool) string {
	var exp time.Time
	if expired {
		exp = time.Now().Add(-1 * time.Hour)
	} else {
		exp = time.Now().Add(1 * time.Hour)
	}

	claims := jwt.MapClaims{
		"sub":  userID,
		"type": tokenType,
		"exp":  exp.Unix(),
		"iat":  time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, _ := token.SignedString([]byte(testSecret))
	return tokenString
}

func setupRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(Auth(testSecret, "HS256"))
	r.GET("/test", func(c *gin.Context) {
		userID := GetUserID(c)
		c.JSON(200, gin.H{"user_id": userID})
	})
	return r
}

func TestAuth_ValidToken(t *testing.T) {
	router := setupRouter()
	token := createTestToken("user123", "access", false)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	router.ServeHTTP(w, req)

	assert.Equal(t, 200, w.Code)
	assert.Contains(t, w.Body.String(), "user123")
}

func TestAuth_MissingHeader(t *testing.T) {
	router := setupRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	router.ServeHTTP(w, req)

	assert.Equal(t, 401, w.Code)
	assert.Contains(t, w.Body.String(), "Authorization header is required")
}

func TestAuth_ExpiredToken(t *testing.T) {
	router := setupRouter()
	token := createTestToken("user123", "access", true)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	router.ServeHTTP(w, req)

	assert.Equal(t, 401, w.Code)
	assert.Contains(t, w.Body.String(), "expired")
}

func TestAuth_RefreshToken(t *testing.T) {
	router := setupRouter()
	token := createTestToken("user123", "refresh", false) // refresh instead of access

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	router.ServeHTTP(w, req)

	assert.Equal(t, 401, w.Code)
	assert.Contains(t, w.Body.String(), "Invalid token type")
}

func TestAuth_InvalidToken(t *testing.T) {
	router := setupRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer invalid.token.here")
	router.ServeHTTP(w, req)

	assert.Equal(t, 401, w.Code)
}

func TestAuth_MalformedAuthHeader(t *testing.T) {
	router := setupRouter()

	tests := []struct {
		name   string
		header string
	}{
		{"no bearer prefix", "token123"},
		{"basic auth", "Basic dXNlcjpwYXNz"},
		{"empty token", "Bearer "},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("GET", "/test", nil)
			req.Header.Set("Authorization", tt.header)
			router.ServeHTTP(w, req)

			assert.Equal(t, 401, w.Code)
		})
	}
}

func TestGetUserID_NotSet(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	userID := GetUserID(c)

	assert.Equal(t, "", userID)
}

func TestGetUserID_WrongType(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Set(ContextKeyUserID, 12345) // wrong type (int instead of string)

	userID := GetUserID(c)

	assert.Equal(t, "", userID)
}

package jwt

import (
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const testSecret = "test-secret-key-for-testing"

// createTestToken creates a token matching Phase 1 format
func createTestToken(userID string, tokenType string, expired bool) string {
	var exp time.Time
	if expired {
		exp = time.Now().Add(-1 * time.Hour)
	} else {
		exp = time.Now().Add(1 * time.Hour)
	}

	claims := &Claims{
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   userID,
			ExpiresAt: jwt.NewNumericDate(exp),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
		},
		Type: tokenType,
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, _ := token.SignedString([]byte(testSecret))
	return tokenString
}

func TestValidateAccessToken_Valid(t *testing.T) {
	validator := NewValidator(testSecret, "HS256")
	token := createTestToken("user123", "access", false)

	userID, err := validator.ValidateAccessToken(token)

	require.NoError(t, err)
	assert.Equal(t, "user123", userID)
}

func TestValidateAccessToken_Expired(t *testing.T) {
	validator := NewValidator(testSecret, "HS256")
	token := createTestToken("user123", "access", true)

	_, err := validator.ValidateAccessToken(token)

	assert.ErrorIs(t, err, ErrExpiredToken)
}

func TestValidateAccessToken_RefreshToken(t *testing.T) {
	validator := NewValidator(testSecret, "HS256")
	token := createTestToken("user123", "refresh", false)

	_, err := validator.ValidateAccessToken(token)

	assert.ErrorIs(t, err, ErrInvalidTokenType)
}

func TestValidateAccessToken_WrongSecret(t *testing.T) {
	validator := NewValidator("wrong-secret", "HS256")
	token := createTestToken("user123", "access", false)

	_, err := validator.ValidateAccessToken(token)

	assert.Error(t, err)
}

func TestValidateAccessToken_InvalidToken(t *testing.T) {
	validator := NewValidator(testSecret, "HS256")

	_, err := validator.ValidateAccessToken("invalid.token.here")

	assert.Error(t, err)
}

func TestExtractBearerToken(t *testing.T) {
	tests := []struct {
		name      string
		header    string
		want      string
		wantError bool
	}{
		{"valid", "Bearer abc123", "abc123", false},
		{"valid with extra spaces", "Bearer   abc123  ", "abc123", false},
		{"lowercase bearer", "bearer abc123", "abc123", false},
		{"empty header", "", "", true},
		{"no bearer prefix", "abc123", "", true},
		{"only bearer", "Bearer", "", true},
		{"bearer with empty token", "Bearer ", "", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ExtractBearerToken(tt.header)
			if tt.wantError {
				assert.Error(t, err)
			} else {
				require.NoError(t, err)
				assert.Equal(t, tt.want, got)
			}
		})
	}
}

func TestNewValidator_Algorithms(t *testing.T) {
	tests := []struct {
		algorithm string
		expected  string
	}{
		{"HS256", "HS256"},
		{"HS384", "HS384"},
		{"HS512", "HS512"},
		{"hs256", "HS256"},   // lowercase
		{"invalid", "HS256"}, // defaults to HS256
	}

	for _, tt := range tests {
		t.Run(tt.algorithm, func(t *testing.T) {
			validator := NewValidator(testSecret, tt.algorithm)
			assert.Equal(t, tt.expected, validator.algorithm.Alg())
		})
	}
}

func TestValidateAccessToken_MissingSubject(t *testing.T) {
	validator := NewValidator(testSecret, "HS256")

	// Create token without subject
	claims := &Claims{
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(1 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
		},
		Type: "access",
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, _ := token.SignedString([]byte(testSecret))

	_, err := validator.ValidateAccessToken(tokenString)

	assert.ErrorIs(t, err, ErrMissingClaims)
}

package jwt

import (
	"errors"
	"fmt"
	"strings"

	"github.com/golang-jwt/jwt/v5"
)

// Common errors
var (
	ErrInvalidToken     = errors.New("invalid token")
	ErrExpiredToken     = errors.New("token has expired")
	ErrInvalidTokenType = errors.New("invalid token type")
	ErrMissingClaims    = errors.New("missing required claims")
)

// Claims represents the JWT claims structure from Phase 1
type Claims struct {
	jwt.RegisteredClaims
	Type string `json:"type"`
}

// Validator handles JWT validation
type Validator struct {
	secretKey []byte
	algorithm jwt.SigningMethod
}

// NewValidator creates a new JWT validator
func NewValidator(secretKey string, algorithm string) *Validator {
	var signingMethod jwt.SigningMethod
	switch strings.ToUpper(algorithm) {
	case "HS384":
		signingMethod = jwt.SigningMethodHS384
	case "HS512":
		signingMethod = jwt.SigningMethodHS512
	default:
		signingMethod = jwt.SigningMethodHS256
	}

	return &Validator{
		secretKey: []byte(secretKey),
		algorithm: signingMethod,
	}
}

// ValidateAccessToken validates a JWT access token and returns the user ID
func (v *Validator) ValidateAccessToken(tokenString string) (string, error) {
	// Parse token with claims
	token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		// Verify signing method
		if token.Method.Alg() != v.algorithm.Alg() {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return v.secretKey, nil
	})

	if err != nil {
		// Check for specific errors
		if errors.Is(err, jwt.ErrTokenExpired) {
			return "", ErrExpiredToken
		}
		return "", fmt.Errorf("%w: %v", ErrInvalidToken, err)
	}

	// Extract claims
	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return "", ErrInvalidToken
	}

	// Validate token type - must be "access" (not "refresh")
	if claims.Type != "access" {
		return "", ErrInvalidTokenType
	}

	// Get user ID from subject claim
	userID := claims.Subject
	if userID == "" {
		return "", ErrMissingClaims
	}

	return userID, nil
}

// ExtractBearerToken extracts token from "Bearer <token>" format
func ExtractBearerToken(authHeader string) (string, error) {
	if authHeader == "" {
		return "", errors.New("authorization header is empty")
	}

	parts := strings.SplitN(authHeader, " ", 2)
	if len(parts) != 2 {
		return "", errors.New("authorization header format must be 'Bearer <token>'")
	}

	if !strings.EqualFold(parts[0], "Bearer") {
		return "", errors.New("authorization header must start with 'Bearer'")
	}

	token := strings.TrimSpace(parts[1])
	if token == "" {
		return "", errors.New("token is empty")
	}

	return token, nil
}

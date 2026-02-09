package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"

	"gateway/pkg/jwt"
)

const (
	// ContextKeyUserID is the key for user ID in Gin context
	ContextKeyUserID = "user_id"
)

// Auth returns a middleware that validates JWT access tokens
func Auth(secretKey string, algorithm string) gin.HandlerFunc {
	validator := jwt.NewValidator(secretKey, algorithm)

	return func(c *gin.Context) {
		// Get Authorization header
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			// Support query parameter token for SSE/EventSource (can't set headers)
			if token := c.Query("token"); token != "" {
				authHeader = "Bearer " + token
			} else {
				log.Debug().Msg("Missing Authorization header")
				abortWithAuthError(c, "Authorization header is required")
				return
			}
		}

		// Extract bearer token
		tokenString, err := jwt.ExtractBearerToken(authHeader)
		if err != nil {
			log.Debug().Err(err).Msg("Failed to extract bearer token")
			abortWithAuthError(c, err.Error())
			return
		}

		// Validate token
		userID, err := validator.ValidateAccessToken(tokenString)
		if err != nil {
			log.Debug().Err(err).Msg("Token validation failed")

			// Return appropriate error message
			switch err {
			case jwt.ErrExpiredToken:
				abortWithAuthError(c, "Token has expired")
			case jwt.ErrInvalidTokenType:
				abortWithAuthError(c, "Invalid token type - access token required")
			case jwt.ErrMissingClaims:
				abortWithAuthError(c, "Token is missing required claims")
			default:
				abortWithAuthError(c, "Invalid or malformed token")
			}
			return
		}

		// Store user ID in context for downstream handlers
		c.Set(ContextKeyUserID, userID)

		log.Debug().
			Str("user_id", userID).
			Str("path", c.Request.URL.Path).
			Msg("Request authenticated")

		c.Next()
	}
}

// abortWithAuthError stops the request with a 401 Unauthorized response
func abortWithAuthError(c *gin.Context, message string) {
	c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
		"error":   "Unauthorized",
		"message": message,
	})
}

// GetUserID retrieves the user ID from the Gin context
// Returns empty string if not found (useful for optional auth scenarios)
func GetUserID(c *gin.Context) string {
	if userID, exists := c.Get(ContextKeyUserID); exists {
		if id, ok := userID.(string); ok {
			return id
		}
	}
	return ""
}

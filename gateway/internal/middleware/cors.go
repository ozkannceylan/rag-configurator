package middleware

import (
	"strings"

	"github.com/gin-gonic/gin"
)

// CORS returns a middleware that handles Cross-Origin Resource Sharing
func CORS(allowedOrigins []string) gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")

		// Requests without Origin header pass through unchanged
		if origin == "" {
			c.Next()
			return
		}

		// Check if origin is allowed
		if isOriginAllowed(origin, allowedOrigins) {
			// Set CORS headers for allowed origins
			c.Header("Access-Control-Allow-Origin", origin)
			c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
			c.Header("Access-Control-Allow-Headers", "Authorization, Content-Type, Accept, Origin, X-Requested-With")
			c.Header("Access-Control-Expose-Headers", "Content-Length, Content-Type")
			c.Header("Access-Control-Allow-Credentials", "true")
			c.Header("Access-Control-Max-Age", "86400")
		}

		// Handle preflight OPTIONS requests
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}

// isOriginAllowed checks if the given origin is in the allowed list
// Supports:
// - Exact match: "http://localhost:3000"
// - Wildcard: "*" (allows any origin)
// - Subdomain wildcard: "*.example.com" (matches "app.example.com", "api.example.com", etc.)
func isOriginAllowed(origin string, allowedOrigins []string) bool {
	for _, allowed := range allowedOrigins {
		// Wildcard allows any origin
		if allowed == "*" {
			return true
		}

		// Exact match
		if allowed == origin {
			return true
		}

		// Subdomain wildcard match (e.g., "*.example.com")
		if strings.HasPrefix(allowed, "*.") {
			// Extract the domain part (e.g., "example.com" from "*.example.com")
			wildcardDomain := allowed[1:] // Remove the "*", keep ".example.com"

			// Parse the origin to get its host
			// Origin format: "http://subdomain.example.com" or "https://subdomain.example.com:port"
			originHost := extractHost(origin)
			if originHost != "" && strings.HasSuffix(originHost, wildcardDomain) {
				return true
			}
		}
	}

	return false
}

// extractHost extracts the host (without port) from an origin URL
// "http://example.com:3000" -> "example.com"
// "https://app.example.com" -> "app.example.com"
func extractHost(origin string) string {
	// Remove protocol
	host := origin
	if idx := strings.Index(origin, "://"); idx != -1 {
		host = origin[idx+3:]
	}

	// Remove port if present
	if idx := strings.LastIndex(host, ":"); idx != -1 {
		// Make sure we're not cutting an IPv6 address
		if !strings.Contains(host[idx:], "]") {
			host = host[:idx]
		}
	}

	// Remove path if present
	if idx := strings.Index(host, "/"); idx != -1 {
		host = host[:idx]
	}

	return host
}

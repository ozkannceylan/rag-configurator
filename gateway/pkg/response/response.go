package response

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// Error sends a standardized error response
func Error(c *gin.Context, status int, code string, message string) {
	c.JSON(status, gin.H{
		"error":   code,
		"message": message,
	})
}

// BadGateway sends a 502 error
func BadGateway(c *gin.Context, message string) {
	Error(c, http.StatusBadGateway, "bad_gateway", message)
}

// ServiceUnavailable sends a 503 error
func ServiceUnavailable(c *gin.Context, message string) {
	Error(c, http.StatusServiceUnavailable, "service_unavailable", message)
}

// InternalError sends a 500 error
func InternalError(c *gin.Context, message string) {
	Error(c, http.StatusInternalServerError, "internal_error", message)
}

// Unauthorized sends a 401 error
func Unauthorized(c *gin.Context, message string) {
	Error(c, http.StatusUnauthorized, "unauthorized", message)
}

// Forbidden sends a 403 error
func Forbidden(c *gin.Context, message string) {
	Error(c, http.StatusForbidden, "forbidden", message)
}

// NotFound sends a 404 error
func NotFound(c *gin.Context, message string) {
	Error(c, http.StatusNotFound, "not_found", message)
}

// BadRequest sends a 400 error
func BadRequest(c *gin.Context, message string) {
	Error(c, http.StatusBadRequest, "bad_request", message)
}

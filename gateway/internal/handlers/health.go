package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"gateway/internal/config"
)

// Health returns a handler for health check endpoint
func Health(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":      "healthy",
			"service":     "gateway",
			"environment": cfg.Environment,
		})
	}
}

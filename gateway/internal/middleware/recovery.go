package middleware

import (
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
)

// Recovery returns a middleware that recovers from panics
func Recovery() gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if err := recover(); err != nil {
				log.Error().Interface("panic", err).Msg("Panic recovered")
				c.AbortWithStatusJSON(500, gin.H{
					"error": "Internal server error",
				})
			}
		}()
		c.Next()
	}
}

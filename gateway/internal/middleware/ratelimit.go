package middleware

import (
	"net/http"
	"sync"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
	"golang.org/x/time/rate"
)

// ipRateLimiter manages rate limiters per client IP
type ipRateLimiter struct {
	limiters map[string]*rate.Limiter
	mu       sync.RWMutex
	rps      rate.Limit
	burst    int
}

// newIPRateLimiter creates a new IP-based rate limiter
func newIPRateLimiter(rps int, burst int) *ipRateLimiter {
	return &ipRateLimiter{
		limiters: make(map[string]*rate.Limiter),
		rps:      rate.Limit(rps),
		burst:    burst,
	}
}

// getLimiter returns the rate limiter for the given IP address
// Creates a new limiter if one doesn't exist
func (rl *ipRateLimiter) getLimiter(ip string) *rate.Limiter {
	// Try read lock first for better performance
	rl.mu.RLock()
	limiter, exists := rl.limiters[ip]
	rl.mu.RUnlock()

	if exists {
		return limiter
	}

	// Create new limiter
	rl.mu.Lock()
	defer rl.mu.Unlock()

	// Double-check after acquiring write lock
	if limiter, exists = rl.limiters[ip]; exists {
		return limiter
	}

	limiter = rate.NewLimiter(rl.rps, rl.burst)
	rl.limiters[ip] = limiter

	return limiter
}

// RateLimit returns a middleware that limits request rate per IP
// Uses token bucket algorithm with the specified requests per second and burst size
func RateLimit(rps int, burst int) gin.HandlerFunc {
	// Create the rate limiter store
	rl := newIPRateLimiter(rps, burst)

	return func(c *gin.Context) {
		// Get client IP (handles X-Forwarded-For automatically)
		ip := c.ClientIP()

		// Get or create limiter for this IP
		limiter := rl.getLimiter(ip)

		// Check if request is allowed
		if !limiter.Allow() {
			log.Warn().
				Str("ip", ip).
				Str("path", c.Request.URL.Path).
				Str("method", c.Request.Method).
				Msg("Rate limit exceeded")

			c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{
				"error":   "Too Many Requests",
				"message": "Rate limit exceeded. Please try again later.",
			})
			return
		}

		c.Next()
	}
}

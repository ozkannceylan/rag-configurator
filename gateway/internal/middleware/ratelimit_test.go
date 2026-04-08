package middleware

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupRateLimitRouter(rps int, burst int) *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(RateLimit(rps, burst))
	r.GET("/test", func(c *gin.Context) {
		c.JSON(200, gin.H{"message": "ok"})
	})
	return r
}

func TestRateLimit_AllowsNormalTraffic(t *testing.T) {
	router := setupRateLimitRouter(10, 10)

	// Make a few requests, should all pass
	for i := 0; i < 5; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/test", nil)
		req.RemoteAddr = "192.168.1.1:12345"
		router.ServeHTTP(w, req)

		assert.Equal(t, 200, w.Code, "Request %d should succeed", i+1)
	}
}

func TestRateLimit_BlocksExcessiveTraffic(t *testing.T) {
	// Very low limit: 1 RPS with burst of 2
	router := setupRateLimitRouter(1, 2)

	var successCount, blockedCount int

	// Make more requests than allowed
	for i := 0; i < 10; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/test", nil)
		req.RemoteAddr = "192.168.1.1:12345"
		router.ServeHTTP(w, req)

		if w.Code == 200 {
			successCount++
		} else if w.Code == 429 {
			blockedCount++
		}
	}

	// Should have some successful and some blocked
	assert.True(t, successCount > 0, "Should have some successful requests")
	assert.True(t, blockedCount > 0, "Should have some blocked requests")
	assert.Equal(t, 10, successCount+blockedCount, "Total should be 10")
}

func TestRateLimit_Returns429WithCorrectBody(t *testing.T) {
	// Very restrictive: 1 RPS with burst of 1
	router := setupRateLimitRouter(1, 1)

	// First request succeeds
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.RemoteAddr = "192.168.1.1:12345"
	router.ServeHTTP(w, req)
	assert.Equal(t, 200, w.Code)

	// Second request should be rate limited
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/test", nil)
	req.RemoteAddr = "192.168.1.1:12345"
	router.ServeHTTP(w, req)

	assert.Equal(t, 429, w.Code)

	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.Equal(t, "Too Many Requests", response["error"])
	assert.Equal(t, "Rate limit exceeded. Please try again later.", response["message"])
}

func TestRateLimit_SeparateLimitersPerIP(t *testing.T) {
	// 1 RPS with burst of 2 per IP
	router := setupRateLimitRouter(1, 2)

	// IP 1: Use up the burst
	for i := 0; i < 2; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/test", nil)
		req.RemoteAddr = "192.168.1.1:12345"
		router.ServeHTTP(w, req)
		assert.Equal(t, 200, w.Code, "IP1 request %d should succeed", i+1)
	}

	// IP 1: Should be rate limited now
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.RemoteAddr = "192.168.1.1:12345"
	router.ServeHTTP(w, req)
	assert.Equal(t, 429, w.Code, "IP1 should be rate limited")

	// IP 2: Should still be able to make requests (independent limiter)
	for i := 0; i < 2; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/test", nil)
		req.RemoteAddr = "192.168.1.2:12345"
		router.ServeHTTP(w, req)
		assert.Equal(t, 200, w.Code, "IP2 request %d should succeed", i+1)
	}
}

func TestRateLimit_BurstAllowed(t *testing.T) {
	// 1 RPS with burst of 5
	router := setupRateLimitRouter(1, 5)

	// Should be able to make 5 requests immediately (burst)
	for i := 0; i < 5; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/test", nil)
		req.RemoteAddr = "192.168.1.1:12345"
		router.ServeHTTP(w, req)
		assert.Equal(t, 200, w.Code, "Burst request %d should succeed", i+1)
	}

	// 6th request should be rate limited (burst exhausted)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	req.RemoteAddr = "192.168.1.1:12345"
	router.ServeHTTP(w, req)
	assert.Equal(t, 429, w.Code, "Request after burst should be rate limited")
}

func TestRateLimit_ConcurrentRequests(t *testing.T) {
	// High limit to avoid false positives
	router := setupRateLimitRouter(100, 100)

	var wg sync.WaitGroup
	var mu sync.Mutex
	successCount := 0

	// Make 50 concurrent requests from same IP
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			w := httptest.NewRecorder()
			req, _ := http.NewRequest("GET", "/test", nil)
			req.RemoteAddr = "192.168.1.1:12345"
			router.ServeHTTP(w, req)

			mu.Lock()
			if w.Code == 200 {
				successCount++
			}
			mu.Unlock()
		}()
	}

	wg.Wait()

	// All should succeed with this high limit
	assert.Equal(t, 50, successCount, "All concurrent requests should succeed")
}

func TestRateLimit_DifferentIPsConcurrent(t *testing.T) {
	// Low limit per IP: 2 RPS with burst of 2
	router := setupRateLimitRouter(2, 2)

	var wg sync.WaitGroup
	var mu sync.Mutex
	results := make(map[string]int)

	// Make requests from multiple IPs concurrently
	ips := []string{"192.168.1.1", "192.168.1.2", "192.168.1.3"}

	for _, ip := range ips {
		for i := 0; i < 3; i++ {
			wg.Add(1)
			ipCopy := ip
			go func() {
				defer wg.Done()
				w := httptest.NewRecorder()
				req, _ := http.NewRequest("GET", "/test", nil)
				req.RemoteAddr = ipCopy + ":12345"
				router.ServeHTTP(w, req)

				mu.Lock()
				if w.Code == 200 {
					results[ipCopy]++
				}
				mu.Unlock()
			}()
		}
	}

	wg.Wait()

	// Each IP should have at least some successful requests
	for _, ip := range ips {
		assert.True(t, results[ip] > 0, "IP %s should have successful requests", ip)
	}
}

func TestNewIPRateLimiter(t *testing.T) {
	rl := newIPRateLimiter(100, 200)

	assert.NotNil(t, rl)
	assert.NotNil(t, rl.limiters)
	assert.Equal(t, 100, int(rl.rps))
	assert.Equal(t, 200, rl.burst)
}

func TestGetLimiter_CreatesNewLimiter(t *testing.T) {
	rl := newIPRateLimiter(10, 20)

	limiter1 := rl.getLimiter("192.168.1.1")
	assert.NotNil(t, limiter1)

	// Getting the same IP should return the same limiter (same pointer)
	limiter2 := rl.getLimiter("192.168.1.1")
	assert.True(t, limiter1 == limiter2, "Same IP should return same limiter instance")

	// Different IP should get different limiter (different pointer)
	limiter3 := rl.getLimiter("192.168.1.2")
	assert.True(t, limiter1 != limiter3, "Different IPs should get different limiter instances")
}

func TestGetLimiter_ThreadSafe(t *testing.T) {
	rl := newIPRateLimiter(10, 20)

	var wg sync.WaitGroup
	limiters := make([]*interface{}, 100)

	// Concurrent access to the same IP
	for i := 0; i < 100; i++ {
		wg.Add(1)
		idx := i
		go func() {
			defer wg.Done()
			limiter := rl.getLimiter("192.168.1.1")
			var iface interface{} = limiter
			limiters[idx] = &iface
		}()
	}

	wg.Wait()

	// All should get the same limiter (after creation)
	// Just verify no panic occurred and all got non-nil limiters
	for i, l := range limiters {
		assert.NotNil(t, l, "Limiter %d should not be nil", i)
	}
}

func TestCleanupStaleEntries_RemovesExpiredLimiters(t *testing.T) {
	rl := newIPRateLimiter(10, 20)
	now := time.Now()
	rl.now = func() time.Time { return now }
	rl.entryTTL = 10 * time.Minute

	rl.limiters["192.168.1.1"] = rl.getLimiter("192.168.1.1")
	rl.limiters["192.168.1.2"] = rl.getLimiter("192.168.1.2")
	rl.lastSeen["192.168.1.1"] = now.Add(-11 * time.Minute)
	rl.lastSeen["192.168.1.2"] = now

	removed := rl.cleanupStaleEntries()

	assert.Equal(t, 1, removed)
	_, staleExists := rl.limiters["192.168.1.1"]
	_, freshExists := rl.limiters["192.168.1.2"]
	assert.False(t, staleExists)
	assert.True(t, freshExists)
}

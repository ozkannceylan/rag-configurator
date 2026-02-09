package proxy

import (
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"

	"gateway/internal/config"
)

// Proxy handles reverse proxy to backend services
type Proxy struct {
	cfg            *config.Config
	configProxy    *httputil.ReverseProxy
	ingestionProxy *httputil.ReverseProxy
	ragProxy       *httputil.ReverseProxy
	httpClient     *http.Client
}

// New creates a new Proxy instance with configured reverse proxies
func New(cfg *config.Config) *Proxy {
	// Shared HTTP client with reasonable timeouts
	httpClient := &http.Client{
		Timeout: 60 * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 10,
			IdleConnTimeout:     90 * time.Second,
		},
	}

	p := &Proxy{
		cfg:        cfg,
		httpClient: httpClient,
	}

	// Create reverse proxies for each backend
	p.configProxy = p.createReverseProxy(cfg.ConfigServiceURL)
	p.ingestionProxy = p.createReverseProxy(cfg.IngestionServiceURL)
	p.ragProxy = p.createReverseProxy(cfg.RAGServiceURL)

	return p
}

// createReverseProxy creates a configured reverse proxy for a target URL
func (p *Proxy) createReverseProxy(targetURL string) *httputil.ReverseProxy {
	target, err := url.Parse(targetURL)
	if err != nil {
		log.Fatal().Err(err).Str("url", targetURL).Msg("Invalid backend URL")
	}

	proxy := httputil.NewSingleHostReverseProxy(target)
	proxy.Transport = p.httpClient.Transport
	proxy.FlushInterval = -1 // Flush immediately for SSE streaming

	// Custom director to modify the request
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		originalDirector(req)

		// Ensure the host header is set to the target
		req.Host = target.Host

		// Add proxy headers
		if clientIP := req.Header.Get("X-Forwarded-For"); clientIP == "" {
			if addr := req.RemoteAddr; addr != "" {
				// Remove port if present
				if idx := strings.LastIndex(addr, ":"); idx != -1 {
					addr = addr[:idx]
				}
				req.Header.Set("X-Forwarded-For", addr)
				req.Header.Set("X-Real-IP", addr)
			}
		}

		// Preserve the original protocol
		if req.Header.Get("X-Forwarded-Proto") == "" {
			if req.TLS != nil {
				req.Header.Set("X-Forwarded-Proto", "https")
			} else {
				req.Header.Set("X-Forwarded-Proto", "http")
			}
		}

		log.Debug().
			Str("method", req.Method).
			Str("target", target.String()).
			Str("path", req.URL.Path).
			Msg("Proxying request")
	}

	// Custom error handler
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		log.Error().
			Err(err).
			Str("target", targetURL).
			Str("path", r.URL.Path).
			Msg("Proxy error")

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadGateway)
		w.Write([]byte(`{"error":"Service unavailable","message":"Backend service is not responding"}`))
	}

	// Modify response if needed (e.g., for logging)
	proxy.ModifyResponse = func(resp *http.Response) error {
		log.Debug().
			Int("status", resp.StatusCode).
			Str("target", targetURL).
			Msg("Proxy response received")
		return nil
	}

	return proxy
}

// ToConfigService returns a handler that proxies to Config Service
func (p *Proxy) ToConfigService() gin.HandlerFunc {
	return p.createProxyHandler(p.configProxy, p.cfg.ConfigServiceURL)
}

// ToIngestionService returns a handler that proxies to Ingestion Service
func (p *Proxy) ToIngestionService() gin.HandlerFunc {
	return p.createProxyHandler(p.ingestionProxy, p.cfg.IngestionServiceURL)
}

// ToRAGService returns a handler that proxies to RAG Service
func (p *Proxy) ToRAGService() gin.HandlerFunc {
	return p.createProxyHandler(p.ragProxy, p.cfg.RAGServiceURL)
}

// ToConfigServiceRewrite returns a handler that proxies to Config Service with path rewriting
func (p *Proxy) ToConfigServiceRewrite(newPath string) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Rewrite the request path before proxying
		c.Request.URL.Path = newPath

		log.Info().
			Str("method", c.Request.Method).
			Str("path", newPath).
			Str("target", p.cfg.ConfigServiceURL).
			Str("client_ip", c.ClientIP()).
			Msg("Proxying request (rewritten)")

		p.configProxy.ServeHTTP(c.Writer, c.Request)
	}
}

// createProxyHandler creates a Gin handler that uses the reverse proxy
func (p *Proxy) createProxyHandler(proxy *httputil.ReverseProxy, targetURL string) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Reconstruct the full path including any path parameters
		// Gin's c.Request.URL.Path already has the resolved path

		// Add query parameters
		if c.Request.URL.RawQuery != "" {
			log.Debug().
				Str("query", c.Request.URL.RawQuery).
				Msg("Preserving query parameters")
		}

		// Log the proxy action
		log.Info().
			Str("method", c.Request.Method).
			Str("path", c.Request.URL.Path).
			Str("target", targetURL).
			Str("client_ip", c.ClientIP()).
			Msg("Proxying request")

		// Use the reverse proxy
		proxy.ServeHTTP(c.Writer, c.Request)
	}
}

// ProxyRequest is an alternative method for more control over the proxy
// Use this for special cases like file uploads or when you need to modify the request
func (p *Proxy) ProxyRequest(c *gin.Context, targetBaseURL string) {
	// Parse target URL
	targetURL, err := url.Parse(targetBaseURL)
	if err != nil {
		log.Error().Err(err).Str("url", targetBaseURL).Msg("Invalid target URL")
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "Internal server error",
			"message": "Invalid backend configuration",
		})
		return
	}

	// Build the full target URL
	targetURL.Path = c.Request.URL.Path
	targetURL.RawQuery = c.Request.URL.RawQuery

	// Create new request
	proxyReq, err := http.NewRequestWithContext(
		c.Request.Context(),
		c.Request.Method,
		targetURL.String(),
		c.Request.Body,
	)
	if err != nil {
		log.Error().Err(err).Msg("Failed to create proxy request")
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "Internal server error",
			"message": "Failed to create proxy request",
		})
		return
	}

	// Copy headers from original request
	for key, values := range c.Request.Header {
		for _, value := range values {
			proxyReq.Header.Add(key, value)
		}
	}

	// Add proxy headers
	proxyReq.Header.Set("X-Forwarded-For", c.ClientIP())
	proxyReq.Header.Set("X-Real-IP", c.ClientIP())
	proxyReq.Header.Set("X-Forwarded-Host", c.Request.Host)

	// Make the request
	resp, err := p.httpClient.Do(proxyReq)
	if err != nil {
		log.Error().Err(err).Str("url", targetURL.String()).Msg("Backend request failed")
		c.JSON(http.StatusBadGateway, gin.H{
			"error":   "Service unavailable",
			"message": "Backend service is not responding",
		})
		return
	}
	defer resp.Body.Close()

	// Copy response headers
	for key, values := range resp.Header {
		for _, value := range values {
			c.Writer.Header().Add(key, value)
		}
	}

	// Set status code
	c.Writer.WriteHeader(resp.StatusCode)

	// Stream response body
	io.Copy(c.Writer, resp.Body)
}

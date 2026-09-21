package handlers

import (
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/rs/zerolog/log"

	"gateway/internal/middleware"
)

// WebSocket upgrader configuration
var upgrader = websocket.Upgrader{
	ReadBufferSize:   1024,
	WriteBufferSize:  1024,
	HandshakeTimeout: 10 * time.Second,
}

// WebSocketProxy returns a handler for WebSocket connections
// It proxies WebSocket connections between the client and the RAG service
func WebSocketProxy(targetURL string, allowedOrigins ...string) gin.HandlerFunc {
	return func(c *gin.Context) {
		currentUpgrader := upgrader
		currentUpgrader.CheckOrigin = func(r *http.Request) bool {
			return isOriginAllowed(r.Header.Get("Origin"), allowedOrigins)
		}

		// Upgrade client connection to WebSocket
		clientConn, err := currentUpgrader.Upgrade(c.Writer, c.Request, nil)
		if err != nil {
			log.Error().
				Err(err).
				Str("client_ip", c.ClientIP()).
				Msg("Failed to upgrade client connection to WebSocket")
			return
		}
		defer func() { _ = clientConn.Close() }()

		// Build backend WebSocket URL
		backendURL, err := buildWebSocketURL(targetURL, c.Request)
		if err != nil {
			log.Error().
				Err(err).
				Str("target_url", targetURL).
				Msg("Failed to build backend WebSocket URL")
			// The WebSocket handshake already completed, so the HTTP response is
			// committed: a failed close frame just means the client is gone too,
			// and we return either way.
			_ = clientConn.WriteMessage(websocket.CloseMessage,
				websocket.FormatCloseMessage(websocket.CloseInternalServerErr, "Failed to connect to backend"))
			return
		}

		// Prepare headers to forward to backend
		requestHeader := buildBackendHeaders(c)

		// Connect to backend WebSocket
		dialer := websocket.Dialer{
			HandshakeTimeout: 10 * time.Second,
		}

		backendConn, resp, err := dialer.Dial(backendURL, requestHeader)
		if err != nil {
			log.Error().
				Err(err).
				Str("backend_url", backendURL).
				Msg("Failed to connect to backend WebSocket")

			closeCode := websocket.CloseInternalServerErr
			closeMessage := "Backend connection failed"
			if resp != nil {
				switch resp.StatusCode {
				case http.StatusUnauthorized:
					closeCode = websocket.ClosePolicyViolation
					closeMessage = "Unauthorized"
				case http.StatusServiceUnavailable:
					closeMessage = "Backend unavailable"
				}
			}
			_ = clientConn.WriteMessage(websocket.CloseMessage,
				websocket.FormatCloseMessage(closeCode, closeMessage))
			return
		}
		defer func() { _ = backendConn.Close() }()

		log.Info().
			Str("client_ip", c.ClientIP()).
			Str("backend_url", backendURL).
			Msg("WebSocket connection established")

		// Create a channel to signal when either connection closes
		done := make(chan struct{})
		var once sync.Once
		closeDone := func() {
			once.Do(func() {
				close(done)
			})
		}

		// Proxy messages from client to backend
		go proxyMessages(clientConn, backendConn, "client->backend", closeDone)

		// Proxy messages from backend to client
		go proxyMessages(backendConn, clientConn, "backend->client", closeDone)

		// Wait for either connection to close
		<-done

		log.Info().
			Str("client_ip", c.ClientIP()).
			Msg("WebSocket connection closed")
	}
}

func isOriginAllowed(origin string, allowedOrigins []string) bool {
	if origin == "" {
		return true
	}

	for _, allowedOrigin := range allowedOrigins {
		trimmed := strings.TrimSpace(allowedOrigin)
		if trimmed == "*" || strings.EqualFold(trimmed, origin) {
			return true
		}
	}

	return false
}

// buildWebSocketURL constructs the backend WebSocket URL from the target URL and request
func buildWebSocketURL(targetURL string, req *http.Request) (string, error) {
	// Parse the target URL
	parsed, err := url.Parse(targetURL)
	if err != nil {
		return "", err
	}

	// Convert HTTP scheme to WebSocket scheme
	switch parsed.Scheme {
	case "http":
		parsed.Scheme = "ws"
	case "https":
		parsed.Scheme = "wss"
	case "ws", "wss":
		// Already WebSocket scheme
	default:
		// Assume http -> ws
		parsed.Scheme = "ws"
	}

	// Append the original request path if needed
	if req.URL.Path != "" && req.URL.Path != "/" {
		parsed.Path = strings.TrimSuffix(parsed.Path, "/") + req.URL.Path
	}

	// Preserve query parameters
	if req.URL.RawQuery != "" {
		parsed.RawQuery = req.URL.RawQuery
	}

	return parsed.String(), nil
}

// buildBackendHeaders creates headers to forward to the backend WebSocket
func buildBackendHeaders(c *gin.Context) http.Header {
	headers := http.Header{}

	// Forward Authorization header if present
	if auth := c.GetHeader("Authorization"); auth != "" {
		headers.Set("Authorization", auth)
	}

	// Forward user ID from context (set by auth middleware)
	if userID := middleware.GetUserID(c); userID != "" {
		headers.Set("X-User-ID", userID)
	}

	// Add request ID for tracing
	if requestID := c.GetHeader("X-Request-ID"); requestID != "" {
		headers.Set("X-Request-ID", requestID)
	}

	// Add forwarded headers
	headers.Set("X-Forwarded-For", c.ClientIP())
	headers.Set("X-Forwarded-Proto", getScheme(c))

	return headers
}

// getScheme returns the request scheme (http or https)
func getScheme(c *gin.Context) string {
	// Check X-Forwarded-Proto first (for reverse proxies)
	if proto := c.GetHeader("X-Forwarded-Proto"); proto != "" {
		return proto
	}

	// Check if TLS is used
	if c.Request.TLS != nil {
		return "https"
	}

	return "http"
}

// proxyMessages reads messages from src and writes them to dst
func proxyMessages(src, dst *websocket.Conn, direction string, onClose func()) {
	defer onClose()

	for {
		messageType, message, err := src.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err,
				websocket.CloseGoingAway,
				websocket.CloseNormalClosure,
				websocket.CloseNoStatusReceived) {
				log.Warn().
					Err(err).
					Str("direction", direction).
					Msg("WebSocket read error")
			}
			// Send close message to the other end. The pump is terminating
			// regardless, and the peer may already be gone, so a write failure
			// here is not actionable.
			_ = dst.WriteMessage(websocket.CloseMessage,
				websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
			return
		}

		err = dst.WriteMessage(messageType, message)
		if err != nil {
			log.Warn().
				Err(err).
				Str("direction", direction).
				Msg("WebSocket write error")
			return
		}
	}
}

package handlers

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestBuildWebSocketURL_HTTPToWS(t *testing.T) {
	req := httptest.NewRequest("GET", "/stream", nil)

	url, err := buildWebSocketURL("http://localhost:8003", req)

	require.NoError(t, err)
	assert.Equal(t, "ws://localhost:8003/stream", url)
}

func TestBuildWebSocketURL_HTTPSToWSS(t *testing.T) {
	req := httptest.NewRequest("GET", "/stream", nil)

	url, err := buildWebSocketURL("https://localhost:8003", req)

	require.NoError(t, err)
	assert.Equal(t, "wss://localhost:8003/stream", url)
}

func TestBuildWebSocketURL_AlreadyWS(t *testing.T) {
	req := httptest.NewRequest("GET", "/stream", nil)

	url, err := buildWebSocketURL("ws://localhost:8003", req)

	require.NoError(t, err)
	assert.Equal(t, "ws://localhost:8003/stream", url)
}

func TestBuildWebSocketURL_PreservesQueryParams(t *testing.T) {
	req := httptest.NewRequest("GET", "/stream?config_id=123&token=abc", nil)

	url, err := buildWebSocketURL("http://localhost:8003", req)

	require.NoError(t, err)
	assert.Equal(t, "ws://localhost:8003/stream?config_id=123&token=abc", url)
}

func TestBuildWebSocketURL_WithBasePath(t *testing.T) {
	req := httptest.NewRequest("GET", "/stream", nil)

	url, err := buildWebSocketURL("http://localhost:8003/api/v1", req)

	require.NoError(t, err)
	assert.Equal(t, "ws://localhost:8003/api/v1/stream", url)
}

func TestBuildWebSocketURL_InvalidURL(t *testing.T) {
	req := httptest.NewRequest("GET", "/stream", nil)

	_, err := buildWebSocketURL("://invalid", req)

	assert.Error(t, err)
}

func TestBuildBackendHeaders_Authorization(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/stream", nil)
	c.Request.Header.Set("Authorization", "Bearer test-token")

	headers := buildBackendHeaders(c)

	assert.Equal(t, "Bearer test-token", headers.Get("Authorization"))
}

func TestBuildBackendHeaders_RequestID(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/stream", nil)
	c.Request.Header.Set("X-Request-ID", "req-123")

	headers := buildBackendHeaders(c)

	assert.Equal(t, "req-123", headers.Get("X-Request-ID"))
}

func TestBuildBackendHeaders_ForwardedFor(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/stream", nil)
	c.Request.RemoteAddr = "192.168.1.100:12345"

	headers := buildBackendHeaders(c)

	assert.NotEmpty(t, headers.Get("X-Forwarded-For"))
}

func TestBuildBackendHeaders_UserIDFromContext(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/stream", nil)
	c.Set("user_id", "user-456")

	headers := buildBackendHeaders(c)

	assert.Equal(t, "user-456", headers.Get("X-User-ID"))
}

func TestGetScheme_Default(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/", nil)

	scheme := getScheme(c)

	assert.Equal(t, "http", scheme)
}

func TestGetScheme_FromForwardedProto(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/", nil)
	c.Request.Header.Set("X-Forwarded-Proto", "https")

	scheme := getScheme(c)

	assert.Equal(t, "https", scheme)
}

func TestWebSocketProxy_FullBidirectionalProxy(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Create a mock backend WebSocket server
	backendMessages := make(chan string, 10)
	backendServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader := websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			t.Logf("Backend upgrade error: %v", err)
			return
		}
		defer conn.Close()

		// Echo server: read message and send response
		for {
			messageType, message, err := conn.ReadMessage()
			if err != nil {
				break
			}
			backendMessages <- string(message)

			// Send response back
			response := "Echo: " + string(message)
			if err := conn.WriteMessage(messageType, []byte(response)); err != nil {
				break
			}
		}
	}))
	defer backendServer.Close()

	// Create gateway with WebSocket proxy
	router := gin.New()
	router.GET("/stream", WebSocketProxy(backendServer.URL))

	// Create gateway server
	gatewayServer := httptest.NewServer(router)
	defer gatewayServer.Close()

	// Connect client to gateway
	wsURL := "ws" + strings.TrimPrefix(gatewayServer.URL, "http") + "/stream"
	clientConn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)
	defer clientConn.Close()

	// Send message from client through gateway to backend
	testMessage := "Hello from client"
	err = clientConn.WriteMessage(websocket.TextMessage, []byte(testMessage))
	require.NoError(t, err)

	// Verify backend received the message
	select {
	case msg := <-backendMessages:
		assert.Equal(t, testMessage, msg)
	case <-time.After(2 * time.Second):
		t.Fatal("Backend did not receive message in time")
	}

	// Verify client receives the echo response
	_, response, err := clientConn.ReadMessage()
	require.NoError(t, err)
	assert.Equal(t, "Echo: "+testMessage, string(response))
}

func TestWebSocketProxy_MultipleMessages(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Create echo backend
	backendServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader := websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()

		for {
			messageType, message, err := conn.ReadMessage()
			if err != nil {
				break
			}
			if err := conn.WriteMessage(messageType, message); err != nil {
				break
			}
		}
	}))
	defer backendServer.Close()

	router := gin.New()
	router.GET("/stream", WebSocketProxy(backendServer.URL))

	gatewayServer := httptest.NewServer(router)
	defer gatewayServer.Close()

	wsURL := "ws" + strings.TrimPrefix(gatewayServer.URL, "http") + "/stream"
	clientConn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)
	defer clientConn.Close()

	// Send multiple messages
	messages := []string{"Message 1", "Message 2", "Message 3"}
	for _, msg := range messages {
		err = clientConn.WriteMessage(websocket.TextMessage, []byte(msg))
		require.NoError(t, err)

		_, response, err := clientConn.ReadMessage()
		require.NoError(t, err)
		assert.Equal(t, msg, string(response))
	}
}

func TestWebSocketProxy_BinaryMessages(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Create echo backend
	backendServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader := websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()

		for {
			messageType, message, err := conn.ReadMessage()
			if err != nil {
				break
			}
			if err := conn.WriteMessage(messageType, message); err != nil {
				break
			}
		}
	}))
	defer backendServer.Close()

	router := gin.New()
	router.GET("/stream", WebSocketProxy(backendServer.URL))

	gatewayServer := httptest.NewServer(router)
	defer gatewayServer.Close()

	wsURL := "ws" + strings.TrimPrefix(gatewayServer.URL, "http") + "/stream"
	clientConn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)
	defer clientConn.Close()

	// Send binary message
	binaryData := []byte{0x00, 0x01, 0x02, 0x03, 0xFF, 0xFE}
	err = clientConn.WriteMessage(websocket.BinaryMessage, binaryData)
	require.NoError(t, err)

	messageType, response, err := clientConn.ReadMessage()
	require.NoError(t, err)
	assert.Equal(t, websocket.BinaryMessage, messageType)
	assert.Equal(t, binaryData, response)
}

func TestWebSocketProxy_HeadersForwarded(t *testing.T) {
	gin.SetMode(gin.TestMode)

	receivedHeaders := make(chan http.Header, 1)

	// Create backend that captures headers
	backendServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedHeaders <- r.Header

		upgrader := websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()

		// Just keep connection alive briefly
		conn.ReadMessage()
	}))
	defer backendServer.Close()

	router := gin.New()
	router.GET("/stream", WebSocketProxy(backendServer.URL))

	gatewayServer := httptest.NewServer(router)
	defer gatewayServer.Close()

	wsURL := "ws" + strings.TrimPrefix(gatewayServer.URL, "http") + "/stream"
	headers := http.Header{}
	headers.Set("Authorization", "Bearer my-token")
	headers.Set("X-Request-ID", "test-request-123")

	clientConn, _, err := websocket.DefaultDialer.Dial(wsURL, headers)
	require.NoError(t, err)
	defer clientConn.Close()

	select {
	case hdrs := <-receivedHeaders:
		assert.Equal(t, "Bearer my-token", hdrs.Get("Authorization"))
		assert.Equal(t, "test-request-123", hdrs.Get("X-Request-ID"))
		assert.NotEmpty(t, hdrs.Get("X-Forwarded-For"))
	case <-time.After(2 * time.Second):
		t.Fatal("Did not receive headers in time")
	}
}

func TestWebSocketProxy_BackendUnavailable(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Use a port that's not listening
	router := gin.New()
	router.GET("/stream", WebSocketProxy("http://localhost:59999"))

	gatewayServer := httptest.NewServer(router)
	defer gatewayServer.Close()

	wsURL := "ws" + strings.TrimPrefix(gatewayServer.URL, "http") + "/stream"
	clientConn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)

	// Should still connect to gateway, but get close message when backend fails
	if err == nil {
		defer clientConn.Close()
		// Try to read - should get close message
		_, _, err = clientConn.ReadMessage()
		assert.Error(t, err)
	}
	// Or connection might fail entirely, which is also acceptable
}

func TestWebSocketProxy_ClientCloses(t *testing.T) {
	gin.SetMode(gin.TestMode)

	backendClosed := make(chan struct{})

	backendServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader := websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer func() {
			conn.Close()
			close(backendClosed)
		}()

		// Wait for close
		for {
			_, _, err := conn.ReadMessage()
			if err != nil {
				break
			}
		}
	}))
	defer backendServer.Close()

	router := gin.New()
	router.GET("/stream", WebSocketProxy(backendServer.URL))

	gatewayServer := httptest.NewServer(router)
	defer gatewayServer.Close()

	wsURL := "ws" + strings.TrimPrefix(gatewayServer.URL, "http") + "/stream"
	clientConn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)

	// Close client connection
	clientConn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
	clientConn.Close()

	// Backend should also close
	select {
	case <-backendClosed:
		// Success
	case <-time.After(2 * time.Second):
		t.Fatal("Backend did not close in time")
	}
}

func TestWebSocketProxy_BackendCloses(t *testing.T) {
	gin.SetMode(gin.TestMode)

	backendServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader := websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}

		// Close immediately after connection
		conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, "Goodbye"))
		conn.Close()
	}))
	defer backendServer.Close()

	router := gin.New()
	router.GET("/stream", WebSocketProxy(backendServer.URL))

	gatewayServer := httptest.NewServer(router)
	defer gatewayServer.Close()

	wsURL := "ws" + strings.TrimPrefix(gatewayServer.URL, "http") + "/stream"
	clientConn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)
	defer clientConn.Close()

	// Client should receive close message
	_, _, err = clientConn.ReadMessage()
	assert.Error(t, err)
}

func TestWebSocketProxy_PreservesQueryParams(t *testing.T) {
	gin.SetMode(gin.TestMode)

	receivedPath := make(chan string, 1)

	backendServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedPath <- r.URL.String()

		upgrader := websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		conn.ReadMessage()
	}))
	defer backendServer.Close()

	router := gin.New()
	router.GET("/stream", WebSocketProxy(backendServer.URL))

	gatewayServer := httptest.NewServer(router)
	defer gatewayServer.Close()

	wsURL := "ws" + strings.TrimPrefix(gatewayServer.URL, "http") + "/stream?config_id=123&mode=chat"
	clientConn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)
	defer clientConn.Close()

	select {
	case path := <-receivedPath:
		assert.Contains(t, path, "config_id=123")
		assert.Contains(t, path, "mode=chat")
	case <-time.After(2 * time.Second):
		t.Fatal("Did not receive path in time")
	}
}

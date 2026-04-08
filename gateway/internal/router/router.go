package router

import (
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"

	"gateway/internal/config"
	"gateway/internal/handlers"
	"gateway/internal/middleware"
	"gateway/internal/proxy"
)

// New creates a new Gin router with all routes and middleware configured
func New(cfg *config.Config) *gin.Engine {
	r := gin.New()

	// Global middleware (applied to ALL routes)
	r.Use(middleware.Recovery())
	r.Use(middleware.Logging())
	r.Use(middleware.CORS(cfg.CORSOrigins))
	r.Use(middleware.RateLimit(cfg.RateLimitRPS, cfg.RateLimitBurst))

	// Health check endpoints - no additional middleware
	r.GET("/health", handlers.Health(cfg))
	r.GET("/health/detailed", handlers.HealthDetailed(cfg))

	// Create reverse proxy
	proxyHandler := proxy.New(cfg)
	var blacklistChecker middleware.TokenBlacklistChecker
	if cfg.RedisURL != "" {
		checker, err := middleware.NewRedisTokenBlacklistChecker(cfg.RedisURL)
		if err != nil {
			log.Fatal().Err(err).Msg("Failed to initialize token blacklist checker")
		}
		blacklistChecker = checker
	}

	// API v1 routes
	v1 := r.Group("/api/v1")
	{
		// ============================================================
		// PUBLIC ROUTES (no authentication required)
		// ============================================================

		// Auth endpoints - proxy to Config Service without auth
		auth := v1.Group("/auth")
		{
			auth.POST("/register", proxyHandler.ToConfigService())
			auth.POST("/login", proxyHandler.ToConfigService())
			auth.POST("/refresh", proxyHandler.ToConfigService())
			auth.POST("/logout", proxyHandler.ToConfigService())
		}

		// Auth /me endpoint - requires auth, proxy to users/me on Config Service
		authMe := v1.Group("/auth")
		authMe.Use(middleware.Auth(cfg.JWTSecretKey, cfg.JWTAlgorithm, blacklistChecker))
		{
			authMe.GET("/me", proxyHandler.ToConfigServiceRewrite("/api/v1/users/me"))
		}

		// ============================================================
		// PROTECTED ROUTES (authentication required)
		// ============================================================

		// Auth middleware for protected routes
		authMiddleware := middleware.Auth(cfg.JWTSecretKey, cfg.JWTAlgorithm, blacklistChecker)

		// User endpoints - proxy to Config Service
		users := v1.Group("/users")
		users.Use(authMiddleware)
		{
			users.GET("/me", proxyHandler.ToConfigService())
			users.PUT("/me", proxyHandler.ToConfigService())
			users.DELETE("/me", proxyHandler.ToConfigService())
		}

		// Config endpoints - proxy to Config Service
		configs := v1.Group("/configs")
		configs.Use(authMiddleware)
		{
			configs.GET("/", proxyHandler.ToConfigService())
			configs.POST("/", proxyHandler.ToConfigService())
			configs.GET("/:id", proxyHandler.ToConfigService())
			configs.PUT("/:id", proxyHandler.ToConfigService())
			configs.DELETE("/:id", proxyHandler.ToConfigService())
			configs.POST("/:id/duplicate", proxyHandler.ToConfigService())
			configs.GET("/:id/export", proxyHandler.ToConfigService())
			configs.POST("/import", proxyHandler.ToConfigService())
		}

		// Folder endpoints - proxy to Config Service
		folders := v1.Group("/folders")
		folders.Use(authMiddleware)
		{
			folders.POST("/scan", proxyHandler.ToConfigService())
			folders.POST("/browse", proxyHandler.ToConfigService())
		}

		// Ingestion endpoints - proxy to Ingestion Service
		ingest := v1.Group("/ingest")
		ingest.Use(authMiddleware)
		{
			ingest.POST("/:config_id/start", proxyHandler.ToIngestionService())
			ingest.GET("/:config_id/status", proxyHandler.ToIngestionService())
			ingest.POST("/:config_id/cancel", proxyHandler.ToIngestionService())
			ingest.POST("/:config_id/retry", proxyHandler.ToIngestionService())
			ingest.GET("/:config_id/logs", proxyHandler.ToIngestionService())
			ingest.GET("/:config_id/stats", proxyHandler.ToIngestionService())
			ingest.GET("/:config_id/history", proxyHandler.ToIngestionService())
			ingest.DELETE("/:config_id/data", proxyHandler.ToIngestionService())
		}

		// Query endpoints - proxy to RAG Service
		query := v1.Group("/query")
		query.Use(authMiddleware)
		{
			query.GET("", proxyHandler.ToRAGService())
			query.POST("", proxyHandler.ToRAGService())
		}

		// Chat endpoints - proxy to RAG Service
		chat := v1.Group("/chat")
		chat.Use(authMiddleware)
		{
			chat.POST("", proxyHandler.ToRAGService())
			chat.GET("/history/:conversation_id", proxyHandler.ToRAGService())
			chat.DELETE("/history/:conversation_id", proxyHandler.ToRAGService())
		}

		// Stream endpoints - SSE proxy to RAG Service
		stream := v1.Group("/stream")
		stream.Use(authMiddleware)
		{
			ragStreamProxy := proxyHandler.ToRAGService()
			// Handle both with and without trailing slash to avoid 307 redirect
			stream.GET("", func(c *gin.Context) {
				// Append trailing slash for FastAPI compatibility
				c.Request.URL.Path = c.Request.URL.Path + "/"
				ragStreamProxy(c)
			})
			stream.GET("/", proxyHandler.ToRAGService())
			stream.POST("", func(c *gin.Context) {
				c.Request.URL.Path = c.Request.URL.Path + "/"
				ragStreamProxy(c)
			})
			stream.POST("/", proxyHandler.ToRAGService())
		}
	}

	return r
}

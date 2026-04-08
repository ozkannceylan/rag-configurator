package config

import (
	"fmt"
	"strings"
	"time"

	"github.com/caarlos0/env/v10"
	gojwt "github.com/golang-jwt/jwt/v5"
	"github.com/joho/godotenv"

	gatewayjwt "gateway/pkg/jwt"
)

// Config holds all gateway configuration
type Config struct {
	// Server
	Port        int    `env:"GATEWAY_PORT" envDefault:"8000"`
	Environment string `env:"ENVIRONMENT" envDefault:"development"`
	LogLevel    string `env:"LOG_LEVEL" envDefault:"info"`

	// JWT - must match Phase 1 Config Service
	JWTSecretKey string `env:"JWT_SECRET_KEY,required"`
	JWTAlgorithm string `env:"JWT_ALGORITHM" envDefault:"HS256"`

	// Redis
	RedisURL string `env:"REDIS_URL" envDefault:"redis://localhost:6379/0"`

	// Backend Services
	ConfigServiceURL    string `env:"CONFIG_SERVICE_URL" envDefault:"http://localhost:8001"`
	IngestionServiceURL string `env:"INGESTION_SERVICE_URL" envDefault:"http://localhost:8002"`
	RAGServiceURL       string `env:"RAG_SERVICE_URL" envDefault:"http://localhost:8003"`

	// CORS
	CORSOriginsRaw string   `env:"CORS_ORIGINS" envDefault:"http://localhost:3000,http://localhost:3001"`
	CORSOrigins    []string `env:"-"`

	// Rate Limiting
	RateLimitRPS   int `env:"RATE_LIMIT_RPS" envDefault:"100"`
	RateLimitBurst int `env:"RATE_LIMIT_BURST" envDefault:"200"`
}

// IsDevelopment returns true if running in development mode
func (c *Config) IsDevelopment() bool {
	return c.Environment == "development"
}

// Load reads configuration from environment variables
func Load() (*Config, error) {
	// Load .env file if it exists (ignore error if not found)
	_ = godotenv.Load()

	cfg := &Config{}
	if err := env.Parse(cfg); err != nil {
		return nil, fmt.Errorf("failed to parse environment config: %w", err)
	}

	// Parse CORS origins from comma-separated string
	cfg.CORSOrigins = parseCSV(cfg.CORSOriginsRaw)

	// Validate
	if err := cfg.validate(); err != nil {
		return nil, err
	}

	return cfg, nil
}

func (c *Config) validate() error {
	if c.JWTSecretKey == "" {
		return fmt.Errorf("JWT_SECRET_KEY is required")
	}
	if c.JWTAlgorithm != "HS256" && c.JWTAlgorithm != "HS384" && c.JWTAlgorithm != "HS512" {
		return fmt.Errorf("JWT_ALGORITHM must be HS256, HS384, or HS512")
	}
	if err := validateJWTCompatibility(c.JWTSecretKey, c.JWTAlgorithm); err != nil {
		return err
	}
	return nil
}

func validateJWTCompatibility(secretKey string, algorithm string) error {
	validator := gatewayjwt.NewValidator(secretKey, algorithm)
	now := time.Now()
	claims := gatewayjwt.Claims{
		RegisteredClaims: gojwt.RegisteredClaims{
			Subject:   "gateway-startup-check",
			ID:        "gateway-startup-jti",
			IssuedAt:  gojwt.NewNumericDate(now),
			ExpiresAt: gojwt.NewNumericDate(now.Add(5 * time.Minute)),
		},
		Type: "access",
	}

	token := gojwt.NewWithClaims(signingMethod(algorithm), claims)
	tokenString, err := token.SignedString([]byte(secretKey))
	if err != nil {
		return fmt.Errorf("failed to sign JWT compatibility token: %w", err)
	}

	if _, err := validator.ValidateAccessTokenClaims(tokenString); err != nil {
		return fmt.Errorf(
			"gateway JWT validation is incompatible with JWT_SECRET_KEY/JWT_ALGORITHM: %w",
			err,
		)
	}

	return nil
}

func signingMethod(algorithm string) gojwt.SigningMethod {
	switch strings.ToUpper(algorithm) {
	case "HS384":
		return gojwt.SigningMethodHS384
	case "HS512":
		return gojwt.SigningMethodHS512
	default:
		return gojwt.SigningMethodHS256
	}
}

func parseCSV(s string) []string {
	if s == "" {
		return []string{}
	}
	parts := strings.Split(s, ",")
	result := make([]string, 0, len(parts))
	for _, p := range parts {
		trimmed := strings.TrimSpace(p)
		if trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}

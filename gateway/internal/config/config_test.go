package config

import (
	"os"
	"testing"
)

func TestLoad_WithRequiredEnvVars(t *testing.T) {
	// Set required environment variable
	os.Setenv("JWT_SECRET_KEY", "test-secret-key")
	defer os.Unsetenv("JWT_SECRET_KEY")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	if cfg.JWTSecretKey != "test-secret-key" {
		t.Errorf("Expected JWT_SECRET_KEY to be 'test-secret-key', got: %s", cfg.JWTSecretKey)
	}
}

func TestLoad_WithoutRequiredEnvVars(t *testing.T) {
	// Clear all JWT related env vars
	os.Unsetenv("JWT_SECRET_KEY")

	_, err := Load()
	if err == nil {
		t.Fatal("Expected error when JWT_SECRET_KEY is not set, got nil")
	}
}

func TestLoad_DefaultValues(t *testing.T) {
	os.Setenv("JWT_SECRET_KEY", "test-secret")
	defer os.Unsetenv("JWT_SECRET_KEY")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Check default values
	if cfg.Port != 8000 {
		t.Errorf("Expected default Port to be 8000, got: %d", cfg.Port)
	}
	if cfg.Environment != "development" {
		t.Errorf("Expected default Environment to be 'development', got: %s", cfg.Environment)
	}
	if cfg.LogLevel != "info" {
		t.Errorf("Expected default LogLevel to be 'info', got: %s", cfg.LogLevel)
	}
	if cfg.JWTAlgorithm != "HS256" {
		t.Errorf("Expected default JWTAlgorithm to be 'HS256', got: %s", cfg.JWTAlgorithm)
	}
	if cfg.ConfigServiceURL != "http://localhost:8001" {
		t.Errorf("Expected default ConfigServiceURL to be 'http://localhost:8001', got: %s", cfg.ConfigServiceURL)
	}
	if cfg.RateLimitRPS != 100 {
		t.Errorf("Expected default RateLimitRPS to be 100, got: %d", cfg.RateLimitRPS)
	}
}

func TestLoad_CustomValues(t *testing.T) {
	os.Setenv("JWT_SECRET_KEY", "custom-secret")
	os.Setenv("GATEWAY_PORT", "9000")
	os.Setenv("ENVIRONMENT", "production")
	os.Setenv("LOG_LEVEL", "debug")
	os.Setenv("CONFIG_SERVICE_URL", "http://config:8001")
	os.Setenv("CORS_ORIGINS", "http://example.com,http://test.com")

	defer func() {
		os.Unsetenv("JWT_SECRET_KEY")
		os.Unsetenv("GATEWAY_PORT")
		os.Unsetenv("ENVIRONMENT")
		os.Unsetenv("LOG_LEVEL")
		os.Unsetenv("CONFIG_SERVICE_URL")
		os.Unsetenv("CORS_ORIGINS")
	}()

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	if cfg.Port != 9000 {
		t.Errorf("Expected Port to be 9000, got: %d", cfg.Port)
	}
	if cfg.Environment != "production" {
		t.Errorf("Expected Environment to be 'production', got: %s", cfg.Environment)
	}
	if cfg.LogLevel != "debug" {
		t.Errorf("Expected LogLevel to be 'debug', got: %s", cfg.LogLevel)
	}
	if cfg.ConfigServiceURL != "http://config:8001" {
		t.Errorf("Expected ConfigServiceURL to be 'http://config:8001', got: %s", cfg.ConfigServiceURL)
	}
	if len(cfg.CORSOrigins) != 2 {
		t.Errorf("Expected 2 CORS origins, got: %d", len(cfg.CORSOrigins))
	}
}

func TestConfig_IsDevelopment(t *testing.T) {
	tests := []struct {
		env      string
		expected bool
	}{
		{"development", true},
		{"production", false},
		{"staging", false},
		{"test", false},
	}

	for _, tc := range tests {
		cfg := &Config{Environment: tc.env}
		if got := cfg.IsDevelopment(); got != tc.expected {
			t.Errorf("IsDevelopment() for %s: expected %v, got %v", tc.env, tc.expected, got)
		}
	}
}

func TestParseCSV(t *testing.T) {
	tests := []struct {
		input    string
		expected []string
	}{
		{"", []string{}},
		{"a", []string{"a"}},
		{"a,b,c", []string{"a", "b", "c"}},
		{"a, b, c", []string{"a", "b", "c"}},
		{" a , b , c ", []string{"a", "b", "c"}},
		{"a,,b", []string{"a", "b"}},
	}

	for _, tc := range tests {
		result := parseCSV(tc.input)
		if len(result) != len(tc.expected) {
			t.Errorf("parseCSV(%q): expected %d elements, got %d", tc.input, len(tc.expected), len(result))
			continue
		}
		for i, v := range result {
			if v != tc.expected[i] {
				t.Errorf("parseCSV(%q)[%d]: expected %q, got %q", tc.input, i, tc.expected[i], v)
			}
		}
	}
}

func TestValidate_InvalidJWTAlgorithm(t *testing.T) {
	cfg := &Config{
		JWTSecretKey: "test",
		JWTAlgorithm: "RS256", // Invalid - only HS* supported
	}

	err := cfg.validate()
	if err == nil {
		t.Fatal("Expected error for invalid JWT algorithm, got nil")
	}
}

func TestValidate_ValidJWTAlgorithms(t *testing.T) {
	algorithms := []string{"HS256", "HS384", "HS512"}

	for _, alg := range algorithms {
		cfg := &Config{
			JWTSecretKey: "test",
			JWTAlgorithm: alg,
		}
		if err := cfg.validate(); err != nil {
			t.Errorf("Expected no error for algorithm %s, got: %v", alg, err)
		}
	}
}

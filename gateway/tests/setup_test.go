//go:build integration

package tests

import (
	"fmt"
	"net/http"
	"os"
	"testing"
	"time"
)

var (
	gatewayURL       string
	configServiceURL string
	jwtSecretKey     string
)

func TestMain(m *testing.M) {
	// Load configuration from environment
	gatewayURL = getEnvOrDefault("GATEWAY_URL", "http://localhost:8000")
	configServiceURL = getEnvOrDefault("CONFIG_SERVICE_URL", "http://localhost:8001")
	jwtSecretKey = getEnvOrDefault("JWT_SECRET_KEY", "test-secret-key-for-integration-tests")

	// Check if Config Service is available
	if !waitForService(configServiceURL+"/health", 10*time.Second) {
		fmt.Println("WARNING: Config Service is not available at", configServiceURL)
		fmt.Println("Some integration tests will be skipped")
	}

	// Run tests
	code := m.Run()

	// Cleanup could go here if needed

	os.Exit(code)
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// waitForService waits for a service to become available
func waitForService(url string, timeout time.Duration) bool {
	client := &http.Client{Timeout: 2 * time.Second}
	deadline := time.Now().Add(timeout)

	for time.Now().Before(deadline) {
		resp, err := client.Get(url)
		if err == nil {
			resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				return true
			}
		}
		time.Sleep(500 * time.Millisecond)
	}
	return false
}

// isConfigServiceAvailable checks if the Config Service is reachable
func isConfigServiceAvailable() bool {
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(configServiceURL + "/health")
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

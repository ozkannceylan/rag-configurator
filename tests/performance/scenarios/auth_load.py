"""
Authentication load testing scenarios.

Tests the authentication system's ability to handle concurrent logins,
token generation, and refresh operations under load.

Target Metrics:
- 100 concurrent login attempts
- < 500ms p95 response time for login
- < 1% error rate
- Token refresh latency < 200ms

Usage:
    locust -f scenarios/auth_load.py --host=http://localhost:8000
"""

import os
from locust import HttpUser, task, between, events
from locust.exception import StopUser


class AuthLoadUser(HttpUser):
    """
    User class for authentication load testing.
    
    Simulates concurrent authentication operations including:
    - Login with valid credentials
    - Login with invalid credentials (failure testing)
    - Token refresh operations
    - Concurrent token validation
    
    Load Profile:
    - Ramp up: 100 users over 60 seconds
    - Sustained: 100 users for 5 minutes
    - Ramp down: 0 users over 30 seconds
    """
    
    wait_time = between(1, 3)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.refresh_token = None
        self.login_success = False
    
    def on_start(self):
        """
        Start with login to establish baseline.
        """
        self._perform_login()
    
    def _perform_login(self):
        """
        Perform login with test credentials.
        Tracks success rate and latency.
        """
        email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        password = os.getenv("TEST_USER_PASSWORD", "testpassword")
        
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password
            },
            name="auth/login"
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.login_success = True
        else:
            self.login_success = False
            raise StopUser()
    
    @task(weight=10)
    def concurrent_login_load(self):
        """
        Simulate multiple concurrent login attempts.
        Tests authentication service capacity.
        
        Weight: 10 (primary load test)
        """
        email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        password = os.getenv("TEST_USER_PASSWORD", "testpassword")
        
        with self.client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password
            },
            catch_response=True,
            name="auth/concurrent_login"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited - too many concurrent requests")
            elif response.status_code == 503:
                response.failure("Service unavailable - auth service overloaded")
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    @task(weight=5)
    def token_refresh_load(self):
        """
        Test token refresh under load.
        Validates refresh token rotation and validation.
        
        Weight: 5
        """
        if not self.refresh_token:
            return
        
        with self.client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {self.refresh_token}"},
            catch_response=True,
            name="auth/refresh_token"
        ) as response:
            if response.status_code == 200:
                data = response.json().get("data", {})
                self.access_token = data.get("access_token")
                response.success()
            elif response.status_code == 401:
                response.failure("Refresh token expired or invalid")
            else:
                response.failure(f"Token refresh failed: {response.status_code}")
    
    @task(weight=3)
    def invalid_login_attempts(self):
        """
        Test authentication with invalid credentials.
        Validates proper error handling and rate limiting.
        
        Weight: 3
        """
        with self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "invalid@example.com",
                "password": "wrongpassword"
            },
            catch_response=True,
            name="auth/invalid_login"
        ) as response:
            if response.status_code == 401:
                response.success()  # Expected failure
            elif response.status_code == 429:
                response.success()  # Rate limiting working
            else:
                response.failure(f"Unexpected response: {response.status_code}")
    
    @task(weight=2)
    def token_validation_load(self):
        """
        Test token validation with concurrent API calls.
        Tests middleware performance.
        
        Weight: 2
        """
        if not self.access_token:
            return
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        with self.client.get(
            "/api/v1/configs",
            headers=headers,
            catch_response=True,
            name="auth/token_validation"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Token validation failed")
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class BurstAuthUser(HttpUser):
    """
    Simulates burst authentication traffic.
    Used for testing spike handling.
    """
    
    wait_time = between(0.1, 0.5)
    
    @task
    def burst_login(self):
        """
        Rapid login attempts to simulate traffic spike.
        """
        email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        password = os.getenv("TEST_USER_PASSWORD", "testpassword")
        
        self.client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password
            },
            name="auth/burst_login"
        )


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, 
               response, context, exception, **kwargs):
    """
    Track authentication-specific metrics.
    """
    if name.startswith("auth/") and response_time > 500:
        print(f"WARNING: Slow auth request - {name}: {response_time}ms")

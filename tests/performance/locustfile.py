"""
Performance testing configuration for RAG Configurator.

This Locust file defines realistic user behavior for load testing
the RAG Configurator API endpoints.

Usage:
    locust -f locustfile.py --host=http://localhost:8000

Configuration:
    Set environment variables:
    - TEST_USER_EMAIL: Email for test user (default: test@example.com)
    - TEST_USER_PASSWORD: Password for test user (default: testpassword)
    - GATEWAY_HOST: Gateway URL (default: http://localhost:8000)
"""

import os
import random
from typing import Optional

from locust import HttpUser, task, between, events


class RAGUser(HttpUser):
    """
    Simulates a typical RAG user interacting with the system.
    
    User behavior:
    - Authenticates on startup
    - Performs read operations (70% weight)
    - Performs RAG queries (30% weight)
    - Includes think time between requests
    """
    
    wait_time = between(1, 5)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.config_ids: list[str] = []
    
    def on_start(self):
        """
        Called when a simulated user starts.
        Performs authentication and initial setup.
        """
        self._login()
        if self.access_token:
            self._load_configs()
    
    def _login(self):
        """
        Authenticate the user and obtain tokens.
        Uses credentials from environment variables.
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
            self.user_id = data.get("user", {}).get("id")
            
            events.request.fire(
                request_type="AUTH",
                name="login_success",
                response_time=response.elapsed.total_seconds() * 1000,
                response_length=len(response.content),
                response=response,
                context=None,
                exception=None
            )
        else:
            events.request.fire(
                request_type="AUTH",
                name="login_failed",
                response_time=response.elapsed.total_seconds() * 1000,
                response_length=len(response.content),
                response=response,
                context=None,
                exception=Exception(f"Login failed: {response.status_code}")
            )
    
    def _load_configs(self):
        """
        Load available RAG configurations for the user.
        Stores config IDs for use in subsequent tasks.
        """
        headers = self._get_auth_headers()
        
        response = self.client.get(
            "/api/v1/configs",
            headers=headers,
            name="configs/list"
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            configs = data.get("items", [])
            self.config_ids = [cfg["id"] for cfg in configs]
    
    def _get_auth_headers(self) -> dict:
        """
        Returns authentication headers with Bearer token.
        
        Returns:
            Dictionary with Authorization header
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _refresh_token_if_needed(self):
        """
        Refresh the access token if it's about to expire.
        Called periodically to maintain session.
        """
        if not self.refresh_token:
            return
        
        response = self.client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {self.refresh_token}"},
            name="auth/refresh"
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            self.access_token = data.get("access_token")
    
    @task(weight=1)
    def list_configs(self):
        """
        Task: List user's RAG configurations.
        Weight: 1 (lower priority than queries)
        
        Simulates users browsing their configurations.
        """
        if not self.access_token:
            return
        
        headers = self._get_auth_headers()
        
        with self.client.get(
            "/api/v1/configs",
            headers=headers,
            catch_response=True,
            name="configs/list"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized - token may be expired")
                self._refresh_token_if_needed()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(weight=3)
    def query_rag(self):
        """
        Task: Send RAG query to the system.
        Weight: 3 (higher priority - main use case)
        
        Simulates users asking questions to the RAG pipeline.
        Uses random queries and available configurations.
        """
        if not self.access_token or not self.config_ids:
            return
        
        config_id = random.choice(self.config_ids)
        query = random.choice([
            "What is the main concept discussed in the document?",
            "Summarize the key findings",
            "List the important points from section 1",
            "Compare and contrast the approaches mentioned",
            "What are the limitations of the proposed method?",
            "Explain the methodology used in the research",
            "What conclusions were drawn from the analysis?",
            "How does this relate to previous work?",
            "What future work is suggested?",
            "Define the technical terms used in section 2"
        ])
        
        headers = self._get_auth_headers()
        
        with self.client.post(
            "/api/v1/query",
            headers=headers,
            json={
                "config_id": config_id,
                "query": query,
                "stream": False
            },
            catch_response=True,
            name="rag/query"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized - token may be expired")
                self._refresh_token_if_needed()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Query failed: {response.status_code}")
    
    @task(weight=1)
    def get_config_details(self):
        """
        Task: Get details of a specific configuration.
        Weight: 1
        
        Simulates users viewing configuration details.
        """
        if not self.access_token or not self.config_ids:
            return
        
        config_id = random.choice(self.config_ids)
        headers = self._get_auth_headers()
        
        with self.client.get(
            f"/api/v1/configs/{config_id}",
            headers=headers,
            catch_response=True,
            name="configs/get"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get config: {response.status_code}")


class PeakLoadUser(RAGUser):
    """
    Simulates peak load conditions with minimal wait time.
    Used for stress testing the system.
    """
    wait_time = between(0.1, 0.5)
    weight = 0.1  # 10% of users during peak


class SustainedUser(RAGUser):
    """
    Simulates sustained load with realistic think time.
    Used for endurance testing.
    """
    wait_time = between(2, 8)
    weight = 0.9  # 90% of users for sustained load


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Called when the load test starts.
    Logs test configuration and validates environment.
    """
    print("=" * 60)
    print("RAG Configurator Performance Test Starting")
    print("=" * 60)
    print(f"Host: {environment.host}")
    print(f"Test User: {os.getenv('TEST_USER_EMAIL', 'test@example.com')}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Called when the load test stops.
    Logs completion and summary statistics.
    """
    print("=" * 60)
    print("Performance Test Completed")
    print("=" * 60)

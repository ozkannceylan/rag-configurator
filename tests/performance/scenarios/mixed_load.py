"""
Mixed load testing scenario.

Simulates realistic production traffic with varied user behaviors:
- 70% query operations (main use case)
- 20% configuration viewing
- 10% CRUD operations

This scenario tests overall system stability under realistic conditions.

Usage:
    locust -f scenarios/mixed_load.py --host=http://localhost:8000
"""

import os
import random
import uuid
from datetime import datetime
from locust import HttpUser, task, between, events


class MixedLoadUser(HttpUser):
    """
    Simulates realistic mixed workload.
    
    Traffic Distribution:
    - 70% RAG queries (read-heavy)
    - 20% Configuration browsing (navigation)
    - 10% CRUD operations (data management)
    
    User Behavior:
    - Authenticates on start
    - Browses configs before querying
    - Occasionally creates/updates configs
    - Has realistic think times
    
    Load Profile:
    - Ramp up: 100 users over 180 seconds
    - Sustained: 100 users for 15 minutes
    - Ramp down: 0 users over 90 seconds
    """
    
    wait_time = between(3, 8)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.config_ids = []
        self.created_config_ids = []  # Track configs created by this user
    
    def on_start(self):
        """
        Initialize user session with authentication.
        """
        self._authenticate()
        if self.access_token:
            self._discover_configs()
    
    def _authenticate(self):
        """
        Authenticate and obtain tokens.
        """
        email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        password = os.getenv("TEST_USER_PASSWORD", "testpassword")
        
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="mixed/auth_login"
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.user_id = data.get("user", {}).get("id")
    
    def _discover_configs(self):
        """
        Load available configurations for this user.
        """
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        response = self.client.get(
            "/api/v1/configs",
            headers=headers,
            name="mixed/list_configs"
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            configs = data.get("items", [])
            self.config_ids = [cfg["id"] for cfg in configs]
    
    def _get_auth_headers(self):
        """Return authentication headers."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    # ==================== QUERY OPERATIONS (70%) ====================
    
    @task(weight=35)
    def simple_rag_query(self):
        """
        Simple RAG query - most common operation.
        Weight: 35% (of 70% = 35% total)
        """
        if not self.access_token or not self.config_ids:
            return
        
        queries = [
            "What is this document about?",
            "Summarize the content",
            "List the key points",
            "Explain the main concepts",
            "What are the findings?",
        ]
        
        config_id = random.choice(self.config_ids)
        headers = self._get_auth_headers()
        
        with self.client.post(
            "/api/v1/query",
            headers=headers,
            json={
                "config_id": config_id,
                "query": random.choice(queries),
                "stream": False
            },
            catch_response=True,
            name="mixed/query_simple"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Query failed: {response.status_code}")
    
    @task(weight=20)
    def detailed_rag_query(self):
        """
        Detailed RAG query with context.
        Weight: 20% (of 70% = 20% total)
        """
        if not self.access_token or not self.config_ids:
            return
        
        queries = [
            "Compare the approaches discussed in the document",
            "What are the advantages and disadvantages mentioned?",
            "Explain the methodology in detail",
            "What evidence supports the conclusions?",
        ]
        
        config_id = random.choice(self.config_ids)
        headers = self._get_auth_headers()
        
        with self.client.post(
            "/api/v1/query",
            headers=headers,
            json={
                "config_id": config_id,
                "query": random.choice(queries),
                "stream": False
            },
            catch_response=True,
            name="mixed/query_detailed"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Detailed query failed: {response.status_code}")
    
    @task(weight=15)
    def streaming_rag_query(self):
        """
        Streaming RAG query.
        Weight: 15% (of 70% = 15% total)
        """
        if not self.access_token or not self.config_ids:
            return
        
        config_id = random.choice(self.config_ids)
        headers = self._get_auth_headers()
        
        with self.client.post(
            "/api/v1/stream/chat",
            headers=headers,
            json={
                "config_id": config_id,
                "query": "Provide a detailed analysis",
                "stream": True
            },
            catch_response=True,
            name="mixed/query_streaming"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Streaming query failed: {response.status_code}")
    
    # ==================== CONFIG VIEWING (20%) ====================
    
    @task(weight=12)
    def list_all_configs(self):
        """
        List all configurations.
        Weight: 12% (of 20% = 12% total)
        """
        if not self.access_token:
            return
        
        headers = self._get_auth_headers()
        
        with self.client.get(
            "/api/v1/configs",
            headers=headers,
            catch_response=True,
            name="mixed/view_list_configs"
        ) as response:
            if response.status_code == 200:
                # Update config list
                data = response.json().get("data", {})
                configs = data.get("items", [])
                self.config_ids = [cfg["id"] for cfg in configs]
                response.success()
            else:
                response.failure(f"List configs failed: {response.status_code}")
    
    @task(weight=8)
    def view_config_details(self):
        """
        View specific configuration details.
        Weight: 8% (of 20% = 8% total)
        """
        if not self.access_token or not self.config_ids:
            return
        
        config_id = random.choice(self.config_ids)
        headers = self._get_auth_headers()
        
        with self.client.get(
            f"/api/v1/configs/{config_id}",
            headers=headers,
            catch_response=True,
            name="mixed/view_config_details"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"View config failed: {response.status_code}")
    
    # ==================== CRUD OPERATIONS (10%) ====================
    
    @task(weight=5)
    def create_config(self):
        """
        Create a new configuration.
        Weight: 5% (of 10% = 5% total)
        """
        if not self.access_token:
            return
        
        headers = self._get_auth_headers()
        config_name = f"LoadTest_Config_{uuid.uuid4().hex[:8]}"
        
        config_data = {
            "name": config_name,
            "description": f"Created during load test at {datetime.now().isoformat()}",
            "pipeline_config": {
                "retrieval": {
                    "strategy": "vector",
                    "top_k": 5
                },
                "generation": {
                    "model_provider": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "temperature": 0.7
                }
            }
        }
        
        with self.client.post(
            "/api/v1/configs",
            headers=headers,
            json=config_data,
            catch_response=True,
            name="mixed/crud_create_config"
        ) as response:
            if response.status_code == 201:
                # Track created config for cleanup
                data = response.json().get("data", {})
                config_id = data.get("id")
                if config_id:
                    self.created_config_ids.append(config_id)
                    self.config_ids.append(config_id)
                response.success()
            else:
                response.failure(f"Create config failed: {response.status_code}")
    
    @task(weight=3)
    def update_config(self):
        """
        Update an existing configuration.
        Weight: 3% (of 10% = 3% total)
        """
        if not self.access_token or not self.config_ids:
            return
        
        # Prefer configs created by this user
        config_pool = self.created_config_ids if self.created_config_ids else self.config_ids
        config_id = random.choice(config_pool)
        
        headers = self._get_auth_headers()
        
        update_data = {
            "description": f"Updated during load test at {datetime.now().isoformat()}",
            "pipeline_config": {
                "retrieval": {
                    "top_k": random.randint(3, 10)
                }
            }
        }
        
        with self.client.put(
            f"/api/v1/configs/{config_id}",
            headers=headers,
            json=update_data,
            catch_response=True,
            name="mixed/crud_update_config"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Update config failed: {response.status_code}")
    
    @task(weight=2)
    def delete_config(self):
        """
        Delete a configuration.
        Weight: 2% (of 10% = 2% total)
        
        Only deletes configs created during this test.
        """
        if not self.access_token or not self.created_config_ids:
            return
        
        config_id = self.created_config_ids.pop()
        headers = self._get_auth_headers()
        
        with self.client.delete(
            f"/api/v1/configs/{config_id}",
            headers=headers,
            catch_response=True,
            name="mixed/crud_delete_config"
        ) as response:
            if response.status_code == 204:
                # Remove from available configs
                if config_id in self.config_ids:
                    self.config_ids.remove(config_id)
                response.success()
            else:
                response.failure(f"Delete config failed: {response.status_code}")
    
    def on_stop(self):
        """
        Cleanup: Delete any configs created during the test.
        """
        if not self.access_token or not self.created_config_ids:
            return
        
        headers = self._get_auth_headers()
        
        for config_id in self.created_config_ids:
            self.client.delete(
                f"/api/v1/configs/{config_id}",
                headers=headers,
                name="mixed/cleanup_delete"
            )


class PowerUser(HttpUser):
    """
    Simulates power users with higher frequency operations.
    Represents 10% of user base but generates 30% of traffic.
    """
    
    wait_time = between(1, 3)
    weight = 0.1
    
    def on_start(self):
        """Quick authentication."""
        email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        password = os.getenv("TEST_USER_PASSWORD", "testpassword")
        
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="power/auth_login"
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            self.access_token = data.get("access_token")
            
            # Get first available config
            headers = {"Authorization": f"Bearer {self.access_token}"}
            resp = self.client.get(
                "/api/v1/configs",
                headers=headers,
                name="power/list_configs"
            )
            
            if resp.status_code == 200:
                configs = resp.json().get("data", {}).get("items", [])
                self.config_id = configs[0]["id"] if configs else None
        else:
            self.access_token = None
            self.config_id = None
    
    @task(weight=80)
    def rapid_queries(self):
        """
        Rapid-fire queries for power users.
        """
        if not self.access_token or not self.config_id:
            return
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        queries = [
            "Quick summary",
            "Key points",
            "Main idea",
            "Overview",
        ]
        
        self.client.post(
            "/api/v1/query",
            headers=headers,
            json={
                "config_id": self.config_id,
                "query": random.choice(queries),
                "stream": False
            },
            name="power/rapid_query"
        )
    
    @task(weight=20)
    def check_configs(self):
        """
        Periodically check configurations.
        """
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        self.client.get(
            "/api/v1/configs",
            headers=headers,
            name="power/check_configs"
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Log mixed load test configuration.
    """
    print("=" * 70)
    print("MIXED LOAD TEST STARTING")
    print("=" * 70)
    print("Traffic Distribution:")
    print("  - 70% Query operations (35% simple, 20% detailed, 15% streaming)")
    print("  - 20% Config viewing (12% list, 8% details)")
    print("  - 10% CRUD operations (5% create, 3% update, 2% delete)")
    print("=" * 70)

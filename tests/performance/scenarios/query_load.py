"""
RAG Query load testing scenarios.

Tests the RAG service's ability to handle concurrent queries
with varying complexity and query lengths.

Target Metrics:
- 50 concurrent queries
- < 2000ms p95 response time
- < 5% error rate
- Support for various query types (short, medium, long)

Usage:
    locust -f scenarios/query_load.py --host=http://localhost:8000
"""

import os
import random
from locust import HttpUser, task, between, events


# Query templates for different complexity levels
SHORT_QUERIES = [
    "What is RAG?",
    "Define embeddings",
    "Explain chunking",
    "What is a vector store?",
    "Define LLM",
    "What is prompting?",
    "Explain retrieval",
]

MEDIUM_QUERIES = [
    "What are the main benefits of using RAG over fine-tuning?",
    "How does vector similarity search work in document retrieval?",
    "Explain the difference between dense and sparse retrieval methods.",
    "What are common chunking strategies for long documents?",
    "How do you evaluate the quality of RAG responses?",
    "What is the role of re-ranking in retrieval systems?",
]

LONG_QUERIES = [
    "Compare and contrast the different retrieval strategies including vector search, keyword search, "
    "and hybrid approaches. What are the trade-offs in terms of accuracy, latency, and cost? "
    "Provide specific examples of when each approach is most effective.",
    
    "Describe the complete pipeline for building a production RAG system from document ingestion "
    "through query processing. Include details on preprocessing, embedding generation, "
    "indexing strategies, query optimization, and response generation.",
    
    "Analyze the impact of different chunking strategies on retrieval performance. "
    "Discuss fixed-size chunking, semantic chunking, and document-aware chunking. "
    "How does chunk size affect context preservation and retrieval accuracy?",
]

QUERY_TYPES = {
    "short": {"queries": SHORT_QUERIES, "weight": 40},
    "medium": {"queries": MEDIUM_QUERIES, "weight": 45},
    "long": {"queries": LONG_QUERIES, "weight": 15},
}


class QueryLoadUser(HttpUser):
    """
    User class for RAG query load testing.
    
    Simulates concurrent RAG queries with:
    - Various query lengths (short/medium/long)
    - Different configurations
    - Streaming and non-streaming modes
    - Concurrent requests per user
    
    Load Profile:
    - Ramp up: 50 users over 120 seconds
    - Sustained: 50 users for 10 minutes
    - Ramp down: 0 users over 60 seconds
    """
    
    wait_time = between(2, 5)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.config_ids = []
        self.user_id = None
    
    def on_start(self):
        """
        Authenticate and load available configurations.
        """
        self._login()
        if self.access_token:
            self._load_configs()
    
    def _login(self):
        """Authenticate user."""
        email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        password = os.getenv("TEST_USER_PASSWORD", "testpassword")
        
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="query_load/login"
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            self.access_token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
    
    def _load_configs(self):
        """Load available RAG configurations."""
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        response = self.client.get(
            "/api/v1/configs",
            headers=headers,
            name="query_load/list_configs"
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            configs = data.get("items", [])
            self.config_ids = [cfg["id"] for cfg in configs]
    
    def _get_query_by_type(self, query_type: str) -> str:
        """
        Get a random query of specified type.
        
        Args:
            query_type: Type of query (short, medium, long)
            
        Returns:
            Random query string
        """
        queries = QUERY_TYPES[query_type]["queries"]
        return random.choice(queries)
    
    def _send_rag_query(self, query: str, stream: bool = False) -> None:
        """
        Send a RAG query to the system.
        
        Args:
            query: The query string
            stream: Whether to use streaming mode
        """
        if not self.access_token or not self.config_ids:
            return
        
        config_id = random.choice(self.config_ids)
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        endpoint = "/api/v1/stream/chat" if stream else "/api/v1/query"
        
        with self.client.post(
            endpoint,
            headers=headers,
            json={
                "config_id": config_id,
                "query": query,
                "stream": stream
            },
            catch_response=True,
            name=f"rag/query_{'stream' if stream else 'sync'}"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            elif response.status_code == 503:
                response.failure("RAG service unavailable")
            elif response.status_code >= 500:
                response.failure(f"Server error: {response.status_code}")
            else:
                response.failure(f"Query failed: {response.status_code}")
    
    @task(weight=40)
    def short_query_load(self):
        """
        Test with short queries.
        Weight: 40%
        
        Short queries test basic retrieval performance.
        """
        query = self._get_query_by_type("short")
        self._send_rag_query(query, stream=False)
    
    @task(weight=45)
    def medium_query_load(self):
        """
        Test with medium-length queries.
        Weight: 45%
        
        Medium queries represent typical user interactions.
        """
        query = self._get_query_by_type("medium")
        self._send_rag_query(query, stream=False)
    
    @task(weight=15)
    def long_query_load(self):
        """
        Test with complex, long queries.
        Weight: 15%
        
        Long queries test complex retrieval and generation.
        """
        query = self._get_query_by_type("long")
        self._send_rag_query(query, stream=False)
    
    @task(weight=10)
    def streaming_query_load(self):
        """
        Test streaming response mode.
        Weight: 10%
        
        Streaming queries test connection stability.
        """
        query = self._get_query_by_type("medium")
        self._send_rag_query(query, stream=True)
    
    @task(weight=5)
    def concurrent_queries(self):
        """
        Send multiple concurrent queries.
        Weight: 5%
        
        Tests system handling of parallel requests.
        """
        if not self.access_token or not self.config_ids:
            return
        
        # Send 3 concurrent queries
        queries = [
            self._get_query_by_type("short"),
            self._get_query_by_type("medium"),
            self._get_query_by_type("short"),
        ]
        
        for query in queries:
            self._send_rag_query(query, stream=False)


class HighThroughputUser(HttpUser):
    """
    Simulates high-throughput query load.
    Minimal think time for stress testing.
    """
    
    wait_time = between(0.5, 1.5)
    
    def on_start(self):
        """Authenticate user."""
        email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        password = os.getenv("TEST_USER_PASSWORD", "testpassword")
        
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="high_throughput/login"
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            self.access_token = data.get("access_token")
            
            # Load first config
            headers = {"Authorization": f"Bearer {self.access_token}"}
            resp = self.client.get(
                "/api/v1/configs",
                headers=headers,
                name="high_throughput/list_configs"
            )
            
            if resp.status_code == 200:
                configs = resp.json().get("data", {}).get("items", [])
                if configs:
                    self.config_id = configs[0]["id"]
                else:
                    self.config_id = None
        else:
            self.access_token = None
            self.config_id = None
    
    @task
    def high_frequency_queries(self):
        """
        Rapid-fire queries for throughput testing.
        """
        if not self.access_token or not self.config_id:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        query = random.choice(SHORT_QUERIES)
        
        self.client.post(
            "/api/v1/query",
            headers=headers,
            json={
                "config_id": self.config_id,
                "query": query,
                "stream": False
            },
            name="high_throughput/query"
        )


@events.request.add_listener
def on_request(request_type, name, response_time, response_length,
               response, context, exception, **kwargs):
    """
    Track query-specific performance metrics.
    Log warnings for slow queries.
    """
    if "rag/query" in name and response_time > 2000:
        print(f"WARNING: Slow RAG query - {name}: {response_time}ms")
    
    if exception:
        print(f"ERROR: Query failed - {name}: {exception}")

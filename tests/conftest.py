"""
conftest.py - Pytest configuration and fixtures

Provides:
- FastAPI test client
- Database fixtures
- Cache fixtures
- Mock data
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from backend.main import app
from backend.core.database import global_connection_pool, ConnectionPool
from backend.core.caching import Cache, global_cache
from backend.core.load_balancer import LoadBalancer, LoadBalancingStrategy


@pytest.fixture(scope="session")
def test_client():
    """Create a test client for API testing"""
    return TestClient(app)


@pytest.fixture(scope="function")
def clean_cache():
    """Provide a clean cache for each test"""
    cache = Cache(max_size=100)
    yield cache
    cache.clear()


@pytest.fixture(scope="function")
def test_connection_pool():
    """Create a test connection pool"""
    pool = ConnectionPool(min_connections=2, max_connections=5)
    yield pool


@pytest.fixture(scope="function")
def test_load_balancer():
    """Create a test load balancer"""
    lb = LoadBalancer(LoadBalancingStrategy.LEAST_CONNECTIONS)
    lb.add_server("localhost", 8000, weight=1)
    lb.add_server("localhost", 8001, weight=1)
    yield lb


@pytest.fixture
def sample_calculate_payload():
    """Sample payload for calculate endpoint"""
    return {
        "gig_type": "rideshare",
        "hours_worked": 8,
        "earnings": 150.0,
        "incidents": [
            {"type": "accident", "severity": "low", "date": "2024-01-15"}
        ],
    }


@pytest.fixture
def sample_risk_payload():
    """Sample payload for risk endpoint"""
    return {
        "gig_type": "delivery",
        "worker_profile": {
            "age": 35,
            "experience_years": 5,
            "accident_count": 1,
        },
        "monthly_hours": 160,
    }


@pytest.fixture
def sample_simulate_payload():
    """Sample payload for simulate endpoint"""
    return {
        "gig_type": "rideshare",
        "duration_months": 12,
        "monthly_earnings": 2000,
        "risk_profile": "standard",
        "num_simulations": 100,
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment"""
    import os
    os.environ["TESTING"] = "true"
    yield
    os.environ.pop("TESTING", None)

"""
test_api_integration.py - Integration tests for API endpoints
"""

import pytest


@pytest.mark.integration
class TestMonitoringEndpoints:
    def test_metrics_endpoint(self, test_client):
        response = test_client.get("/api/monitoring/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "request_metrics" in data
        assert "endpoint_metrics" in data

    def test_health_endpoint(self, test_client):
        response = test_client.get("/api/monitoring/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data

    def test_database_stats_endpoint(self, test_client):
        response = test_client.get("/api/monitoring/database/stats")
        assert response.status_code == 200
        data = response.json()
        assert "pool_stats" in data
        assert "query_metrics" in data

    def test_cache_stats_endpoint(self, test_client):
        response = test_client.get("/api/monitoring/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "cache_stats" in data

    def test_load_balancer_stats_endpoint(self, test_client):
        response = test_client.get("/api/monitoring/load-balancer/stats")
        assert response.status_code == 200
        data = response.json()
        assert "overall_stats" in data
        assert "server_stats" in data

    def test_system_overview_endpoint(self, test_client):
        response = test_client.get("/api/monitoring/system/overview")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "health" in data
        assert "performance" in data


@pytest.mark.integration
class TestRootEndpoint:
    def test_root_endpoint(self, test_client):
        response = test_client.get("/")
        assert response.status_code in [200, 404]


@pytest.mark.integration
class TestAPIErrorHandling:
    def test_invalid_endpoint_returns_404(self, test_client):
        response = test_client.get("/api/invalid/endpoint")
        assert response.status_code == 404

    def test_monitoring_endpoints_are_accessible(self, test_client):
        endpoints = [
            "/api/monitoring/metrics",
            "/api/monitoring/health",
            "/api/monitoring/database/stats",
            "/api/monitoring/cache/stats",
        ]

        for endpoint in endpoints:
            response = test_client.get(endpoint)
            assert response.status_code == 200

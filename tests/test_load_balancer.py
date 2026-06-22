"""
test_load_balancer.py - Tests for load balancing functionality
"""

import pytest
from backend.core.load_balancer import (
    Server,
    LoadBalancer,
    LoadBalancingStrategy,
)


@pytest.mark.unit
class TestServer:
    def test_server_creation(self):
        server = Server("localhost", 8000, weight=1)
        assert server.host == "localhost"
        assert server.port == 8000
        assert server.is_healthy

    def test_record_request_success(self):
        server = Server("localhost", 8000)
        server.record_request(100.0, success=True)

        assert server.total_requests == 1
        assert server.consecutive_failures == 0

    def test_record_request_failure(self):
        server = Server("localhost", 8000)
        server.record_request(100.0, success=False)

        assert server.consecutive_failures == 1

    def test_server_becomes_unhealthy_on_failures(self):
        server = Server("localhost", 8000)
        for i in range(5):
            server.record_request(100.0, success=False)

        assert not server.is_healthy

    def test_get_load(self):
        server = Server("localhost", 8000, weight=2)
        server.active_connections = 4

        load = server.get_load()
        assert load == 2.0


@pytest.mark.unit
class TestLoadBalancer:
    def test_load_balancer_creation(self, test_load_balancer):
        assert len(test_load_balancer.servers) == 2

    def test_add_server(self, test_load_balancer):
        test_load_balancer.add_server("localhost", 8002)
        assert len(test_load_balancer.servers) == 3

    def test_remove_server(self, test_load_balancer):
        test_load_balancer.remove_server("localhost", 8000)
        assert len(test_load_balancer.servers) == 1

    def test_select_server_round_robin(self):
        lb = LoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)
        lb.add_server("localhost", 8000)
        lb.add_server("localhost", 8001)

        server1 = lb.select_server()
        server2 = lb.select_server()

        assert server1.port != server2.port

    def test_select_server_least_connections(self):
        lb = LoadBalancer(LoadBalancingStrategy.LEAST_CONNECTIONS)
        server1 = lb.add_server("localhost", 8000)
        server2 = lb.add_server("localhost", 8001)

        server1.active_connections = 10
        server2.active_connections = 2

        selected = lb.select_server()
        assert selected.port == 8001

    def test_record_response(self, test_load_balancer):
        server = test_load_balancer.servers[0]
        test_load_balancer.record_response(server, 100.0, success=True)

        assert test_load_balancer.stats["total_requests"] == 1

    def test_get_overall_stats(self, test_load_balancer):
        stats = test_load_balancer.get_overall_stats()

        assert "total_servers" in stats
        assert "healthy_servers" in stats
        assert "strategy" in stats

    def test_health_check_all(self, test_load_balancer):
        health = test_load_balancer.health_check_all()

        assert "servers" in health
        assert "summary" in health

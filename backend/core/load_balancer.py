"""
load_balancer.py - Load balancing and request distribution

Implements:
- Round-robin load balancing
- Weighted load balancing
- Least-connections strategy
- Health-aware routing
"""

import time
from typing import List, Optional, Dict
from enum import Enum


class LoadBalancingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    RANDOM = "random"


class Server:
    def __init__(self, host: str, port: int, weight: int = 1):
        self.host = host
        self.port = port
        self.weight = weight
        self.active_connections = 0
        self.total_requests = 0
        self.total_response_time = 0
        self.last_health_check = time.time()
        self.is_healthy = True
        self.error_count = 0
        self.consecutive_failures = 0

    def record_request(self, response_time: float, success: bool = True):
        self.total_requests += 1
        self.total_response_time += response_time

        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.error_count += 1

        if self.consecutive_failures >= 5:
            self.is_healthy = False

    def get_load(self) -> float:
        return self.active_connections / max(1, self.weight)

    def get_avg_response_time(self) -> float:
        if self.total_requests == 0:
            return 0
        return self.total_response_time / self.total_requests

    def health_check(self) -> bool:
        if time.time() - self.last_health_check > 60:
            if self.error_count < 5:
                self.is_healthy = True
            self.last_health_check = time.time()

        return self.is_healthy

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "weight": self.weight,
            "active_connections": self.active_connections,
            "total_requests": self.total_requests,
            "avg_response_time_ms": round(self.get_avg_response_time(), 2),
            "is_healthy": self.is_healthy,
            "error_count": self.error_count,
            "load": round(self.get_load(), 2),
        }


class LoadBalancer:
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS):
        self.servers: List[Server] = []
        self.strategy = strategy
        self.current_index = 0
        self.stats = {
            "total_requests": 0,
            "total_response_time": 0,
            "errors": 0,
        }

    def add_server(self, host: str, port: int, weight: int = 1) -> Server:
        server = Server(host, port, weight)
        self.servers.append(server)
        return server

    def remove_server(self, host: str, port: int) -> bool:
        self.servers = [
            s for s in self.servers if not (s.host == host and s.port == port)
        ]
        return True

    def select_server(self) -> Optional[Server]:
        healthy_servers = [s for s in self.servers if s.health_check()]

        if not healthy_servers:
            healthy_servers = self.servers

        if not healthy_servers:
            return None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            return self._weighted(healthy_servers)
        else:
            return healthy_servers[0]

    def _round_robin(self, servers: List[Server]) -> Server:
        server = servers[self.current_index % len(servers)]
        self.current_index += 1
        return server

    def _least_connections(self, servers: List[Server]) -> Server:
        return min(servers, key=lambda s: s.active_connections)

    def _weighted(self, servers: List[Server]) -> Server:
        return min(servers, key=lambda s: s.get_load())

    def get_server_stats(self) -> list:
        return [s.to_dict() for s in self.servers]

    def get_overall_stats(self) -> dict:
        avg_response_time = (
            self.stats["total_response_time"] / self.stats["total_requests"]
            if self.stats["total_requests"] > 0
            else 0
        )

        healthy_servers = sum(1 for s in self.servers if s.is_healthy)

        return {
            "total_servers": len(self.servers),
            "healthy_servers": healthy_servers,
            "unhealthy_servers": len(self.servers) - healthy_servers,
            "total_requests": self.stats["total_requests"],
            "avg_response_time_ms": round(avg_response_time, 2),
            "error_count": self.stats["errors"],
            "error_rate": (
                f"{(self.stats['errors'] / self.stats['total_requests'] * 100):.1f}%"
                if self.stats["total_requests"] > 0
                else "0%"
            ),
            "strategy": self.strategy.value,
        }

    def record_response(self, server: Server, response_time: float, success: bool = True):
        server.record_request(response_time, success)
        self.stats["total_requests"] += 1
        self.stats["total_response_time"] += response_time

        if not success:
            self.stats["errors"] += 1

    def health_check_all(self) -> dict:
        for server in self.servers:
            server.health_check()

        return {
            "timestamp": time.time(),
            "servers": self.get_server_stats(),
            "summary": self.get_overall_stats(),
        }


def create_default_load_balancer() -> LoadBalancer:
    lb = LoadBalancer(LoadBalancingStrategy.LEAST_CONNECTIONS)

    lb.add_server("localhost", 8000, weight=2)
    lb.add_server("localhost", 8001, weight=1)
    lb.add_server("localhost", 8002, weight=1)

    return lb


global_load_balancer = create_default_load_balancer()

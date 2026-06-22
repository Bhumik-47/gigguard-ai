"""
database.py - Database optimization and connection pooling for scalability

Implements:
- Connection pooling for efficient resource management
- Query optimization patterns
- Database performance monitoring
- Connection health checks
"""

from typing import Optional, Any
import time
from contextlib import contextmanager
from functools import lru_cache


class DatabaseConnection:
    def __init__(self, connection_id: str, created_at: float = None):
        self.id = connection_id
        self.created_at = created_at or time.time()
        self.last_used = time.time()
        self.query_count = 0
        self.error_count = 0
        self.is_active = True

    def record_query(self, success: bool = True):
        self.last_used = time.time()
        if success:
            self.query_count += 1
        else:
            self.error_count += 1

    def is_healthy(self) -> bool:
        return self.error_count < 5 and self.is_active

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "query_count": self.query_count,
            "error_count": self.error_count,
            "is_healthy": self.is_healthy(),
        }


class ConnectionPool:
    def __init__(
        self,
        min_connections: int = 5,
        max_connections: int = 20,
        idle_timeout: int = 300,
    ):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self.pool = []
        self.in_use = set()
        self.stats = {
            "total_created": 0,
            "total_reused": 0,
            "total_errors": 0,
            "max_wait_time": 0,
        }

        self._initialize_pool()

    def _initialize_pool(self):
        for i in range(self.min_connections):
            conn = DatabaseConnection(f"conn_{i}")
            self.pool.append(conn)
            self.stats["total_created"] += 1

    def acquire_connection(self, timeout: int = 5000) -> Optional[DatabaseConnection]:
        start_time = time.time()

        available = [c for c in self.pool if c.id not in self.in_use and c.is_healthy()]

        if available:
            conn = available[0]
            self.in_use.add(conn.id)
            self.stats["total_reused"] += 1
            return conn

        if len(self.pool) < self.max_connections:
            conn = DatabaseConnection(f"conn_{len(self.pool)}")
            self.pool.append(conn)
            self.in_use.add(conn.id)
            self.stats["total_created"] += 1
            return conn

        while (time.time() - start_time) * 1000 < timeout:
            available = [c for c in self.pool if c.id not in self.in_use and c.is_healthy()]
            if available:
                conn = available[0]
                self.in_use.add(conn.id)
                self.stats["total_reused"] += 1
                wait_time = (time.time() - start_time) * 1000
                self.stats["max_wait_time"] = max(self.stats["max_wait_time"], wait_time)
                return conn
            time.sleep(0.01)

        self.stats["total_errors"] += 1
        return None

    def release_connection(self, connection: DatabaseConnection):
        if connection and connection.id in self.in_use:
            self.in_use.remove(connection.id)
            connection.last_used = time.time()

    def cleanup_idle_connections(self):
        current_time = time.time()
        to_remove = [
            c
            for c in self.pool
            if c.id not in self.in_use
            and (current_time - c.last_used) > self.idle_timeout
            and len(self.pool) > self.min_connections
        ]

        for conn in to_remove:
            self.pool.remove(conn)
            self.stats["total_destroyed"] = self.stats.get("total_destroyed", 0) + 1

        return len(to_remove)

    def get_stats(self) -> dict:
        return {
            **self.stats,
            "active_connections": len(self.in_use),
            "pool_size": len(self.pool),
            "utilization": f"{(len(self.in_use) / len(self.pool) * 100):.1f}%",
        }

    def get_connection_details(self) -> list:
        return [c.to_dict() for c in self.pool]

    def health_check(self) -> dict:
        healthy = [c for c in self.pool if c.is_healthy()]
        return {
            "total_connections": len(self.pool),
            "healthy_connections": len(healthy),
            "unhealthy_connections": len(self.pool) - len(healthy),
            "status": "healthy" if len(healthy) >= self.min_connections else "degraded",
        }


class QueryOptimizer:
    @staticmethod
    def index_recommendations(query_pattern: str) -> list:
        recommendations = []

        if "WHERE" in query_pattern.upper() and "JOIN" in query_pattern.upper():
            recommendations.append("Add composite index on joined columns")

        if query_pattern.count("OR") > 2:
            recommendations.append("Consider denormalization or materialized views")

        if "LIKE" in query_pattern.upper():
            recommendations.append("Use full-text search or trigram indexes")

        return recommendations

    @staticmethod
    def analyze_slow_query(query: str, execution_time: float) -> dict:
        is_slow = execution_time > 100

        return {
            "query": query[:100],
            "execution_time_ms": execution_time,
            "is_slow": is_slow,
            "recommendations": QueryOptimizer.index_recommendations(query),
        }


class DatabaseMetrics:
    def __init__(self):
        self.queries_executed = 0
        self.total_execution_time = 0
        self.slow_queries = []
        self.error_count = 0

    def record_query_execution(self, query: str, execution_time: float, success: bool = True):
        self.queries_executed += 1
        self.total_execution_time += execution_time

        if execution_time > 100:
            analysis = QueryOptimizer.analyze_slow_query(query, execution_time)
            self.slow_queries.append(analysis)

        if not success:
            self.error_count += 1

    def get_metrics(self) -> dict:
        avg_time = (
            self.total_execution_time / self.queries_executed
            if self.queries_executed > 0
            else 0
        )

        return {
            "total_queries": self.queries_executed,
            "average_execution_time_ms": round(avg_time, 2),
            "total_execution_time_ms": round(self.total_execution_time, 2),
            "slow_query_count": len(self.slow_queries),
            "error_count": self.error_count,
            "slow_queries": self.slow_queries[:10],
        }

    def reset(self):
        self.queries_executed = 0
        self.total_execution_time = 0
        self.slow_queries = []
        self.error_count = 0


global_connection_pool = ConnectionPool(min_connections=5, max_connections=20)
global_database_metrics = DatabaseMetrics()


@contextmanager
def get_db_connection():
    connection = global_connection_pool.acquire_connection()
    if not connection:
        raise RuntimeError("Unable to acquire database connection")

    try:
        yield connection
        connection.record_query(success=True)
    except Exception as e:
        connection.record_query(success=False)
        raise e
    finally:
        global_connection_pool.release_connection(connection)

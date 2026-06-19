"""
test_database.py - Tests for database connection pooling and optimization
"""

import pytest
from backend.core.database import (
    ConnectionPool,
    DatabaseConnection,
    QueryOptimizer,
    DatabaseMetrics,
)


@pytest.mark.unit
class TestDatabaseConnection:
    def test_connection_creation(self):
        conn = DatabaseConnection("test_conn")

        assert conn.id == "test_conn"
        assert conn.is_healthy()

    def test_record_query_success(self):
        conn = DatabaseConnection("test_conn")
        conn.record_query(success=True)

        assert conn.query_count == 1
        assert conn.error_count == 0

    def test_record_query_error(self):
        conn = DatabaseConnection("test_conn")
        conn.record_query(success=False)

        assert conn.query_count == 0
        assert conn.error_count == 1

    def test_health_check_fails_on_errors(self):
        conn = DatabaseConnection("test_conn")
        for i in range(5):
            conn.record_query(success=False)

        assert not conn.is_healthy()


@pytest.mark.unit
class TestConnectionPool:
    def test_pool_initialization(self):
        pool = ConnectionPool(min_connections=3, max_connections=10)

        assert len(pool.pool) == 3
        assert pool.max_connections == 10

    def test_acquire_connection(self):
        pool = ConnectionPool(min_connections=2, max_connections=5)
        conn = pool.acquire_connection()

        assert conn is not None
        assert conn.id in pool.in_use

    def test_release_connection(self):
        pool = ConnectionPool(min_connections=2, max_connections=5)
        conn = pool.acquire_connection()
        pool.release_connection(conn)

        assert conn.id not in pool.in_use

    def test_pool_grows_to_max(self):
        pool = ConnectionPool(min_connections=2, max_connections=5)
        connections = [pool.acquire_connection() for _ in range(5)]

        assert len(pool.pool) == 5

    def test_connection_reuse(self):
        pool = ConnectionPool(min_connections=2, max_connections=5)
        conn1 = pool.acquire_connection()
        pool.release_connection(conn1)

        conn2 = pool.acquire_connection()
        assert conn2.id == conn1.id

    def test_get_stats(self):
        pool = ConnectionPool(min_connections=2, max_connections=5)
        conn = pool.acquire_connection()

        stats = pool.get_stats()
        assert stats["active_connections"] == 1
        assert stats["pool_size"] == 2


@pytest.mark.unit
class TestQueryOptimizer:
    def test_index_recommendations_for_joins(self):
        query = "SELECT * FROM users WHERE id = 1 JOIN posts ON users.id = posts.user_id"
        recommendations = QueryOptimizer.index_recommendations(query)

        assert len(recommendations) > 0
        assert any("composite index" in r.lower() for r in recommendations)

    def test_slow_query_detection(self):
        query = "SELECT * FROM users"
        analysis = QueryOptimizer.analyze_slow_query(query, 150.0)

        assert analysis["is_slow"]

    def test_fast_query_detection(self):
        query = "SELECT * FROM users WHERE id = 1"
        analysis = QueryOptimizer.analyze_slow_query(query, 10.0)

        assert not analysis["is_slow"]


@pytest.mark.unit
class TestDatabaseMetrics:
    def test_record_query_execution(self):
        metrics = DatabaseMetrics()
        metrics.record_query_execution("SELECT * FROM users", 50.0)

        assert metrics.queries_executed == 1
        assert metrics.error_count == 0

    def test_slow_query_tracking(self):
        metrics = DatabaseMetrics()
        metrics.record_query_execution("SELECT * FROM users", 150.0)

        assert len(metrics.slow_queries) == 1

    def test_get_metrics(self):
        metrics = DatabaseMetrics()
        metrics.record_query_execution("SELECT * FROM users", 50.0)
        metrics.record_query_execution("SELECT * FROM posts", 100.0)

        result = metrics.get_metrics()
        assert result["total_queries"] == 2
        assert result["average_execution_time_ms"] == 75.0

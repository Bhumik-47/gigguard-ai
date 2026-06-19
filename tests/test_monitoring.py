"""
test_monitoring.py - Tests for monitoring and metrics functionality
"""

import pytest
from backend.core.monitoring import (
    RequestMetrics,
    SystemHealthMonitor,
    PerformanceAnalyzer,
)


@pytest.mark.unit
class TestRequestMetrics:
    def test_record_request_success(self):
        metrics = RequestMetrics()
        metrics.record_request("/api/test", "GET", 200, 50.0)

        assert metrics.request_count == 1
        assert metrics.error_count == 0
        assert "/api/test" in metrics.endpoints

    def test_record_request_error(self):
        metrics = RequestMetrics()
        metrics.record_request("/api/test", "GET", 500, 100.0)

        assert metrics.request_count == 1
        assert metrics.error_count == 1

    def test_get_metrics(self):
        metrics = RequestMetrics()
        metrics.record_request("/api/test", "GET", 200, 50.0)
        metrics.record_request("/api/test", "GET", 200, 100.0)

        result = metrics.get_metrics()

        assert result["total_requests"] == 2
        assert result["error_count"] == 0
        assert result["avg_response_time_ms"] == 75.0

    def test_error_rate_calculation(self):
        metrics = RequestMetrics()
        for i in range(100):
            status = 500 if i % 10 == 0 else 200
            metrics.record_request("/api/test", "GET", status, 50.0)

        result = metrics.get_metrics()
        assert result["error_rate_percent"] == 10.0

    def test_endpoint_metrics(self):
        metrics = RequestMetrics()
        metrics.record_request("/api/users", "GET", 200, 50.0)
        metrics.record_request("/api/users", "POST", 201, 100.0)

        result = metrics.get_endpoint_metrics()
        assert "/api/users" in result
        assert result["/api/users"]["count"] == 2


@pytest.mark.unit
class TestPerformanceAnalyzer:
    def test_record_slow_request(self):
        analyzer = PerformanceAnalyzer()
        analyzer.record_slow_request("/api/test", "GET", 2000.0)

        summary = analyzer.get_performance_summary()
        assert len(summary["slow_requests"]) == 1

    def test_record_error_pattern(self):
        analyzer = PerformanceAnalyzer()
        analyzer.record_error("/api/test", 500, "Database error")
        analyzer.record_error("/api/test", 500, "Database error")

        summary = analyzer.get_performance_summary()
        assert "/api/test:500" in summary["error_patterns"]
        assert summary["error_patterns"]["/api/test:500"]["count"] == 2

    def test_most_common_errors(self):
        analyzer = PerformanceAnalyzer()
        for i in range(5):
            analyzer.record_error("/api/a", 500, "Error A")
        for i in range(3):
            analyzer.record_error("/api/b", 404, "Error B")

        summary = analyzer.get_performance_summary()
        errors = summary["most_common_errors"]
        assert errors[0][0] == "/api/a:500"
        assert errors[0][1]["count"] == 5

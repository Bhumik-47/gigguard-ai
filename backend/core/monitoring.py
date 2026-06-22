"""
monitoring.py - System monitoring and performance tracking

Implements:
- Request/response timing
- Error tracking
- System health monitoring
- Performance metrics collection
"""

import time
from typing import Dict, List
from datetime import datetime, timedelta


class RequestMetrics:
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0
        self.response_times = []
        self.endpoints = {}
        self.start_time = time.time()

    def record_request(
        self, endpoint: str, method: str, status_code: int, response_time: float
    ):
        self.request_count += 1
        self.total_response_time += response_time
        self.response_times.append(response_time)

        if status_code >= 400:
            self.error_count += 1

        if endpoint not in self.endpoints:
            self.endpoints[endpoint] = {
                "method": method,
                "count": 0,
                "errors": 0,
                "total_time": 0,
                "avg_time": 0,
            }

        ep = self.endpoints[endpoint]
        ep["count"] += 1
        ep["total_time"] += response_time
        ep["avg_time"] = ep["total_time"] / ep["count"]

        if status_code >= 400:
            ep["errors"] += 1

    def get_metrics(self) -> dict:
        uptime = time.time() - self.start_time

        avg_response_time = (
            self.total_response_time / self.request_count
            if self.request_count > 0
            else 0
        )

        error_rate = (
            (self.error_count / self.request_count * 100)
            if self.request_count > 0
            else 0
        )

        p95_response_time = sorted(self.response_times)[
            int(len(self.response_times) * 0.95)
        ] if self.response_times else 0
        p99_response_time = sorted(self.response_times)[
            int(len(self.response_times) * 0.99)
        ] if self.response_times else 0

        return {
            "uptime_seconds": int(uptime),
            "total_requests": self.request_count,
            "error_count": self.error_count,
            "error_rate_percent": round(error_rate, 2),
            "avg_response_time_ms": round(avg_response_time, 2),
            "p95_response_time_ms": round(p95_response_time, 2),
            "p99_response_time_ms": round(p99_response_time, 2),
            "requests_per_second": round(
                self.request_count / uptime if uptime > 0 else 0, 2
            ),
        }

    def get_endpoint_metrics(self) -> dict:
        return self.endpoints

    def get_slowest_endpoints(self, limit: int = 10) -> list:
        sorted_endpoints = sorted(
            self.endpoints.items(),
            key=lambda x: x[1]["avg_time"],
            reverse=True,
        )

        return [
            {
                "endpoint": ep_name,
                "method": ep["method"],
                "avg_time_ms": round(ep["avg_time"], 2),
                "count": ep["count"],
                "errors": ep["errors"],
            }
            for ep_name, ep in sorted_endpoints[:limit]
        ]


class SystemHealthMonitor:
    def __init__(self):
        self.checks = {}
        self.last_check_time = {}

    def register_health_check(self, name: str, check_func, interval: int = 60):
        self.checks[name] = {
            "func": check_func,
            "interval": interval,
            "last_result": None,
            "last_check": 0,
        }

    async def run_health_check(self, name: str) -> dict:
        if name not in self.checks:
            return {"status": "unknown", "message": "Check not found"}

        check = self.checks[name]
        current_time = time.time()

        if (current_time - check["last_check"]) < check["interval"]:
            return check["last_result"]

        try:
            result = await check["func"]() if hasattr(check["func"], "__await__") else check["func"]()
            check["last_result"] = {
                "status": "healthy" if result else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "details": result,
            }
        except Exception as e:
            check["last_result"] = {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

        check["last_check"] = current_time
        return check["last_result"]

    def get_all_health_checks(self) -> dict:
        return {name: check["last_result"] for name, check in self.checks.items()}

    def get_overall_health(self) -> dict:
        all_checks = self.get_all_health_checks()

        statuses = [
            check.get("status", "unknown") for check in all_checks.values()
        ]

        overall_status = "healthy"
        if any(s == "error" for s in statuses):
            overall_status = "critical"
        elif any(s == "unhealthy" for s in statuses):
            overall_status = "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": all_checks,
        }


class PerformanceAnalyzer:
    def __init__(self):
        self.slow_requests = []
        self.error_patterns = {}

    def record_slow_request(self, endpoint: str, method: str, response_time: float):
        if response_time > 1000:
            self.slow_requests.append({
                "endpoint": endpoint,
                "method": method,
                "response_time_ms": response_time,
                "timestamp": datetime.now().isoformat(),
            })

            if len(self.slow_requests) > 1000:
                self.slow_requests = self.slow_requests[-500:]

    def record_error(self, endpoint: str, status_code: int, error_message: str):
        key = f"{endpoint}:{status_code}"

        if key not in self.error_patterns:
            self.error_patterns[key] = {
                "count": 0,
                "last_error": None,
                "first_seen": datetime.now().isoformat(),
            }

        self.error_patterns[key]["count"] += 1
        self.error_patterns[key]["last_error"] = error_message

    def get_performance_summary(self) -> dict:
        return {
            "slow_requests": len(self.slow_requests),
            "recent_slow_requests": self.slow_requests[-5:],
            "error_patterns": self.error_patterns,
            "most_common_errors": sorted(
                self.error_patterns.items(),
                key=lambda x: x[1]["count"],
                reverse=True,
            )[:5],
        }


global_request_metrics = RequestMetrics()
global_health_monitor = SystemHealthMonitor()
global_performance_analyzer = PerformanceAnalyzer()

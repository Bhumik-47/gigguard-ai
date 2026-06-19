"""
monitoring.py - Monitoring and system health endpoints

Provides endpoints for:
- System metrics
- Health checks
- Performance analytics
- Cache and database statistics
"""

from fastapi import APIRouter
from backend.core.monitoring import (
    global_request_metrics,
    global_health_monitor,
    global_performance_analyzer,
)
from backend.core.database import global_connection_pool, global_database_metrics
from backend.core.caching import global_cache, global_query_cache
from backend.core.load_balancer import global_load_balancer

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/metrics")
async def get_system_metrics():
    return {
        "request_metrics": global_request_metrics.get_metrics(),
        "endpoint_metrics": global_request_metrics.get_endpoint_metrics(),
        "slowest_endpoints": global_request_metrics.get_slowest_endpoints(10),
    }


@router.get("/health")
async def get_health_status():
    return {
        "status": "healthy",
        "database": global_connection_pool.health_check(),
        "cache": global_cache.get_stats(),
        "load_balancer": global_load_balancer.get_overall_stats(),
    }


@router.get("/database/stats")
async def get_database_stats():
    return {
        "pool_stats": global_connection_pool.get_stats(),
        "pool_health": global_connection_pool.health_check(),
        "query_metrics": global_database_metrics.get_metrics(),
        "connections": global_connection_pool.get_connection_details(),
    }


@router.get("/cache/stats")
async def get_cache_stats():
    return {
        "cache_stats": global_cache.get_stats(),
        "cache_entries": global_cache.get_entries(20),
        "query_cache_stats": global_query_cache.get_stats(),
    }


@router.get("/load-balancer/stats")
async def get_load_balancer_stats():
    return {
        "overall_stats": global_load_balancer.get_overall_stats(),
        "server_stats": global_load_balancer.get_server_stats(),
    }


@router.post("/load-balancer/health-check")
async def trigger_health_check():
    return global_load_balancer.health_check_all()


@router.get("/performance")
async def get_performance_analysis():
    return global_performance_analyzer.get_performance_summary()


@router.get("/cache/cleanup")
async def cleanup_expired_cache():
    removed = global_cache.cleanup_expired()
    return {
        "expired_entries_removed": removed,
        "cache_stats": global_cache.get_stats(),
    }


@router.post("/database/cleanup-idle")
async def cleanup_idle_connections():
    removed = global_connection_pool.removeIdleConnections()
    return {
        "idle_connections_removed": removed,
        "pool_stats": global_connection_pool.get_stats(),
    }


@router.get("/system/overview")
async def get_system_overview():
    return {
        "metrics": global_request_metrics.get_metrics(),
        "health": {
            "database": global_connection_pool.health_check(),
            "cache": {"status": "healthy" if global_cache.get_stats()["hit_rate"] > "0%" else "degraded"},
            "load_balancer": {"healthy_servers": len([s for s in global_load_balancer.servers if s.is_healthy])},
        },
        "performance": global_performance_analyzer.get_performance_summary(),
        "slowest_endpoints": global_request_metrics.get_slowest_endpoints(5),
    }

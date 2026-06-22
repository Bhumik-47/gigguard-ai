from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
import time
from backend.core.monitoring import global_request_metrics, global_performance_analyzer


async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000

    global_request_metrics.record_request(
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code,
        response_time=process_time,
    )

    if response.status_code >= 400:
        global_performance_analyzer.record_error(
            endpoint=request.url.path,
            status_code=response.status_code,
            error_message=f"HTTP {response.status_code}",
        )

    if process_time > 1000:
        global_performance_analyzer.record_slow_request(
            endpoint=request.url.path,
            method=request.method,
            response_time=process_time,
        )

    response.headers["X-Process-Time"] = str(process_time)

    return response


def configure_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(metrics_middleware)

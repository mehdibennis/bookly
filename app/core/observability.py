"""Observability helpers (prometheus/tracing) used by the FastAPI app.

This module provides lightweight instrumentation when Prometheus is enabled.
When disabled or when the prometheus_client package is not installed, the
functions are safe no-ops so tests and environments lacking monitoring can
import the application without failing.
"""

from typing import Callable

from fastapi import FastAPI, Response


def setup_prometheus(
    app: FastAPI, enabled: bool = False, endpoint: str | None = None
) -> None:
    """Configure a /metrics endpoint and basic request metrics.

    When enabled and prometheus_client is available, register a Counter
    for total requests and a Histogram for request durations. The metrics
    are exposed at ``endpoint`` (defaults to "/metrics").
    """
    if not enabled:
        return None

    try:
        import time

        from prometheus_client import (
            CONTENT_TYPE_LATEST,
            Counter,
            Histogram,
            exposition,
        )
    except Exception:
        # Optional dependency: do not fail when prometheus_client isn't present
        return None

    REQUEST_COUNTER = Counter(
        "bookly_requests_total",
        "Total number of HTTP requests processed by Bookly",
        ["method", "endpoint", "http_status"],
    )

    REQUEST_DURATION = Histogram(
        "bookly_request_duration_seconds",
        "Histogram of request processing durations in seconds",
        ["method", "endpoint"],
    )

    metrics_endpoint = endpoint or "/metrics"

    @app.middleware("http")
    async def prometheus_middleware(request, call_next: Callable):
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        try:
            REQUEST_COUNTER.labels(
                request.method, request.url.path, str(response.status_code)
            ).inc()
            REQUEST_DURATION.labels(request.method, request.url.path).observe(duration)
        except Exception:
            # best-effort metrics; don't let metrics break the app
            pass
        return response

    @app.get(metrics_endpoint, include_in_schema=False)
    async def metrics():
        """Return Prometheus metrics exposition.

        This handler uses the prometheus_client exposition module to return
        the latest metrics with the expected content type.
        """
        registry = exposition.REGISTRY
        output = exposition.generate_latest(registry)
        return Response(content=output, media_type=CONTENT_TYPE_LATEST)


def setup_tracing(
    app: FastAPI,
    enabled: bool = False,
    service_name: str | None = None,
    otlp_endpoint: str | None = None,
) -> None:
    """Configure tracing (OpenTelemetry).

    No-op in testing environments.
    """
    return None

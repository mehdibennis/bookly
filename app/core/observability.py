import logging

from app.core.logging_config import request_id_var


def setup_prometheus(app, enabled: bool, endpoint: str = "/metrics") -> None:
    """Optionally expose Prometheus metrics using prometheus-fastapi-instrumentator.

    Safe to call even if the package is missing when disabled.
    """
    if not enabled:
        return
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except Exception as e:  # pragma: no cover - optional dep
        logging.getLogger(__name__).warning(f"Prometheus disabled (missing package): {e}")
        return

    try:
        Instrumentator().instrument(app).expose(app, endpoint=endpoint)
        logging.getLogger(__name__).info("Prometheus metrics exposed at %s", endpoint)
    except Exception as e:  # pragma: no cover - best effort
        logging.getLogger(__name__).warning(f"Prometheus not initialized: {e}")


def setup_tracing(
    app,
    enabled: bool,
    service_name: str = "bookly",
    otlp_endpoint: str | None = None,
    console_fallback: bool = False,
) -> None:
    """Optionally initialize OpenTelemetry tracing for FastAPI.

    - If otlp_endpoint is provided and exporter is available, export via OTLP.
    - Else, if console_fallback=True, enable ConsoleSpanExporter (multiline output).
        By default, we avoid console exporter to prevent noisy multiline logs.
    """
    if not enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except Exception as e:  # pragma: no cover - optional dep
        logging.getLogger(__name__).warning(f"Tracing disabled (missing package): {e}")
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    exporter = None
    if otlp_endpoint:
        try:  # pragma: no cover - optional dep
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        except Exception as e:
            logging.getLogger(__name__).warning(f"OTLP exporter not available, falling back to ConsoleSpanExporter: {e}")

    if exporter is None and console_fallback:
        exporter = ConsoleSpanExporter()

    if exporter is not None:
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument FastAPI app
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

    # Add middleware to attach request_id to current span
    @app.middleware("http")
    async def _otlp_request_id(request, call_next):  # type: ignore[no-redef]
        from opentelemetry.trace import get_current_span

        response = await call_next(request)
        span = get_current_span()
        try:
            span.set_attribute("request.id", request_id_var.get())
            span.set_attribute("http.request_id", request_id_var.get())
        except Exception:
            pass
        return response

    logging.getLogger(__name__).info("OpenTelemetry tracing initialized (service=%s)", service_name)

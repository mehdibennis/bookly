import json
import logging
import uuid
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core import config
from app.core.logging_config import request_id_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Injects an X-Request-ID header and stores it in a ContextVar for logging.

    - Uses incoming X-Request-ID if present, otherwise generates a new one.
    - Exposes the value via app.core.logging_config.request_id_var ContextVar.
    - Adds the header to the outgoing response.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming or uuid.uuid4().hex[:16]
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Structured access logging with optional request/response bodies.

    Notes:
    - Bodies are captured only if enabled via settings and up to LOG_BODY_MAX_BYTES.
    - Non-JSON bodies are logged as text (truncated) when enabled.
    - For performance/safety, request body capture is disabled by default.
    """

    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("access")
        # Préparer la liste des chemins à exclure (préfixes)
        try:
            self._exclude_paths = tuple(config.settings.LOG_BODY_EXCLUDE_PATHS)
        except Exception:
            self._exclude_paths = ("/metrics",)

    def _is_excluded(self, path: str) -> bool:
        return any(path.startswith(p) for p in self._exclude_paths)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = perf_counter()

        # Request metadata
        client_ip = request.client.host if request.client else "-"
        user_agent = request.headers.get("user-agent", "-")
        method = request.method
        path = request.url.path

        # Évaluer exclusion (ex: /metrics)
        excluded = self._is_excluded(path) or (
            path == getattr(config.settings, "METRICS_ENDPOINT", "/metrics")
        )

        # Optionally capture request body (best effort)
        req_body_snippet: str | None = None
        if config.settings.LOG_REQUEST_BODY and not excluded:
            try:
                raw = await request.body()
                if raw:
                    raw = raw[: config.settings.LOG_BODY_MAX_BYTES]
                    content_type = request.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            req_body_snippet = json.dumps(
                                json.loads(raw.decode("utf-8", errors="ignore"))
                            )
                        except Exception:
                            req_body_snippet = raw.decode("utf-8", errors="ignore")
                    else:
                        req_body_snippet = raw.decode("utf-8", errors="ignore")

                # Rebuild the request stream for downstream handlers
                async def receive():
                    return {"type": "http.request", "body": raw, "more_body": False}

                request = Request(request.scope, receive)
            except Exception:
                req_body_snippet = None

        # Call downstream and capture response body if enabled
        response = await call_next(request)

        resp_body_snippet: str | None = None
        if config.settings.LOG_RESPONSE_BODY and not excluded:
            try:
                body_bytes = b""
                async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                    body_bytes += chunk
                # Recreate response to avoid consuming the iterator
                new_response = Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                    background=response.background,
                )
                response = new_response

                if body_bytes:
                    body_bytes = body_bytes[: config.settings.LOG_BODY_MAX_BYTES]
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            resp_body_snippet = json.dumps(
                                json.loads(body_bytes.decode("utf-8", errors="ignore"))
                            )
                        except Exception:
                            resp_body_snippet = body_bytes.decode(
                                "utf-8", errors="ignore"
                            )
                    else:
                        resp_body_snippet = body_bytes.decode("utf-8", errors="ignore")
            except Exception:
                resp_body_snippet = None

        # Sécurité: si exclu, on force la suppression des corps
        if excluded:
            req_body_snippet = None
            resp_body_snippet = None

        duration_ms = round((perf_counter() - start) * 1000, 2)
        payload = {
            "request_id": request_id_var.get(),
            "method": method,
            "path": path,
            "status": response.status_code,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "duration_ms": duration_ms,
        }
        if req_body_snippet is not None:
            payload["request_body"] = req_body_snippet
        if resp_body_snippet is not None:
            payload["response_body"] = resp_body_snippet

        # Log at INFO; elevate to WARNING for 4xx and ERROR for 5xx
        if response.status_code >= 500:
            self.logger.error(
                "HTTP request",
                extra={"request_id": request_id_var.get()},
                stack_info=False,
            )
            self.logger.error(json.dumps(payload, ensure_ascii=False))
        elif response.status_code >= 400:
            self.logger.warning(
                "HTTP request",
                extra={"request_id": request_id_var.get()},
                stack_info=False,
            )
            self.logger.warning(json.dumps(payload, ensure_ascii=False))
        else:
            self.logger.info(json.dumps(payload, ensure_ascii=False))

        return response

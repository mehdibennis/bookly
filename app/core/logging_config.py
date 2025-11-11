import json
import logging
import logging.config
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        try:
            record.request_id = request_id_var.get()
        except Exception:
            record.request_id = "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        # Optional extras
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    to_file: bool = False,
    filename: str | None = None,
    json_logs: bool = False,
) -> None:
    """
    Configure application-wide logging using dictConfig.

    Parameters:
    - level: logging level name (e.g., "DEBUG", "INFO")
    - to_file: also log to a rotating file if True
    - filename: file name to use when to_file is True (default: app.log)
    """

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handlers: dict[str, dict] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": numeric_level,
            "formatter": "json" if json_logs else "standard",
            "stream": "ext://sys.stdout",
            "filters": ["request_id"],
        }
    }

    if to_file:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": numeric_level,
            "formatter": "json" if json_logs else "standard",
            "filename": filename or "app.log",
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 3,
            "encoding": "utf-8",
            "filters": ["request_id"],
        }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "json": {"()": JsonFormatter},
            },
            "filters": {"request_id": {"()": RequestIdFilter}},
            "handlers": handlers,
            "root": {
                "level": numeric_level,
                "handlers": list(handlers.keys()),
            },
            "loggers": {
                # Ensure uvicorn logs (access & error) use our handlers/formatters
                "uvicorn": {
                    "level": numeric_level,
                    "handlers": list(handlers.keys()),
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": numeric_level,
                    "handlers": list(handlers.keys()),
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": numeric_level,
                    "handlers": list(handlers.keys()),
                    "propagate": False,
                },
                # Gunicorn (if ever used)
                "gunicorn.error": {
                    "level": numeric_level,
                    "handlers": list(handlers.keys()),
                    "propagate": False,
                },
                "gunicorn.access": {
                    "level": numeric_level,
                    "handlers": list(handlers.keys()),
                    "propagate": False,
                },
            },
        }
    )

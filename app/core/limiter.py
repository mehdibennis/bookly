from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core import config


def rate_limit_key(request: Request) -> str:
    if config.settings.TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    # Fallback to SlowAPI helper (client host)
    return get_remote_address(request)


# Limiter instance shared across the app; import from this module to avoid
# circular imports between `app.main` and route modules.
limiter = Limiter(key_func=rate_limit_key)

import logging


def setup_sentry(
    enabled: bool,
    dsn: str | None,
    environment: str = "dev",
    traces_sample_rate: float = 0.0,
    profiles_sample_rate: float = 0.0,
) -> None:
    """Initialize Sentry SDK for error and performance monitoring.

    Safe no-op when disabled or when SDK is missing.
    """
    if not enabled or not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
    except Exception as e:  # pragma: no cover - optional dependency
        logging.getLogger(__name__).warning(f"Sentry disabled (missing package): {e}")
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[FastApiIntegration()],
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            send_default_pii=False,
        )
        logging.getLogger(__name__).info("Sentry initialized (env=%s)", environment)
    except Exception as e:  # pragma: no cover - best effort
        logging.getLogger(__name__).warning(f"Sentry not initialized: {e}")

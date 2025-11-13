import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
    # SECRET_KEY: str

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: bool = False
    LOG_FILE: str = "app.log"
    LOG_JSON: bool = True
    # Access logging
    LOG_ACCESS: bool = True
    LOG_REQUEST_BODY: bool = False
    LOG_RESPONSE_BODY: bool = False
    LOG_BODY_MAX_BYTES: int = 2048
    # Exclure la capture des corps (req/resp) pour certains chemins (préfixes). Exemple: ["/metrics", "/health"]
    LOG_BODY_EXCLUDE_PATHS: list[str] = ["/metrics"]

    # Security and platform
    TRUST_PROXY: bool = False
    # ENABLE_ADMIN: bool = False

    # Observability
    ENABLE_METRICS: bool = False
    METRICS_ENDPOINT: str = "/metrics"
    ENABLE_TRACING: bool = True
    OTEL_SERVICE_NAME: str = "bookly"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None

    # Sentry
    ENABLE_SENTRY: bool = False
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "dev"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.0

    # Keycloak settings
    KEYCLOAK_SERVER_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "bookly"
    KEYCLOAK_CLIENT_ID: str = "bookly-client"
    KEYCLOAK_CLIENT_SECRET: str = ""

    @property
    def KEYCLOAK_URL(self) -> str:
        """Complete Keycloak realm URL (base for realm-specific endpoints)."""
        return f"{self.KEYCLOAK_SERVER_URL.rstrip('/')}/realms/{self.KEYCLOAK_REALM}"

    @property
    def KEYCLOAK_TOKEN_URL(self) -> str:
        return f"{self.KEYCLOAK_URL}/protocol/openid-connect/token"

    @property
    def KEYCLOAK_USERINFO_URL(self) -> str:
        return f"{self.KEYCLOAK_URL}/protocol/openid-connect/userinfo"

    @property
    def KEYCLOAK_INTROSPECT_URL(self) -> str:
        return f"{self.KEYCLOAK_URL}/protocol/openid-connect/token/introspect"

    @property
    def KEYCLOAK_JWKS_URL(self) -> str:
        return f"{self.KEYCLOAK_URL}/protocol/openid-connect/certs"

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def SYNC_DATABASE_URL(self):
        """Synchronous URL for tools that require sync SQLAlchemy engine (e.g., SQLAdmin)."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")

    @property
    def REDIS_URL(self):
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def TEST_SCHEMA(self) -> str:  # pragma: no cover - xdist only
        """Return a test schema name based on xdist worker id if present.

        When running tests in parallel, pytest-xdist sets the environment
        variable `PYTEST_XDIST_WORKER` (e.g. 'gw0', 'gw1'). We append this
        to a base schema name to isolate test data between workers.
        """
        worker = os.getenv("PYTEST_XDIST_WORKER")
        if worker:
            return f"test_{worker}"
        return "test"

    # class Config:
    #     env_file = ".env"


settings = Settings()  # type: ignore[call-arg]

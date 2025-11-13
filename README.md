# Bookly — Books API

> Modern REST API built with FastAPI, PostgreSQL, Redis and Keycloak.

[![codecov](https://codecov.io/github/mehdibennis/bookly/branch/clean_arch_implem/graph/badge.svg?token=CGu5EDQbRu)](https://codecov.io/github/mehdibennis/bookly)
[![Python](https://img.shields.io/badge/python-3.11-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern-009688)]()

Summary
-------
Bookly is a small, modern FastAPI application that manages books. It
follows a clean-architecture style (domain/services/repositories), uses
asynchronous SQLAlchemy with asyncpg for the database, Redis for caching,
and Keycloak for authentication in integration / production-like setups.

Quick facts
-----------
- Language: Python 3.11
- Framework: FastAPI
- DB: PostgreSQL (async SQLAlchemy / asyncpg)
- Cache: Redis (redis.asyncio)
- Auth: Keycloak (OIDC)

Quick start
-----------
1. Clone the repo:

```bash
git clone <repo-url>
cd bookly
```

2. Bring up services (API, Postgres, Redis, Keycloak):

```bash
docker compose up -d
# API is then available at http://localhost:8000
```

Local development notes
-----------------------
- Use Python 3.11 for local development.
- The project expects a PostgreSQL and Redis instance for integration tests.
- For a smooth local test workflow there's a Make target `make test-local` that
  will start db/redis (host-mapped
  ports) and run pytest on the host. This avoids common asyncpg/docker-proxy
  issues by preferring a direct container IP when necessary.

Repository layout
-----------------
```
bookly/
├── alembic/                # migrations
├── app/                    # application code
│   ├── api/                # API layer (routes, controllers)
│   │   └── v1/routes/      # versioned HTTP routes
│   ├── core/               # config, auth, cache, error handlers
│   ├── db/                 # models, session, migrations
│   ├── domain/             # domain entities & interfaces (DDD)
│   ├── repositories/       # data access layer
│   ├── schemas/            # Pydantic DTOs
│   └── services/           # business logic
├── tests/                  # unit & integration tests
│   └── helpers/            # shared test helpers (DummyUser, FakeRedis...)
├── scripts/                # local helper scripts (test-local.sh)
├── docker-compose.yml
├── Makefile
└── README.md
```

Testing & quality
-----------------
- Tests: integration + unit tests (async)
- Test runner: pytest, pytest-asyncio, pytest-xdist
- Coverage: CI target is >= 98% (local runs in this branch reported ~98.28% coverage and 328 passing tests)

Metrics
-------
- Coverage: >= 98% (CI gate)
- Tests: ~320+ (varies by branch)
- Typical running time: ~60s (when run concurrently with pytest-xdist)

Run tests locally
------------------

- Fast, host-run workflow (recommended for local dev):

```bash
# DB+Redis containers must be up and running
make test-local
```

- To run tests inside the `web` container (CI-like):

```bash
make test
```

If you want to run a single test file quickly without the global coverage gate:

```bash
POSTGRES_USER=bookly_user POSTGRES_PASSWORD=bookly_pass POSTGRES_DB=bookly_db \
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=15432 \
pytest -o addopts= tests/unit/test_unit_redis_cache.py -q
```

API surface
-----------
- GET  /                               — root (service info / health)
- GET  /api/v1/books/?page=&size=      — paginated list of books (public)
- GET  /api/v1/books/{id}              — book details (auth required)
- POST /api/v1/books/                  — create a book (auth required)
- PUT  /api/v1/books/{id}              — update a book (auth required)
- DELETE /api/v1/books/{id}           — delete a book (auth required)

- GET  /api/v1/authors/?page=&size=    — paginated list of authors (public)
- GET  /api/v1/authors/{id}            — author details (auth required)
- POST /api/v1/authors/                — create an author (auth required)
- PUT  /api/v1/authors/{id}            — update an author (auth required)
- DELETE /api/v1/authors/{id}         — delete an author (auth required)

- GET  /ping                           — health check
- GET  /docs, /redoc                   — API documentation

Technical features
------------------
- Authentication: Keycloak (OIDC)
- Cache: Redis for paginated lists (tests use a `tests.helpers.FakeRedis`)
- Validation: Pydantic v2
- ORM: SQLAlchemy async (asyncpg)
- Rate limiting: slowapi (IP-based)
- Structured request logging with request UUID

Development & environment
-------------------------
Create a `.env` file at the repository root (example values):

```env
# Database (when running in docker compose the host is usually `db`)
POSTGRES_USER=bookly_user
POSTGRES_PASSWORD=bookly_pass
POSTGRES_DB=bookly_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Application
SECRET_KEY=replace-me
DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000

# Keycloak
KEYCLOAK_SERVER_URL=http://keycloak:8080
KEYCLOAK_REALM=bookly
KEYCLOAK_CLIENT_ID=bookly-client
KEYCLOAK_CLIENT_SECRET=

# Redis
REDIS_URL=redis://redis:6379/0
```

Useful commands
---------------

```bash
# Build the web image
docker compose build web

# Tail logs
docker compose logs -f web

# Open a shell in the running web container
docker compose exec web bash

# Run alembic migrations (inside container)
docker compose run --rm web alembic upgrade head

# Create an alembic revision
docker compose run --rm web alembic revision --autogenerate -m "msg"
```

Testing helpers
---------------
Shared test helpers live under `tests/helpers` (for example `DummyUser` and
`FakeRedis`) and are used by multiple test modules to avoid duplicated test
fixtures.

Pre-commit hooks
----------------
This repository includes a `.pre-commit-config.yaml`. To enable local pre-commit
hooks run once on your machine:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # optional: fix the codebase once
```

CI / Coverage
-------------
CI is expected to run the full test suite and upload coverage to Codecov. The
project enforces a high coverage gate in CI (>= 98%). If you want a fast local
loop, use `make test-local` which starts the services and runs pytest on the
host.

Roadmap
-------
- Harden SQLAdmin + RBAC for admin UI

Contributing
------------
1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Run tests and linters locally
4. Open a pull request

Standards
- Coverage >= 98% in CI
- Black / isort formatting
- Type hints and tests for new behavior


Authors
-------
Mehdi Bennis — medi.b@hotmail.com

---

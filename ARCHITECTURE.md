# Architecture decisions (summary)

This project follows Clean Architecture / Onion (Ports & Adapters). Below are a couple of short, actionable rules to help contributors keep layers clean.

## Exceptions: domain vs core

- Domain exceptions live in `app/domain/exceptions.py`.
  - Purpose: represent pure business/domain errors (e.g. `NotFoundException`, `ConflictException`, `DomainException`).
  - Must not depend on HTTP, FastAPI, or status codes. They are raised by services and repositories.

- Application / HTTP exceptions live in `app/core/exceptions.py`.
  - Purpose: exceptions that carry HTTP semantics (status_code, user-facing messages) and are used by the API layer and tests that assert on status codes.
  - The API layer (in `app/core/error_handlers.py` and `app/main.py`) maps domain exceptions -> appropriate HTTP responses using these application exceptions or direct JSONResponses.

Rationale:
- Keeping domain errors framework-agnostic improves portability (CLI, background jobs, different web frameworks) and testability.
- The API layer is responsible for translating domain errors into transport-level errors (HTTP status codes + messages).

## Enforcement
- There's an architecture test at `tests/unit/test_architecture.py` which asserts that files under `app/domain/` do not import `app.core`, `app.api`, `app.db`, or other infra layers.
- If you need to add a new domain exception, add it to `app/domain/exceptions.py` and then update `app/core/error_handlers.py` if mapping to HTTP responses is required.

## Quick dev notes
- Services should raise domain exceptions from `app.domain.exceptions`.
- The API layer should catch/map domain exceptions to HTTP responses (handlers registered in `app/main.py`).
- `app/core/exceptions.py` remains the choice for HTTP-oriented exceptions used by the API and tests that assert `status_code`.

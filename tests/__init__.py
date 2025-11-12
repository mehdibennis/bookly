"""Make `tests` a regular package to avoid mypy module name ambiguity.

Having this __init__.py prevents mypy from sometimes mapping files under
`tests/...` to both top-level and package module names (for example
`mocks.cache_service` vs `tests.mocks.cache_service`).
"""

__all__ = []

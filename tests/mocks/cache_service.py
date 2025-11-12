from __future__ import annotations

from typing import Any

from app.domain.entities import AuthorEntity, BookEntity
from app.domain.repositories import ICacheService
from app.domain.value_objects import PaginatedResult


class MockCacheService(ICacheService):
    """In-memory mock cache implementation used by tests.

    The methods and signatures intentionally match `ICacheService` so mypy
    and pre-commit checks accept the implementation used by tests.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def get_books_page(
        self, page: int, size: int
    ) -> PaginatedResult[BookEntity] | None:
        key = f"books:page:{page}:size:{size}"
        return self._cache.get(key)

    async def set_books_page(
        self, page: int, size: int, result: PaginatedResult[BookEntity] | dict[str, Any]
    ) -> None:
        key = f"books:page:{page}:size:{size}"
        self._cache[key] = result

    async def invalidate_books_cache(self) -> None:
        self._cache = {
            k: v for k, v in self._cache.items() if not k.startswith("books:page:")
        }

    async def get_authors_page(
        self, page: int, size: int
    ) -> PaginatedResult[AuthorEntity] | None:
        key = f"authors:page:{page}:size:{size}"
        return self._cache.get(key)

    async def set_authors_page(
        self,
        page: int,
        size: int,
        result: PaginatedResult[AuthorEntity] | dict[str, Any],
    ) -> None:
        key = f"authors:page:{page}:size:{size}"
        self._cache[key] = result

    # Backwards-compatible search variants required by tests that were added
    # while the cache contract evolved. Provide permissive signatures so
    # test code and older mocks continue to work without mypy errors.
    async def get_authors_page_search(
        self, page: int, size: int, search: str
    ) -> PaginatedResult[AuthorEntity] | None:
        # naive search over cached authors pages
        for k, v in self._cache.items():
            if k.startswith("authors:page:"):
                return v
        return None

    async def set_authors_page_search(
        self,
        page: int,
        size: int,
        search: str,
        result: PaginatedResult[AuthorEntity] | dict[str, Any],
    ) -> None:
        key = f"authors:search:{search}:page:{page}:size:{size}"
        self._cache[key] = result

    async def invalidate_authors_cache(self) -> None:
        self._cache = {
            k: v for k, v in self._cache.items() if not k.startswith("authors:page:")
        }

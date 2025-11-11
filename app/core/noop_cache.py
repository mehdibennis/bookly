from typing import Any

from app.domain.entities import AuthorEntity, BookEntity
from app.domain.repositories import ICacheService
from app.domain.value_objects import PaginatedResult


class NoopCache(ICacheService):
    """A small, shared no-op cache implementation for tests and fallbacks."""

    async def connect(self) -> None:  # pragma: no cover - trivial
        return None

    async def close(self) -> None:  # pragma: no cover - trivial
        return None

    async def get_books_page(
        self, page: int, size: int
    ) -> PaginatedResult[BookEntity] | None:  # pragma: no cover
        return None

    async def set_books_page(
        self, page: int, size: int, result: PaginatedResult[BookEntity] | dict
    ) -> None:  # pragma: no cover
        return None

    async def invalidate_books_cache(self) -> None:  # pragma: no cover
        return None

    async def get_authors_page(
        self, page: int, size: int
    ) -> PaginatedResult[AuthorEntity] | None:  # pragma: no cover
        return None

    async def set_authors_page(
        self, page: int, size: int, result: PaginatedResult[AuthorEntity] | dict
    ) -> None:  # pragma: no cover
        return None

    async def invalidate_authors_cache(self) -> None:  # pragma: no cover
        return None

    async def get_authors_page_search(
        self, page: int, size: int, search: str
    ) -> PaginatedResult[AuthorEntity] | None:  # pragma: no cover
        return None

    async def set_authors_page_search(
        self,
        page: int,
        size: int,
        search: str,
        result: PaginatedResult[AuthorEntity] | dict,
    ):  # pragma: no cover
        return None

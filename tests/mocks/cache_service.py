"""Mock cache service for testing.

This provides a simple in-memory cache implementation that can be used
in tests without requiring Redis infrastructure.
"""

from app.domain.entities import AuthorEntity, BookEntity
from app.domain.repositories import ICacheService
from app.domain.value_objects import PaginatedResult


class MockCacheService(ICacheService):
    """In-memory cache service for testing."""

    def __init__(self):
        self._cache = {}

    async def connect(self) -> None:
        """No-op for mock cache."""
        pass

    async def get_books_page(self, page: int, size: int) -> PaginatedResult[BookEntity] | None:
        """Get cached books page."""
        key = f"books:page:{page}:size:{size}"
        return self._cache.get(key)

    async def set_books_page(self, page: int, size: int, result: PaginatedResult[BookEntity]) -> None:
        """Cache books page."""
        key = f"books:page:{page}:size:{size}"
        self._cache[key] = result

    async def invalidate_books_cache(self) -> None:
        """Invalidate all books cache."""
        self._cache = {k: v for k, v in self._cache.items() if not k.startswith("books:page:")}

    async def get_authors_page(self, page: int, size: int) -> PaginatedResult[AuthorEntity] | None:
        """Get cached authors page."""
        key = f"authors:page:{page}:size:{size}"
        return self._cache.get(key)

    async def set_authors_page(self, page: int, size: int, result: PaginatedResult[AuthorEntity]) -> None:
        """Cache authors page."""
        key = f"authors:page:{page}:size:{size}"
        self._cache[key] = result

    async def invalidate_authors_cache(self) -> None:
        """Invalidate all authors cache."""
        self._cache = {k: v for k, v in self._cache.items() if not k.startswith("authors:page:")}

"""
Reusable fixtures for unit tests.
Provides common mocks for services, repositories, and cache.
"""

from unittest.mock import AsyncMock

import pytest

from app.domain.entities import AuthorEntity, BookEntity
from app.domain.value_objects import PaginatedResult, PaginationMeta
from tests.mocks.cache_service import MockCacheService


@pytest.fixture
def mock_cache():
    """Provide a mock cache service."""
    return MockCacheService()


@pytest.fixture
def mock_book_repository():
    """Provide a mock book repository with common methods."""
    repo = AsyncMock()

    # Default return values
    repo.get_by_id.return_value = None
    repo.get_by_title.return_value = None
    repo.create.return_value = BookEntity(id=1, title="Test Book", authors=[1])
    repo.update.return_value = BookEntity(id=1, title="Updated Book", authors=[1])
    repo.partial_update.return_value = BookEntity(
        id=1, title="Patched Book", authors=[1]
    )
    repo.delete.return_value = True
    repo.get_paginated.return_value = PaginatedResult(
        data=[], meta=PaginationMeta(total=0, page=1, size=10, count=0)
    )

    return repo


@pytest.fixture
def mock_author_repository():
    """Provide a mock author repository with common methods."""
    repo = AsyncMock()

    # Default return values
    repo.get_by_id.return_value = None
    repo.get_by_full_name.return_value = None
    repo.create.return_value = AuthorEntity(id=1, first_name="John", last_name="Doe")
    repo.update.return_value = AuthorEntity(id=1, first_name="Updated", last_name="Doe")
    repo.partial_update.return_value = AuthorEntity(
        id=1, first_name="Patched", last_name="Doe"
    )
    repo.delete.return_value = True
    repo.get_paginated.return_value = PaginatedResult(
        data=[], meta=PaginationMeta(total=0, page=1, size=10, count=0)
    )

    return repo


@pytest.fixture
def mock_unit_of_work():
    """Provide a mock unit of work."""
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=None)
    uow.__aexit__ = AsyncMock(return_value=None)
    return uow


@pytest.fixture
def sample_book_entity():
    """Provide a sample book entity for testing."""
    return BookEntity(
        id=1,
        title="Sample Book",
        authors=[1, 2],
        authors_details=[
            {"id": 1, "first_name": "John", "last_name": "Doe"},
            {"id": 2, "first_name": "Jane", "last_name": "Smith"},
        ],
        authors_number=2,
    )


@pytest.fixture
def sample_author_entity():
    """Provide a sample author entity for testing."""
    from datetime import date, datetime

    return AuthorEntity(
        id=1,
        first_name="John",
        last_name="Doe",
        birth_date=date(1950, 1, 1),
        death_date=None,
        nationality="USA",
        bio="Test bio",
        photo_url="http://example.com/photo.jpg",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 2, 12, 0, 0),
    )


@pytest.fixture
def paginated_books_result():
    """Provide a sample paginated books result."""
    books = [
        BookEntity(id=1, title="Book 1", authors=[1]),
        BookEntity(id=2, title="Book 2", authors=[1]),
        BookEntity(id=3, title="Book 3", authors=[1]),
    ]
    meta = PaginationMeta(total=10, page=1, size=10, count=3)
    return PaginatedResult(data=books, meta=meta)


@pytest.fixture
def paginated_authors_result():
    """Provide a sample paginated authors result."""
    authors = [
        AuthorEntity(id=1, first_name="John", last_name="Doe"),
        AuthorEntity(id=2, first_name="Jane", last_name="Smith"),
        AuthorEntity(id=3, first_name="Bob", last_name="Johnson"),
    ]
    meta = PaginationMeta(total=15, page=2, size=5, count=3)
    return PaginatedResult(data=authors, meta=meta)

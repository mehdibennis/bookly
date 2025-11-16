from unittest.mock import AsyncMock

import pytest

from app.domain.entities import AuthorEntity
from app.domain.value_objects import PaginatedResult, PaginationMeta, PaginationParams
from app.services.author_service import AuthorService


@pytest.fixture
def service(mock_repo, mock_uow, monkeypatch):
    s = AuthorService(mock_repo, mock_uow)
    mock_cache = AsyncMock()
    mock_cache.connect = AsyncMock()
    mock_cache.close = AsyncMock()
    mock_cache.get_authors_page = AsyncMock(return_value=None)
    mock_cache.set_authors_page = AsyncMock()
    mock_cache.get_authors_page_search = AsyncMock(return_value=None)
    mock_cache.set_authors_page_search = AsyncMock()
    monkeypatch.setattr(s, "cache", mock_cache)
    return s


@pytest.mark.asyncio
async def test_list_authors_by_page_with_search_calls_repo_with_search(
    service, mock_repo
):
    authors = [
        AuthorEntity(
            id=1,
            first_name="John",
            last_name="Doe",
            nationality=None,
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        ),
    ]
    mock_repo.get_paginated.return_value = PaginatedResult(
        data=authors,
        meta=PaginationMeta(
            total=1,
            page=1,
            size=10,
            count=len(authors),
        ),
    )

    result = await service.list_authors_by_page(page=1, size=10, search="jo")

    assert result.meta.total == 1
    # Repository should be called with PaginationParams and search
    assert mock_repo.get_paginated.called
    call_args = mock_repo.get_paginated.call_args
    pagination_arg = call_args[0][0]  # First positional arg
    assert isinstance(pagination_arg, PaginationParams)
    assert pagination_arg.page == 1
    assert pagination_arg.size == 10
    assert call_args[1]["search"] == "jo"  # Keyword arg
    # Ensure search uses dedicated cache key helpers
    service.cache.get_authors_page_search.assert_called_once()
    service.cache.set_authors_page_search.assert_called_once()


@pytest.mark.asyncio
async def test_list_authors_by_page_without_search_keeps_legacy_cache(
    service, mock_repo
):
    authors = []
    mock_repo.get_paginated.return_value = PaginatedResult(
        data=authors,
        meta=PaginationMeta(
            total=0,
            page=2,
            size=5,
            count=len(authors),
        ),
    )

    await service.list_authors_by_page(page=2, size=5)

    # Repository should be called with PaginationParams without search
    assert mock_repo.get_paginated.called
    call_args = mock_repo.get_paginated.call_args
    pagination_arg = call_args[0][0]  # First positional arg
    assert isinstance(pagination_arg, PaginationParams)
    assert pagination_arg.page == 2
    assert pagination_arg.size == 5
    service.cache.get_authors_page.assert_called_once()
    service.cache.set_authors_page.assert_called_once()

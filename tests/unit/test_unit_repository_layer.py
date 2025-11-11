from uuid import uuid4

import pytest

from app.db.session import get_session
from app.domain.value_objects import BookCreateData, BookUpdateData, PaginationParams
from app.main import app
from app.repositories.book_repository import BookRepository


@pytest.mark.asyncio
async def test_repository_crud_and_pagination_direct(test_author_id):
    # Use the overridden session provided in tests
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)

        # Create a couple of books
        title1 = f"Repo Book {uuid4()}"
        title2 = f"Repo Book {uuid4()}"
        b1 = await repo.create(BookCreateData(title=title1, authors=[test_author_id]))
        b2 = await repo.create(BookCreateData(title=title2, authors=[test_author_id]))

        # Read by id and title
        fetched1 = await repo.get_by_id(b1.id)
        assert fetched1 and fetched1.title == title1
        fetched_by_title = await repo.get_by_title(title2)
        assert fetched_by_title and fetched_by_title.id == b2.id

        # Pagination via get_paginated
        pagination = PaginationParams(page=1, size=1)
        result = await repo.get_paginated(pagination)
        assert isinstance(result.data, list)
        assert result.meta.total >= 2
        assert len(result.data) == 1

        # Update title only: repository.update expects BookUpdateData
        fetched_before = await repo.get_by_id(b1.id)
        updated = await repo.update(
            b1.id,
            BookUpdateData(title="Updated Title", authors=fetched_before.authors),
        )
        assert updated.title == "Updated Title"

        # Delete and ensure it's gone
        ok = await repo.delete(b2.id)
        assert ok is True
        gone = await repo.get_by_id(b2.id)
        assert gone is None

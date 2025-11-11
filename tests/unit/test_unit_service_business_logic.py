from uuid import uuid4

import pytest
from tests.mocks.cache_service import MockCacheService

from app.db.session import get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.value_objects import BookCreateData, BookUpdateData
from app.main import app
from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService


@pytest.mark.asyncio
async def test_service_update_title_only_normalized_and_no_conflict_with_self(
    test_author_id,
):
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        # Create two books
        t1 = f"TitleOnly {uuid4()}"
        t2 = f"Other {uuid4()}"
        from app.domain.entities import BookEntity

        b1 = await repo.create(BookEntity(id=None, title=t1, authors=[test_author_id]))
        await repo.create(BookEntity(id=None, title=t2, authors=[test_author_id]))
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        # Update b1 title with different casing/spaces of the same title: should not conflict
        updated = await service.update_book(b1.id, BookUpdateData(title=f"  {t1.lower()}  "))
        assert updated.id == b1.id
        # Service normalizes with .title(), which also affects hex characters in UUIDs
        assert updated.title == t1.strip().title()

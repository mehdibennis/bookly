import pytest

from app.db.session import get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.value_objects import BookCreateData
from app.main import app
from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService
from tests.mocks.cache_service import MockCacheService


@pytest.mark.asyncio
async def test_unit_of_work_rollback_path(test_author_id):
    """Induce an exception inside the unit of work to trigger rollback branch (line 13)."""
    # Use the raw dependency override session generator
    async for session in app.dependency_overrides[get_session]():
        uow = SqlAlchemyUnitOfWork(session)
        repo = BookRepository(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        # Use a unique title to avoid conflict
        import uuid

        unique_title = f"Rollback Test {uuid.uuid4()}"
        b = await service.create_book(
            BookCreateData(title=unique_title, authors=[test_author_id])
        )
        assert b.id is not None

        class TestExc(Exception):
            pass

        # Trigger exception in context
        with pytest.raises(TestExc):
            async with uow:
                # Perform an operation then raise
                await repo.create(
                    BookCreateData(
                        title=f"Temp Title {uuid.uuid4()}",
                        authors=[test_author_id],
                    )
                )
                raise TestExc("force rollback")
        # Ensure earlier committed book still present (rollback only rolled back inner operations)
        fetched = await repo.get_by_id(b.id)
        assert fetched is not None

import pytest

from app.db.session import get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.value_objects import PaginationParams
from app.main import app
from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService
from tests.mocks.cache_service import MockCacheService


@pytest.mark.asyncio
async def test_list_books_invalid_page_value_error():
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        BookService(repo, uow, cache)
        with pytest.raises(ValueError):
            PaginationParams(page=0, size=10)


@pytest.mark.asyncio
async def test_list_books_invalid_size_value_error():
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        BookService(repo, uow, cache)
        with pytest.raises(ValueError):
            PaginationParams(page=1, size=101)


@pytest.mark.asyncio
async def test_get_book_invalid_id_value_error():
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        with pytest.raises(ValueError):
            await service.get_book(0)


@pytest.mark.asyncio
async def test_get_book_not_found():
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        with pytest.raises(Exception) as exc:
            await service.get_book(99999999)
        assert "not found" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_update_book_not_found():
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        from app.domain.value_objects import BookUpdateData

        with pytest.raises(Exception) as exc:
            await service.partial_update_book(
                99999999, book_data=BookUpdateData(title=None, authors=None)
            )
        assert "not found" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_delete_book_not_found():
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        with pytest.raises(Exception) as exc:
            await service.delete_book(99999999)
        assert "not found" in str(exc.value).lower()

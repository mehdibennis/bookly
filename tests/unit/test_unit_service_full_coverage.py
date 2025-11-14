from uuid import uuid4

import pytest

from app.db.session import get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.entities import BookEntity
from app.domain.exceptions import ConflictException, NotFoundException
from app.domain.value_objects import AuthorCreateData, BookCreateData, BookUpdateData
from app.main import app
from app.repositories.author_repository import AuthorRepository
from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService
from tests.mocks.cache_service import MockCacheService


async def _make_service():
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        yield repo, BookService(repo, uow, cache)


@pytest.mark.asyncio
async def test_create_book_validation_and_conflict(test_author_id):
    async for repo, service in _make_service():
        # Title empty
        with pytest.raises(ValueError):
            await service.create_book(
                BookCreateData(title="   ", authors=[test_author_id])
            )
        # Authors invalid (contains non-positive)
        with pytest.raises(ValueError):
            await service.create_book(BookCreateData(title="Valid", authors=[0]))
        base = f"Title {uuid4()}"
        b1 = await service.create_book(
            BookCreateData(title=base, authors=[test_author_id])
        )
        assert b1.id is not None
        # Duplicate (case + spaces)
        with pytest.raises(ConflictException):
            await service.create_book(
                BookCreateData(title=f"  {base.upper()}  ", authors=[test_author_id])
            )


@pytest.mark.asyncio
async def test_get_book_invalid_and_not_found():
    async for repo, service in _make_service():
        with pytest.raises(ValueError):
            await service.get_book(0)
        with pytest.raises(ValueError):
            await service.get_book(-5)
        with pytest.raises(NotFoundException):
            await service.get_book(999999)


@pytest.mark.asyncio
async def test_update_book_branches(test_author_id):
    async for repo, service in _make_service():
        # Not found
        with pytest.raises(NotFoundException):
            await service.partial_update_book(999999, BookUpdateData(title="X"))
        # Seed two books
        b1 = await service.create_book(
            BookCreateData(title=f"Seed1 {uuid4()}", authors=[test_author_id])
        )
        b2 = await service.create_book(
            BookCreateData(title=f"Seed2 {uuid4()}", authors=[test_author_id])
        )
        # Empty title
        with pytest.raises(ValueError):
            await service.partial_update_book(b1.id, BookUpdateData(title="   "))
        # Duplicate title conflict
        with pytest.raises(ConflictException):
            await service.partial_update_book(b1.id, BookUpdateData(title=b2.title))
        # Authors invalid (contains non-positive)
        with pytest.raises(ValueError):
            await service.partial_update_book(b1.id, BookUpdateData(authors=[0]))
        # Successful partial update (authors only) -> create a second author
        async for session in app.dependency_overrides[get_session]():
            arepo = AuthorRepository(session)
            author2 = await arepo.create(
                AuthorCreateData(first_name=f"Temp{uuid4()}", last_name="Author")
            )
            new_author_id = author2.id
        updated = await service.partial_update_book(
            b1.id, BookUpdateData(authors=[new_author_id])
        )
        assert updated.authors == [new_author_id]
        assert updated.title == b1.title


@pytest.mark.asyncio
async def test_delete_book_paths(test_author_id):
    async for repo, service in _make_service():
        with pytest.raises(ValueError):
            await service.delete_book(0)
        with pytest.raises(ValueError):
            await service.delete_book(-3)
        with pytest.raises(NotFoundException):
            await service.delete_book(777777)
        b = await service.create_book(
            BookCreateData(title=f"Del {uuid4()}", authors=[test_author_id])
        )
        assert await service.delete_book(b.id) is True
        # Now not found
        with pytest.raises(NotFoundException):
            await service.delete_book(b.id)


@pytest.mark.asyncio
async def test_list_books_pagination_error_and_success(test_author_id):
    async for repo, service in _make_service():
        # Errors
        with pytest.raises(ValueError):
            await service.list_books_by_page(page=0, size=10)
        with pytest.raises(ValueError):
            await service.list_books_by_page(page=1, size=0)
        with pytest.raises(ValueError):
            await service.list_books_by_page(page=1, size=101)
        # Seed 12 books
        for i in range(12):
            await repo.create(
                BookCreateData(title=f"P{i}-{uuid4()}", authors=[test_author_id])
            )
        page1 = await service.list_books_by_page(page=1, size=5)
        assert page1.meta.next_page == 2
        assert page1.meta.previous_page is None
        page2 = await service.list_books_by_page(page=2, size=5)
        assert page2.meta.next_page == 3
        assert page2.meta.previous_page == 1
        page3 = await service.list_books_by_page(page=3, size=5)
        # Dynamically assert last page logic instead of hard-coding totals
        # (other tests may have inserted rows)
        meta3 = page3.meta
        if meta3.page == meta3.last_page:
            assert meta3.next_page is None
        else:  # In case extra data seeded globally, ensure next_page advances by 1 until last_page
            assert meta3.next_page == meta3.page + 1
        assert meta3.previous_page == meta3.page - 1


@pytest.mark.asyncio
async def test_repository_update_delete_edge_returns(test_author_id):
    async for repo, service in _make_service():
        # update non existent returns None (service wraps earlier but repo alone used here)
        updated_none = await repo.update(
            999999, BookEntity(id=999999, title="X", authors=[test_author_id])
        )
        assert updated_none is None
        # delete non existent -> False
        assert await repo.delete(999999) is False

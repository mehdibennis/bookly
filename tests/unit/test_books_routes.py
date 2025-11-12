from types import SimpleNamespace

import pytest

from app.api.v1.routes import books as books_module
from app.domain.entities import BookEntity
from app.domain.value_objects import PaginatedResult, PaginationMeta


class FakeBookService:
    async def list_books_by_page(self, page, size):
        be = BookEntity(
            id=1, title="x", authors=[], authors_details=[], authors_number=0
        )
        meta = PaginationMeta(total=1, page=page, size=size, count=1)
        return PaginatedResult(data=[be], meta=meta)

    async def get_book(self, book_id):
        return BookEntity(
            id=book_id, title="t", authors=[], authors_details=[], authors_number=0
        )

    async def create_book(self, book_data):
        return BookEntity(
            id=2,
            title=book_data.title if hasattr(book_data, "title") else "t",
            authors=[],
            authors_details=[],
            authors_number=0,
        )

    async def update_book(self, book_id, book_data):
        return BookEntity(
            id=book_id,
            title=book_data.title if hasattr(book_data, "title") else "t",
            authors=[],
            authors_details=[],
            authors_number=0,
        )

    async def delete_book(self, book_id):
        return None


@pytest.mark.asyncio
async def test_books_route_handlers_direct_call():
    svc = FakeBookService()
    # list_books
    resp = await books_module.list_books(page=1, size=10, book_service=svc)
    assert resp.meta.total == 1

    # get_book
    user = SimpleNamespace(username="u", roles=["admin"])  # user required by dependency
    book = await books_module.get_book(1, book_service=svc, user=user)
    assert book.id == 1

    # create_book
    BookCreate = SimpleNamespace(title="new", authors=[1])
    created = await books_module.create_book(BookCreate, book_service=svc, user=user)
    assert created.id == 2

    # update_book
    BookUpdate = SimpleNamespace(title="up", authors=None)
    updated = await books_module.update_book(2, BookUpdate, book_service=svc, user=user)
    assert updated.id == 2

    # patch_book calls same service
    patched = await books_module.patch_book(2, BookUpdate, book_service=svc, user=user)
    assert patched.id == 2

    # delete_book returns None (204)
    res = await books_module.delete_book(2, book_service=svc, user=user)
    assert res is None

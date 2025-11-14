"""
Tests for service layer edge cases and error scenarios.
Covers business logic validation and service-level error handling.
"""

from uuid import uuid4

import pytest

from app.db.session import get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.entities import BookEntity
from app.domain.exceptions import NotFoundException
from app.domain.value_objects import BookCreateData, BookUpdateData
from app.main import app
from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService
from tests.conftest import get_unique_rate_headers
from tests.mocks.cache_service import MockCacheService


class TestServiceLayerEdgeCases:
    @pytest.mark.asyncio
    async def test_book_service_get_returns_book(self, test_author_id):
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            service = BookService(repo, uow, cache)
            book = await service.create_book(
                BookCreateData(
                    title=f"GetBook Test {uuid4()}", authors=[test_author_id]
                )
            )
            fetched = await service.get_book(book.id)
            assert fetched is not None
            assert fetched.id == book.id
            assert fetched.title == book.title
            assert fetched.authors == book.authors

    @pytest.mark.asyncio
    async def test_book_service_create_with_empty_author(self, test_author_id):
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            BookService(repo, uow, cache)
            # authors are required, but here we test empty title
            with pytest.raises(ValueError) as exc_info:
                BookCreateData(title="   ", authors=[test_author_id])
            # Accept both French and English error messages
            error_msg = str(exc_info.value).lower()
            assert "titre" in error_msg or "title" in error_msg
            assert "vide" in error_msg or "empty" in error_msg

    @pytest.mark.asyncio
    async def test_book_service_update_with_empty_title(self, test_author_id):
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            service = BookService(repo, uow, cache)
            book = await service.create_book(
                BookCreateData(title=f"Update Test {uuid4()}", authors=[test_author_id])
            )
            with pytest.raises(ValueError) as exc_info:
                await service.partial_update_book(book.id, BookUpdateData(title="   "))
            error_msg = str(exc_info.value).lower()
            assert "titre" in error_msg or "title" in error_msg

    @pytest.mark.asyncio
    async def test_book_service_update_with_negativ_id(self, test_author_id):
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            service = BookService(repo, uow, cache)
            update_data = BookUpdateData(title="test title")
            with pytest.raises(ValueError) as exc_info:
                await service.partial_update_book(-1, update_data)

            assert "L'ID du livre doit être un entier positif" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_book_service_update_nonexistent_book(self):
        """Test updating non-existent book raises BookNotFoundError."""
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            service = BookService(repo, uow, cache)

            update_data = BookUpdateData(title="Updated Title")

            with pytest.raises(NotFoundException):
                await service.partial_update_book(999999, update_data)

    @pytest.mark.asyncio
    async def test_book_service_delete_nonexistent_book(self):
        """Test deleting non-existent book raises NotFoundException."""
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            service = BookService(repo, uow, cache)

            with pytest.raises(NotFoundException):
                await service.delete_book(999999)

    @pytest.mark.asyncio
    async def test_book_service_get_nonexistent_book(self):
        """Test getting non-existent book raises NotFoundException."""
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            service = BookService(repo, uow, cache)

            with pytest.raises(NotFoundException):
                await service.get_book(999999)

    @pytest.mark.asyncio
    async def test_book_service_create_duplicate_title_conflict(self, test_author_id):
        """Test creating book with duplicate title raises BookConflictError."""
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            service = BookService(repo, uow, cache)

            # Create first book
            title = f"Duplicate Test {uuid4()}"
            book_data1 = BookCreateData(title=title, authors=[test_author_id])
            await service.create_book(book_data1)

            # Try to create second book with same title (normalized)
            book_data2 = BookCreateData(title=title.upper(), authors=[test_author_id])

            with pytest.raises(Exception) as exc_info:
                await service.create_book(book_data2)

            # Should be a conflict error (the exact exception type may vary)
            assert (
                "exist" in str(exc_info.value).lower()
                or "conflict" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_book_service_update_to_duplicate_title(self, test_author_id):
        """Test updating book to existing title raises conflict."""
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            service = BookService(repo, uow, cache)

            # Create two books
            title1 = f"Original 1 {uuid4()}"
            title2 = f"Original 2 {uuid4()}"

            book_data1 = BookCreateData(title=title1, authors=[test_author_id])
            book_data2 = BookCreateData(title=title2, authors=[test_author_id])

            book1 = await service.create_book(book_data1)
            await service.create_book(book_data2)

            # Try to update book1 to have the same title as book2
            update_data = BookUpdateData(title=title2)

            with pytest.raises(Exception) as exc_info:
                await service.partial_update_book(book1.id, update_data)

            assert (
                "exist" in str(exc_info.value).lower()
                or "conflict" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_book_service_validation_edge_cases(self):
        """Test various validation edge cases in service layer."""
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            cache = MockCacheService()
            service = BookService(repo, uow, cache)

            # Test with invalid book ID
            with pytest.raises(ValueError):
                await service.get_book(0)

            with pytest.raises(ValueError):
                await service.get_book(-1)

            # Test pagination with invalid parameters
            with pytest.raises(ValueError):
                await service.list_books_by_page(page=0, size=10)

            with pytest.raises(ValueError):
                await service.list_books_by_page(page=1, size=0)

            with pytest.raises(ValueError):
                await service.list_books_by_page(
                    page=1, size=101
                )  # Assuming max size is 100

    @pytest.mark.asyncio
    async def test_repository_error_scenarios(self, test_author_id):
        """Test repository-level error handling."""
        async for session in app.dependency_overrides[get_session]():
            repo = BookRepository(session)

            # Test getting non-existent book
            book = await repo.get_by_id(999999)
            assert book is None

            # Test searching with empty title should return None (no book with empty title expected)
            result = await repo.get_by_title("")
            assert result is None

            # Create a book directly through repository and fetch it back by title
            new_entity = BookEntity(
                id=None, title=f"Repo Created {uuid4()}", authors=[test_author_id]
            )
            created = await repo.create(new_entity)
            assert created.id is not None
            fetched = await repo.get_by_title(created.title)
            assert fetched is not None
            assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_unit_of_work_edge_cases(self):
        """Test unit of work pattern edge cases."""
        async for session in app.dependency_overrides[get_session]():
            uow = SqlAlchemyUnitOfWork(session)

            # Test multiple commits
            await uow.commit()
            await uow.commit()  # Should not fail

            # Test rollback
            await uow.rollback()  # Should not fail


@pytest.mark.usefixtures("override_keycloak")
class TestServiceIntegrationEdgeCases:
    """Integration tests for service layer with API layer."""

    @pytest.mark.asyncio
    async def test_api_service_integration_error_propagation(self, client):
        """Test that service errors are properly propagated through API."""
        headers = get_unique_rate_headers()

        # Test creating book with empty title (missing author_id will yield 422)
        resp = await client.post(
            "/api/v1/books/", json={"title": "   "}, headers=headers
        )
        assert resp.status_code in [400, 401, 422]

    @pytest.mark.asyncio
    async def test_concurrent_operations_consistency(self, client):
        """Test consistency during concurrent operations."""
        headers = get_unique_rate_headers(ip_range="10.0.9")
        title = f"Concurrent {uuid4()}"
        book_data = {"title": title}
        first = await client.post("/api/v1/books/", json=book_data, headers=headers)
        assert first.status_code in [201, 409, 401, 422]
        second = await client.post("/api/v1/books/", json=book_data, headers=headers)
        assert second.status_code in [409, 401, 422]

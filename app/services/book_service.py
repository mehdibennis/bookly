# logique métier (utilise le repo)
from app.domain.entities import BookEntity
from app.domain.exceptions import ConflictException, NotFoundException
from app.domain.repositories import IBookRepository, ICacheService
from app.domain.unit_of_work import IUnitOfWork
from app.domain.value_objects import (
    BookCreateData,
    BookUpdateData,
    PaginatedResult,
    PaginationParams,
)


class BookService:
    """
    Service layer for book-related business logic.

    Responsibilities:
    - Input validation and normalization
    - Conflict and not-found checks with domain-specific exceptions
    - Pagination calculation
    - Optional caching for paginated listings
    - Delegation to repository under a Unit of Work
    """

    def __init__(self, repo: IBookRepository, uow: IUnitOfWork, cache: ICacheService):
        self.repo = repo
        self.uow = uow
        self.cache = cache

    async def list_books_by_page(
        self, page: int = 1, size: int = 10
    ) -> PaginatedResult[BookEntity]:
        """
        Return a paginated list of books with metadata.

        Args:
            page: Page number (1-based). Must be >= 1.
            size: Page size. Must be in [1, 100].

        Returns:
            PaginatedResult[BookEntity]: Paginated books with metadata.
        """
        await self.cache.connect()
        cached = await self.cache.get_books_page(page, size)
        if cached:
            return cached

        pagination = PaginationParams(page=page, size=size)
        result = await self.repo.get_paginated(pagination)
        await self.cache.set_books_page(page, size, result)
        return result

    async def get_book(self, book_id: int) -> BookEntity:
        """
        Retrieve a book by its ID.

        Args:
            book_id: Positive integer identifier of the book.

        Raises:
            ValueError: If book_id <= 0.
            NotFoundException: If the book does not exist.
        """
        if book_id <= 0:
            raise ValueError("L'ID du livre doit être un entier positif.")
        book = await self.repo.get_by_id(book_id)
        if not book:
            raise NotFoundException(f"Book with id={book_id} not found.")
        return book

    async def create_book(self, book_data: BookCreateData) -> BookEntity:
        """
        Create a new book after validating uniqueness.

        Args:
            book_data: BookCreateData with title and authors.

        Raises:
            ConflictException: If a book with the same normalized title exists.
        """
        # Create normalized entity for validation
        book_entity = BookEntity(
            id=None, title=book_data.title, authors=list(book_data.authors)
        ).normalize()

        existing_book = await self.repo.get_by_title(book_entity.title)
        if existing_book:
            raise ConflictException(
                f"A book with the title '{book_data.title}' already exists."
            )

        # Create normalized data for repository
        normalized_data = BookCreateData(
            title=book_entity.title,  # Use normalized title
            authors=book_data.authors,
        )

        async with self.uow:
            await self.cache.invalidate_books_cache()
            return await self.repo.create(normalized_data)

    async def partial_update_book(
        self, book_id: int, book_data: BookUpdateData
    ) -> BookEntity:
        """
        Update an existing book's fields.

        Args:
            book_id: Positive integer identifier of the book to update.
            book_data: BookUpdateData with optional title/authors.

        Raises:
            ValueError: If book_id <= 0.
            NotFoundException: If the book does not exist.
            ConflictException: If updating title conflicts with another book.
        """
        if book_id <= 0:
            raise ValueError("L'ID du livre doit être un entier positif.")

        existing_book = await self.repo.get_by_id(book_id)
        if not existing_book:
            raise NotFoundException(f"Book with id={book_id} not found.")

        # Normalize title if provided and check conflict
        normalized_title = None
        if book_data.title is not None:
            normalized_title = book_data.title.strip().title()
            book_with_title = await self.repo.get_by_title(normalized_title)
            if book_with_title and book_with_title.id != book_id:
                raise ConflictException(
                    f"Another book with the title '{book_data.title}' already exists."
                )

        # Create normalized data for repository
        normalized_data = BookUpdateData(
            title=normalized_title,  # Use normalized title
            authors=book_data.authors,
        )

        async with self.uow:
            await self.cache.invalidate_books_cache()
            updated = await self.repo.update(book_id, normalized_data)
            # Existence was checked earlier; updated should not be None
            assert updated is not None
            return updated

    async def delete_book(self, book_id: int) -> bool:
        """
        Delete a book by ID.

        Args:
            book_id: Positive integer identifier of the book to delete.

        Raises:
            ValueError: If book_id <= 0.
            NotFoundException: If the book does not exist.

        Returns:
            bool: True if deletion succeeded.
        """
        if book_id <= 0:
            raise ValueError("L'ID du livre doit être un entier positif.")
        existing_book = await self.repo.get_by_id(book_id)
        if not existing_book:
            raise NotFoundException(f"Book with id={book_id} not found.")
        async with self.uow:
            await self.cache.invalidate_books_cache()
            return await self.repo.delete(book_id)

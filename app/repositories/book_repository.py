# Repository implementation using SQLAlchemy

import logging
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.book_model import Book
from app.domain.entities import BookEntity
from app.domain.repositories import IBookRepository
from app.domain.value_objects import BookCreateData, BookUpdateData, PaginatedResult, PaginationMeta, PaginationParams

_LOGGER = logging.getLogger(__name__)


class BookRepository(IBookRepository):
    """SQLAlchemy implementation of IBookRepository.

    Interacts with the database using an AsyncSession and maps ORM models
    to domain entities. All methods are async and commit as needed.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, book_id: int) -> BookEntity | None:
        """Fetch a single book by its ID, return a domain entity or None."""
        stmt = (
            select(Book).options(selectinload(Book.authors)).where(Book.id == book_id)
        )
        result = await self.session.execute(stmt)
        book = result.scalar_one_or_none()
        if not book:
            return None
        return self._model_to_entity(book)

    async def get_by_title(self, title: str) -> BookEntity | None:
        """Fetch a single book by its exact title, return a domain entity or None."""
        stmt = (
            select(Book).options(selectinload(Book.authors)).where(Book.title == title)
        )
        result = await self.session.execute(stmt)
        book = result.scalar_one_or_none()
        if not book:
            return None
        return self._model_to_entity(book)

    async def get_paginated(
        self, pagination: PaginationParams
    ) -> PaginatedResult[BookEntity]:
        """Return a paginated result of books."""
        # Get books for the page
        stmt = (
            select(Book)
            .options(selectinload(Book.authors))
            .offset(pagination.skip)
            .limit(pagination.limit)
        )
        result = await self.session.execute(stmt)
        books = result.scalars().all()

        # Get total count
        count_stmt = select(func.count(Book.id))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # Convert to entities
        entities = [self._model_to_entity(book) for book in books]

        # Create metadata
        meta = PaginationMeta(
            total=total,
            page=pagination.page,
            size=pagination.size,
            count=len(entities),
        )

        return PaginatedResult(data=entities, meta=meta)

    async def create(self, book_data: BookCreateData) -> BookEntity:
        """Create a new book from domain data."""
        # Create the book model
        book = Book(title=book_data.title)

        # Add authors if any
        if book_data.authors:
            from app.db.models.author_model import Author

            author_stmt = select(Author).where(Author.id.in_(book_data.authors))
            author_result = await self.session.execute(author_stmt)
            authors = author_result.scalars().all()
            book.authors = authors

        self.session.add(book)
        await self.session.flush()  # Get the ID
        await self.session.refresh(book, ["authors"])  # Refresh with authors
        return self._model_to_entity(book)

    async def update(
        self, book_id: int, book_data: BookUpdateData
    ) -> BookEntity | None:
        """Update an existing book with new data."""
        stmt = (
            select(Book).options(selectinload(Book.authors)).where(Book.id == book_id)
        )
        result = await self.session.execute(stmt)
        book = result.scalar_one_or_none()

        if not book:
            return None

        # Update fields if provided
        if book_data.title is not None:
            book.title = book_data.title

        if book_data.authors is not None:
            from app.db.models.author_model import Author

            author_stmt = select(Author).where(Author.id.in_(book_data.authors))
            author_result = await self.session.execute(author_stmt)
            authors = author_result.scalars().all()
            book.authors = authors

        await self.session.flush()
        await self.session.refresh(book, ["authors"])
        return self._model_to_entity(book)

    async def delete(self, book_id: int) -> bool:
        """Delete a book by its ID."""
        stmt = select(Book).where(Book.id == book_id)
        result = await self.session.execute(stmt)
        book = result.scalar_one_or_none()

        if not book:
            return False

        await self.session.delete(book)
        return True

    def _model_to_entity(self, book: Book) -> BookEntity:
        """Convert SQLAlchemy model to domain entity."""
        author_ids = [cast(int, a.id) for a in (book.authors or [])]
        author_details = []

        for author in book.authors or []:
            author_details.append(
                {
                    "id": author.id,
                    "first_name": author.first_name,
                    "last_name": author.last_name,
                    "birth_date": (
                        author.birth_date.isoformat() if author.birth_date else None
                    ),
                    "death_date": (
                        author.death_date.isoformat() if author.death_date else None
                    ),
                    "nationality": author.nationality,
                    "bio": author.bio,
                    "photo_url": author.photo_url,
                    "created_at": (
                        author.created_at.isoformat() if author.created_at else None
                    ),
                    "updated_at": (
                        author.updated_at.isoformat() if author.updated_at else None
                    ),
                }
            )

        return BookEntity(
            id=cast(int, book.id),
            title=cast(str, book.title),
            authors=author_ids,
            authors_details=author_details,
            authors_number=len(author_ids),
        )

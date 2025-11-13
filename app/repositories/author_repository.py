# requêtes DB pures (SQLAlchemy)

import logging
from datetime import date as date_type
from datetime import datetime as datetime_type
from typing import cast

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.author_model import Author
from app.domain.entities import AuthorEntity
from app.domain.repositories import IAuthorRepository
from app.domain.value_objects import (
    AuthorCreateData,
    AuthorUpdateData,
    PaginatedResult,
    PaginationMeta,
    PaginationParams,
)

_LOGGER = logging.getLogger(__name__)


def _parse_date(value: date_type | str | None) -> date_type | None:
    """Parse input into a date object.

    Accepts:
    - datetime.date: returned as-is
    - ISO string (YYYY-MM-DD): parsed via fromisoformat
    - None/invalid: returns None
    """
    if value is None:
        return None
    # If already a date object, return it
    if isinstance(value, date_type):
        return value
    # If a string, try ISO format
    if isinstance(value, str) and value:
        try:
            return date_type.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    # Any other type is unsupported
    return None


class AuthorRepository(IAuthorRepository):
    """SQLAlchemy implementation of IAuthorRepository.

    Interacts with the database using an AsyncSession and maps ORM models
    to domain entities. All methods are async and commit as needed.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _model_to_entity(self, author: Author) -> AuthorEntity:
        """Convert SQLAlchemy model to domain entity."""
        return AuthorEntity(
            id=cast(int, author.id),
            first_name=cast(str, author.first_name),
            last_name=cast(str, author.last_name),
            birth_date=cast(date_type | None, author.birth_date),
            death_date=cast(date_type | None, author.death_date),
            nationality=cast(str | None, author.nationality),
            bio=cast(str | None, author.bio),
            photo_url=cast(str | None, author.photo_url),
            created_at=cast(datetime_type | None, author.created_at),
            updated_at=cast(datetime_type | None, author.updated_at),
        )

    async def get_by_id(self, author_id: int) -> AuthorEntity | None:
        """Fetch a single author by its ID, return a domain entity or None."""
        stmt = select(Author).where(Author.id == author_id)
        result = await self.session.execute(stmt)
        author = result.scalar_one_or_none()
        if not author:
            return None
        return self._model_to_entity(author)

    async def get_by_full_name(
        self, first_name: str, last_name: str
    ) -> AuthorEntity | None:
        """Fetch a single author by their full name, return a domain entity or None."""
        stmt = select(Author).where(
            Author.first_name == first_name, Author.last_name == last_name
        )
        result = await self.session.execute(stmt)
        author = result.scalar_one_or_none()
        if not author:
            return None
        return self._model_to_entity(author)

    async def get_paginated(
        self, pagination: PaginationParams, search: str | None = None
    ) -> PaginatedResult[AuthorEntity]:
        """Return a paginated result of authors.

        Optionally filters by 'search' (ILIKE) on first_name or last_name.
        """
        stmt = select(Author)
        count_stmt = select(func.count(Author.id))

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(Author.first_name.ilike(pattern), Author.last_name.ilike(pattern))
            )
            count_stmt = count_stmt.where(
                or_(Author.first_name.ilike(pattern), Author.last_name.ilike(pattern))
            )

        stmt = stmt.offset(pagination.skip).limit(pagination.limit)
        result = await self.session.execute(stmt)
        authors = result.scalars().all()

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        entities = [self._model_to_entity(a) for a in authors]

        meta = PaginationMeta(
            total=total, page=pagination.page, size=pagination.size, count=len(entities)
        )

        return PaginatedResult(data=entities, meta=meta)

    async def create(self, author_data: AuthorCreateData) -> AuthorEntity:
        """Create a new author and return it as a domain entity."""
        new_author = Author(
            first_name=author_data.first_name,
            last_name=author_data.last_name,
            birth_date=_parse_date(author_data.birth_date),
            death_date=_parse_date(author_data.death_date),
            nationality=author_data.nationality,
            bio=author_data.bio,
            photo_url=author_data.photo_url,
        )
        self.session.add(new_author)
        # Flush to populate DB-generated fields (e.g. id) but do not commit here.
        # Transaction commit is the responsibility of the UnitOfWork.
        await self.session.flush()
        return self._model_to_entity(new_author)

    async def update(
        self, author_id: int, author_data: AuthorUpdateData
    ) -> AuthorEntity | None:
        """Update an existing author; returns the updated entity or None if missing."""
        stmt = select(Author).where(Author.id == author_id)
        result = await self.session.execute(stmt)
        db_author = result.scalar_one_or_none()

        if not db_author:
            return None

        # Update only fields that are provided (not None)
        if author_data.first_name is not None:
            setattr(db_author, "first_name", author_data.first_name)
        if author_data.last_name is not None:
            setattr(db_author, "last_name", author_data.last_name)
        if author_data.birth_date is not None:
            setattr(db_author, "birth_date", _parse_date(author_data.birth_date))
        if author_data.death_date is not None:
            setattr(db_author, "death_date", _parse_date(author_data.death_date))
        if author_data.nationality is not None:
            setattr(db_author, "nationality", author_data.nationality)
        if author_data.bio is not None:
            setattr(db_author, "bio", author_data.bio)
        if author_data.photo_url is not None:
            setattr(db_author, "photo_url", author_data.photo_url)

        self.session.add(db_author)
        # Flush changes so generated columns (if any) are available.
        await self.session.flush()
        await self.session.refresh(db_author)

        return self._model_to_entity(db_author)

    async def partial_update(
        self, author_id: int, author_data: AuthorUpdateData
    ) -> AuthorEntity | None:
        """
        Partially update an author with only the provided fields.

        Args:
            author_id: ID of the author to update
            author_data: AuthorUpdateData containing only the fields to update

        Returns:
            Updated AuthorEntity or None if author not found
        """
        stmt = select(Author).where(Author.id == author_id)
        result = await self.session.execute(stmt)
        db_author = result.scalar_one_or_none()

        if not db_author:
            return None

        # Update only the provided fields, converting date strings to date objects
        update_data = {k: v for k, v in author_data.__dict__.items() if v is not None}
        for field, value in update_data.items():
            if not hasattr(db_author, field):
                continue
            if field in {"birth_date", "death_date"}:
                setattr(db_author, field, _parse_date(value))
            else:
                setattr(db_author, field, value)

        self.session.add(db_author)
        await self.session.flush()
        # Ensure server-default/triggered columns (e.g., updated_at) are loaded
        await self.session.refresh(db_author)

        return self._model_to_entity(db_author)

    async def delete(self, author_id: int) -> bool:
        """Delete an author by ID; returns True if a row was deleted, else False."""
        stmt = select(Author).where(Author.id == author_id)
        result = await self.session.execute(stmt)
        db_author = result.scalar_one_or_none()
        if db_author:
            await self.session.delete(db_author)
            # Deletion is flushed here but commit is handled by UnitOfWork.
            await self.session.flush()
            return True
        return False

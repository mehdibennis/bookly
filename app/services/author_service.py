# Business logic (uses the repository)
# Redis cache to add here
import logging
from typing import Any

from app.domain.entities import AuthorEntity
from app.domain.exceptions import ConflictException, NotFoundException
from app.domain.repositories import IAuthorRepository, ICacheService
from app.domain.unit_of_work import IUnitOfWork
from app.domain.value_objects import AuthorCreateData, AuthorUpdateData


class AuthorService:
    """
    Service layer for author-related business logic.

    Responsibilities:
    - Input validation and normalization
    - Conflict and not-found checks with domain-specific exceptions
    - Pagination calculation
    - Optional Redis caching for paginated listings
    - Delegation to repository under a Unit of Work
    """

    def __init__(
        self,
        repo: IAuthorRepository,
        uow: IUnitOfWork,
        cache: ICacheService | None = None,
    ):
        self.repo = repo
        self.uow = uow
        # cache attribute may be None if no cache is provided; callers (or
        # DI) should supply a concrete cache implementation. Guard cache
        # usage throughout the service when it is optional for tests.
        self.cache: ICacheService | None = cache
        self._logger = logging.getLogger(__name__)

    async def list_authors_by_page(
        self, page: int = 1, size: int = 10, search: str | None = None
    ):
        """
        Return a paginated list of authors with metadata.

        Args:
            page: Page number (1-based). Must be >= 1.
            size: Page size. Must be in [1, 100].
            search: Optional free-text search applied to first_name and last_name (ILIKE).

        Raises:
            ValueError: If page/size are out of allowed bounds.

        Returns:
            dict: { "data": [AuthorEntity...], "meta": { total, page, size, count, last_page, next_page, previous_page } }
        """
        if page < 1:
            raise ValueError("Page number must be >= 1.")
        if size < 1 or size > 100:
            raise ValueError("Page size must be between 1 and 100.")
        # Only interact with the cache if one was provided
        if self.cache is not None:
            await self.cache.connect()
            # Use different cache key when search filter is provided to avoid collisions
            if search:
                # Use search-aware cache helper when available
                cached = await self.cache.get_authors_page_search(page, size, search)
            else:
                cached = await self.cache.get_authors_page(page, size)
            if cached:  # pragma: no cover - cache hit depends on environment
                await self.cache.close()
                return cached

        from app.domain.value_objects import PaginationParams

        pagination = PaginationParams(page=page, size=size)
        result = await self.repo.get_paginated(pagination, search=search)

        # Cache the domain PaginatedResult and return it. API layer will handle
        # serialization to response DTOs via mappers.
        if self.cache is not None:
            if search:
                await self.cache.set_authors_page_search(page, size, search, result)
            else:
                await self.cache.set_authors_page(page, size, result)
            await self.cache.close()
        return result

    async def get_author(self, author_id: int) -> AuthorEntity:
        """
        Retrieve an author by its ID.

        Args:
            author_id: Positive integer identifier of the author.

        Raises:
            ValueError: If author_id <= 0.
            NotFoundException: If the author does not exist.
        """
        self._logger.debug("get_author called with author_id=%s", author_id)
        if author_id <= 0:
            raise ValueError("Author ID must be a positive integer.")
        author = await self.repo.get_by_id(author_id)
        if not author:
            raise NotFoundException(f"Author with id={author_id} not found.")
        return author

    async def create_author(self, author_in: AuthorCreateData) -> AuthorEntity:
        """
        Create a new author after validating uniqueness and input fields.

        Args:
            author_in: AuthorCreateData value object with author details.

        Raises:
            ValueError: If first_name/last_name are empty or whitespace.
            ConflictException: If an author with the same normalized name exists.
        """
        if not author_in.first_name or not author_in.first_name.strip():
            raise ValueError("Author's first name cannot be empty.")
        if not author_in.last_name or not author_in.last_name.strip():
            raise ValueError("Author's last name cannot be empty.")

        # Normalize names
        first_name = author_in.first_name.strip().title()
        last_name = author_in.last_name.strip().title()

        # Check for existing author
        existing_author = await self.repo.get_by_full_name(first_name, last_name)
        if existing_author:
            raise ConflictException(
                f"An author named '{first_name} {last_name}' already exists."
            )

        # Create normalized data
        normalized_data = AuthorCreateData(
            first_name=first_name,
            last_name=last_name,
            nationality=author_in.nationality,
            birth_date=author_in.birth_date,
            death_date=author_in.death_date,
            bio=author_in.bio,
            photo_url=author_in.photo_url,
        )

        async with self.uow:
            return await self.repo.create(normalized_data)

    async def partial_update_author(
        self, author_id: int, author_in: AuthorUpdateData
    ) -> AuthorEntity:
        """
        Partially update an existing author (PATCH semantic).
        Only updates fields that are explicitly provided in the request.

        Args:
            author_id: Positive integer identifier of the author to update.
            author_in: AuthorUpdateData value object with optional fields.

        Raises:
            ValueError: If author_id <= 0, or provided fields are invalid.
            NotFoundException: If the author does not exist.
            ConflictException: If updating name conflicts with another author.
        """
        if author_id <= 0:
            raise ValueError("Author ID must be a positive integer.")

        # Check if author exists
        existing_author = await self.repo.get_by_id(author_id)
        if not existing_author:
            raise NotFoundException(f"Author with id={author_id} not found.")

        # Validate and normalize provided fields
        first_name = (
            author_in.first_name.strip().title()
            if author_in.first_name is not None
            else None
        )
        last_name = (
            author_in.last_name.strip().title()
            if author_in.last_name is not None
            else None
        )
        nationality = (
            author_in.nationality.strip().title()
            if author_in.nationality is not None
            else None
        )
        bio = author_in.bio.strip() if author_in.bio is not None else None
        photo_url = (
            author_in.photo_url.strip() if author_in.photo_url is not None else None
        )

        # Check for name conflicts if name fields are being updated
        if first_name is not None or last_name is not None:
            check_first = (
                first_name if first_name is not None else existing_author.first_name
            )
            check_last = (
                last_name if last_name is not None else existing_author.last_name
            )
            author_with_name = await self.repo.get_by_full_name(check_first, check_last)
            if author_with_name and author_with_name.id != author_id:
                raise ConflictException(
                    f"An author named '{check_first} {check_last}' already exists."
                )

        # Build dict with only the fields that are provided (not None)
        update_dict: dict[str, Any] = {}
        if first_name is not None:
            update_dict["first_name"] = first_name
        if last_name is not None:
            update_dict["last_name"] = last_name
        if nationality is not None:
            update_dict["nationality"] = nationality
        if author_in.birth_date is not None:
            update_dict["birth_date"] = author_in.birth_date
        if author_in.death_date is not None:
            update_dict["death_date"] = author_in.death_date
        if bio is not None:
            update_dict["bio"] = bio
        if photo_url is not None:
            update_dict["photo_url"] = photo_url

        # If no fields to update, return existing author
        if not update_dict:
            return existing_author

        # Convert dict to AuthorUpdateData for repository
        update_data = AuthorUpdateData(
            first_name=update_dict.get("first_name"),
            last_name=update_dict.get("last_name"),
            birth_date=update_dict.get("birth_date"),
            death_date=update_dict.get("death_date"),
            nationality=update_dict.get("nationality"),
            bio=update_dict.get("bio"),
            photo_url=update_dict.get("photo_url"),
        )

        # Use repository's partial_update method
        async with self.uow:
            updated = await self.repo.partial_update(author_id, update_data)
            # We checked existence earlier; this is a safe narrow cast
            assert updated is not None
            return updated

    async def delete_author(self, author_id: int) -> bool:
        """
        Delete an author by ID.

        Args:
            author_id: Positive integer identifier of the author to delete.

        Raises:
            ValueError: If book_id <= 0.
            NotFoundException: If the author does not exist.

        Returns:
            bool: True if deletion succeeded.
        """
        if author_id <= 0:
            raise ValueError("Author ID must be a positive integer.")
        existing_author = await self.repo.get_by_id(author_id)
        if not existing_author:
            raise NotFoundException(f"Author with id={author_id} not found.")
        async with self.uow:
            return await self.repo.delete(author_id)

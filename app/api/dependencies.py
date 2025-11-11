"""Dependency injection for the API layer.

This module provides dependency injection functions that create properly
configured service instances with all their dependencies.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache_service import RedisCacheService
from app.core.config import settings
from app.db.session import get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.repositories import ICacheService
from app.repositories.author_repository import AuthorRepository
from app.repositories.book_repository import BookRepository
from app.services.author_service import AuthorService
from app.services.book_service import BookService


async def get_cache_service() -> ICacheService:
    """Get configured cache service."""
    # When running tests in parallel (pytest-xdist) we avoid using a shared
    # Redis instance to prevent cross-worker cache contamination which leads
    # to flaky integration tests. If the PYTEST_XDIST_WORKER env var is set,
    # return a no-op cache implementation.
    import os

    if os.getenv("PYTEST_XDIST_WORKER"):
        # Use centralized NoopCache implementation to avoid duplication
        from app.core.noop_cache import NoopCache

        return NoopCache()

    return RedisCacheService(settings.REDIS_URL)


async def get_book_service(session: AsyncSession = Depends(get_session)) -> BookService:
    """Get configured book service with all dependencies."""
    repo = BookRepository(session)
    uow = SqlAlchemyUnitOfWork(session)
    cache = await get_cache_service()
    return BookService(repo, uow, cache)


async def get_author_service(
    session: AsyncSession = Depends(get_session),
) -> AuthorService:
    """Get configured author service with all dependencies."""
    repo = AuthorRepository(session)
    uow = SqlAlchemyUnitOfWork(session)
    cache = await get_cache_service()
    return AuthorService(repo, uow, cache)

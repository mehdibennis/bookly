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
from app.repositories.store_repository import StoreRepository
from app.services.author_service import AuthorService
from app.services.book_service import BookService
from app.services.store_service import StoreService


async def get_cache_service() -> ICacheService:
    """Get configured cache service."""
    # Always return the configured Redis-backed cache service. Tests and
    # test fixtures are responsible for patching/mocking the backing
    # implementation when needed (e.g. pytest autouse mocks used in tests).
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


async def get_store_service(
    session: AsyncSession = Depends(get_session),
) -> StoreService:
    """Get configured store service with all dependencies."""
    repo = StoreRepository(session)
    uow = SqlAlchemyUnitOfWork(session)
    return StoreService(repo, uow)

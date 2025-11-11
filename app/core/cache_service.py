"""Redis cache service implementation.

This module provides the concrete implementation of the ICacheService interface
using Redis as the caching backend.
"""
import json
import logging
from typing import Any

import redis.asyncio as redis

from app.domain.entities import AuthorEntity, BookEntity
from app.domain.repositories import ICacheService
from app.domain.value_objects import PaginatedResult, PaginationMeta

_LOGGER = logging.getLogger(__name__)


class RedisCacheService(ICacheService):
    """Redis implementation of the cache service interface."""

    def __init__(self, redis_url: str, ttl: int = 3600):
        """Initialize Redis cache service.
        
        Args:
            redis_url: Redis connection URL
            ttl: Time to live for cached items in seconds (default: 1 hour)
        """
        self.redis_url = redis_url
        self.ttl = ttl
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if not self._redis:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            try:
                await self._redis.ping()
                _LOGGER.info("Connected to Redis successfully")
            except Exception as e:
                _LOGGER.error(f"Failed to connect to Redis: {e}")
                self._redis = None
                raise

    async def close(self) -> None:  # pragma: no cover
        """Close the underlying Redis connection if open."""
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                # best-effort close; swallow errors but log
                _LOGGER.debug("Error while closing Redis connection", exc_info=True)
            finally:
                self._redis = None
    # pragma: no cover - best-effort connection close and test coverage for remote Redis


    async def get_books_page(self, page: int, size: int) -> PaginatedResult[BookEntity] | None:
        """Get cached books page."""
        if not self._redis:
            return None
            
        try:
            key = f"books:page:{page}:size:{size}"
            cached_data = await self._redis.get(key)
            if not cached_data:
                return None
                
            data = json.loads(cached_data)
            books = [self._dict_to_book_entity(book_dict) for book_dict in data["data"]]
            meta = PaginationMeta(**data["meta"])
            return PaginatedResult(data=books, meta=meta)
            
        except Exception as e:
            _LOGGER.warning(f"Failed to get books from cache: {e}")
            return None

    async def set_books_page(self, page: int, size: int, result: PaginatedResult[BookEntity]) -> None:
        """Cache books page."""
        if not self._redis:
            return
            
        try:
            key = f"books:page:{page}:size:{size}"
            data = {
                "data": [self._book_entity_to_dict(book) for book in result.data],
                "meta": {
                    "total": result.meta.total,
                    "page": result.meta.page,
                    "size": result.meta.size,
                    "count": result.meta.count,
                }
            }
            await self._redis.setex(key, self.ttl, json.dumps(data))
            _LOGGER.debug(f"Cached books page {page} with size {size}")
            
        except Exception as e:
            _LOGGER.warning(f"Failed to cache books page: {e}")

    async def invalidate_books_cache(self) -> None:
        """Invalidate all books cache."""
        if not self._redis:
            return
            
        try:
            keys = await self._redis.keys("books:page:*")
            if keys:
                await self._redis.delete(*keys)
                _LOGGER.debug(f"Invalidated {len(keys)} books cache entries")
                
        except Exception as e:
            _LOGGER.warning(f"Failed to invalidate books cache: {e}")

    async def get_authors_page(self, page: int, size: int) -> PaginatedResult[AuthorEntity] | None:
        """Get cached authors page."""
        if not self._redis:
            return None
            
        try:
            key = f"authors:page:{page}:size:{size}"
            cached_data = await self._redis.get(key)
            if not cached_data:
                return None
                
            data = json.loads(cached_data)
            authors = [self._dict_to_author_entity(author_dict) for author_dict in data["data"]]
            meta = PaginationMeta(**data["meta"])
            return PaginatedResult(data=authors, meta=meta)
            
        except Exception as e:
            _LOGGER.warning(f"Failed to get authors from cache: {e}")
            return None

    async def set_authors_page(self, page: int, size: int, result: PaginatedResult[AuthorEntity]) -> None:
        """Cache authors page."""
        if not self._redis:
            return
            
        try:
            key = f"authors:page:{page}:size:{size}"
            # Support either a PaginatedResult or an already-serialized dict
            if isinstance(result, dict):
                data = result
            else:
                data = {
                    "data": [self._author_entity_to_dict(author) for author in result.data],
                    "meta": {
                        "total": result.meta.total,
                        "page": result.meta.page,
                        "size": result.meta.size,
                        "count": result.meta.count,
                    }
                }
            await self._redis.setex(key, self.ttl, json.dumps(data))
            _LOGGER.debug(f"Cached authors page {page} with size {size}")
            
        except Exception as e:
            _LOGGER.warning(f"Failed to cache authors page: {e}")

    async def invalidate_authors_cache(self) -> None:
        """Invalidate all authors cache."""
        if not self._redis:
            return
            
        try:
            keys = await self._redis.keys("authors:page:*")
            if keys:
                await self._redis.delete(*keys)
                _LOGGER.debug(f"Invalidated {len(keys)} authors cache entries")
                
        except Exception as e:
            _LOGGER.warning(f"Failed to invalidate authors cache: {e}")

    # Search-aware helpers used by the service layer when a search query is provided
    async def get_authors_page_search(self, page: int, size: int, search: str) -> PaginatedResult[AuthorEntity] | None:  # pragma: no cover
        """Get cached authors page for a search query."""
        # pragma: no cover - optional search-aware cache helpers (integration only)
        if not self._redis:
            return None

        try:
            key = f"authors:search:{search}:page:{page}:size:{size}"
            cached_data = await self._redis.get(key)
            if not cached_data:
                return None
            data = json.loads(cached_data)
            authors = [self._dict_to_author_entity(author_dict) for author_dict in data["data"]]
            meta = PaginationMeta(**data["meta"])
            return PaginatedResult(data=authors, meta=meta)
        except Exception as e:
            _LOGGER.warning(f"Failed to get authors (search) from cache: {e}")
            return None

    async def set_authors_page_search(self, page: int, size: int, search: str, result) -> None:  # pragma: no cover
        """Cache authors page for a search query."""
        # pragma: no cover - optional search-aware cache helpers (integration only)
        if not self._redis:
            return

        try:
            key = f"authors:search:{search}:page:{page}:size:{size}"
            if isinstance(result, dict):
                data = result
            else:
                data = {
                    "data": [self._author_entity_to_dict(author) for author in result.data],
                    "meta": {
                        "total": result.meta.total,
                        "page": result.meta.page,
                        "size": result.meta.size,
                        "count": result.meta.count,
                    }
                }
            await self._redis.setex(key, self.ttl, json.dumps(data))
            _LOGGER.debug(f"Cached authors (search) page {page} size {size} for '{search}'")
        except Exception as e:
            _LOGGER.warning(f"Failed to cache authors (search) page: {e}")

    def _book_entity_to_dict(self, book: BookEntity) -> dict[str, Any]:
        """Convert BookEntity to serializable dictionary."""
        return {
            "id": book.id,
            "title": book.title,
            "authors": book.authors,
            "authors_details": book.authors_details,
            "authors_number": book.authors_number,
        }

    def _dict_to_book_entity(self, data: dict[str, Any]) -> BookEntity:
        """Convert dictionary to BookEntity."""
        return BookEntity(
            id=data["id"],
            title=data["title"],
            authors=data["authors"],
            authors_details=data["authors_details"],
            authors_number=data["authors_number"],
        )

    def _author_entity_to_dict(self, author: AuthorEntity) -> dict[str, Any]:
        """Convert AuthorEntity to serializable dictionary."""
        return {
            "id": author.id,
            "first_name": author.first_name,
            "last_name": author.last_name,
            "birth_date": author.birth_date.isoformat() if author.birth_date else None,
            "death_date": author.death_date.isoformat() if author.death_date else None,
            "nationality": author.nationality,
            "bio": author.bio,
            "photo_url": author.photo_url,
            "created_at": author.created_at.isoformat() if author.created_at else None,
            "updated_at": author.updated_at.isoformat() if author.updated_at else None,
        }

    def _dict_to_author_entity(self, data: dict[str, Any]) -> AuthorEntity:
        """Convert dictionary to AuthorEntity."""
        from datetime import datetime, date
        
        return AuthorEntity(
            id=data["id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            birth_date=date.fromisoformat(data["birth_date"]) if data["birth_date"] else None,
            death_date=date.fromisoformat(data["death_date"]) if data["death_date"] else None,
            nationality=data["nationality"],
            bio=data["bio"],
            photo_url=data["photo_url"],
            created_at=datetime.fromisoformat(data["created_at"]) if data["created_at"] else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data["updated_at"] else None,
        )
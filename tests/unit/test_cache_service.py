"""
Comprehensive tests for Redis cache service.
Tests all cache operations with mock Redis.
"""
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cache_service import RedisCacheService
from app.domain.entities import AuthorEntity, BookEntity
from app.domain.value_objects import PaginatedResult, PaginationMeta


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock()
    mock.delete = AsyncMock()
    mock.keys = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def cache_service(mock_redis):
    """Create a cache service with mocked Redis."""
    with patch('redis.asyncio.from_url', return_value=mock_redis):
        service = RedisCacheService(redis_url="redis://localhost:6379", ttl=3600)
        service._redis = mock_redis  # Set directly to avoid async connect
        return service


class TestRedisCacheServiceConnection:
    """Tests for cache service connection."""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_redis):
        """Test successful Redis connection."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            service = RedisCacheService(redis_url="redis://localhost:6379")
            await service.connect()
            
            assert service._redis is not None
            mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test Redis connection failure."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            service = RedisCacheService(redis_url="redis://localhost:6379")
            
            with pytest.raises(Exception, match="Connection failed"):
                await service.connect()
            
            assert service._redis is None

    @pytest.mark.asyncio
    async def test_connect_only_once(self, mock_redis):
        """Test that connect doesn't create multiple connections."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            service = RedisCacheService(redis_url="redis://localhost:6379")
            await service.connect()
            await service.connect()  # Second call
            
            # from_url should be called only once
            mock_redis.ping.assert_awaited_once()


class TestRedisCacheServiceBooks:
    """Tests for books cache operations."""

    @pytest.mark.asyncio
    async def test_get_books_page_not_connected(self):
        """Test getting books page when not connected."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        result = await service.get_books_page(1, 10)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_books_page_cache_miss(self, cache_service, mock_redis):
        """Test getting books page with cache miss."""
        mock_redis.get.return_value = None
        
        result = await cache_service.get_books_page(1, 10)
        
        assert result is None
        mock_redis.get.assert_awaited_once_with("books:page:1:size:10")

    @pytest.mark.asyncio
    async def test_get_books_page_cache_hit(self, cache_service, mock_redis):
        """Test getting books page with cache hit."""
        import json
        
        cached_data = {
            "data": [
                {
                    "id": 1,
                    "title": "Book 1",
                    "authors": [1],
                    "authors_details": [],
                    "authors_number": 1,
                }
            ],
            "meta": {
                "total": 10,
                "page": 1,
                "size": 10,
                "count": 1,
            }
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = await cache_service.get_books_page(1, 10)
        
        assert result is not None
        assert len(result.data) == 1
        assert result.data[0].id == 1
        assert result.data[0].title == "Book 1"
        assert result.meta.total == 10
        assert result.meta.page == 1

    @pytest.mark.asyncio
    async def test_get_books_page_json_error(self, cache_service, mock_redis):
        """Test getting books page with JSON decode error."""
        mock_redis.get.return_value = "invalid json"
        
        result = await cache_service.get_books_page(1, 10)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_set_books_page_not_connected(self):
        """Test setting books page when not connected."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        
        books = [BookEntity(id=1, title="Test", authors=[1])]
        meta = PaginationMeta(total=1, page=1, size=10, count=1)
        result = PaginatedResult(data=books, meta=meta)
        
        # Should not raise error
        await service.set_books_page(1, 10, result)

    @pytest.mark.asyncio
    async def test_set_books_page_success(self, cache_service, mock_redis):
        """Test setting books page successfully."""
        books = [
            BookEntity(
                id=1,
                title="Test Book",
                authors=[1, 2],
                authors_details=[{"id": 1, "name": "Author 1"}],
                authors_number=2,
            )
        ]
        meta = PaginationMeta(total=10, page=1, size=10, count=1)
        result = PaginatedResult(data=books, meta=meta)
        
        await cache_service.set_books_page(1, 10, result)
        
        mock_redis.setex.assert_awaited_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "books:page:1:size:10"
        assert call_args[0][1] == 3600  # TTL

    @pytest.mark.asyncio
    async def test_set_books_page_redis_error(self, cache_service, mock_redis):
        """Test setting books page with Redis error."""
        mock_redis.setex.side_effect = Exception("Redis error")
        
        books = [BookEntity(id=1, title="Test", authors=[1])]
        meta = PaginationMeta(total=1, page=1, size=10, count=1)
        result = PaginatedResult(data=books, meta=meta)
        
        # Should not raise error (logged as warning)
        await cache_service.set_books_page(1, 10, result)

    @pytest.mark.asyncio
    async def test_invalidate_books_cache_not_connected(self):
        """Test invalidating books cache when not connected."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        
        # Should not raise error
        await service.invalidate_books_cache()

    @pytest.mark.asyncio
    async def test_invalidate_books_cache_no_keys(self, cache_service, mock_redis):
        """Test invalidating books cache with no keys."""
        mock_redis.keys.return_value = []
        
        await cache_service.invalidate_books_cache()
        
        mock_redis.keys.assert_awaited_once_with("books:page:*")
        mock_redis.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalidate_books_cache_with_keys(self, cache_service, mock_redis):
        """Test invalidating books cache with multiple keys."""
        mock_redis.keys.return_value = [
            "books:page:1:size:10",
            "books:page:2:size:10",
            "books:page:3:size:10",
        ]
        
        await cache_service.invalidate_books_cache()
        
        mock_redis.delete.assert_awaited_once()
        call_args = mock_redis.delete.call_args[0]
        assert len(call_args) == 3

    @pytest.mark.asyncio
    async def test_invalidate_books_cache_redis_error(self, cache_service, mock_redis):
        """Test invalidating books cache with Redis error."""
        mock_redis.keys.side_effect = Exception("Redis error")
        
        # Should not raise error (logged as warning)
        await cache_service.invalidate_books_cache()


class TestRedisCacheServiceAuthors:
    """Tests for authors cache operations."""

    @pytest.mark.asyncio
    async def test_get_authors_page_not_connected(self):
        """Test getting authors page when not connected."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        result = await service.get_authors_page(1, 10)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_authors_page_cache_miss(self, cache_service, mock_redis):
        """Test getting authors page with cache miss."""
        mock_redis.get.return_value = None
        
        result = await cache_service.get_authors_page(1, 10)
        
        assert result is None
        mock_redis.get.assert_awaited_with("authors:page:1:size:10")

    @pytest.mark.asyncio
    async def test_get_authors_page_cache_hit(self, cache_service, mock_redis):
        """Test getting authors page with cache hit."""
        import json
        
        cached_data = {
            "data": [
                {
                    "id": 1,
                    "first_name": "John",
                    "last_name": "Doe",
                    "birth_date": "1950-01-01",
                    "death_date": None,
                    "nationality": "USA",
                    "bio": "Test bio",
                    "photo_url": "http://example.com/photo.jpg",
                    "created_at": "2023-01-01T12:00:00",
                    "updated_at": "2023-01-02T12:00:00",
                }
            ],
            "meta": {
                "total": 10,
                "page": 1,
                "size": 10,
                "count": 1,
            }
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = await cache_service.get_authors_page(1, 10)
        
        assert result is not None
        assert len(result.data) == 1
        assert result.data[0].id == 1
        assert result.data[0].first_name == "John"
        assert result.data[0].birth_date == date(1950, 1, 1)
        assert result.meta.total == 10

    @pytest.mark.asyncio
    async def test_get_authors_page_with_null_dates(self, cache_service, mock_redis):
        """Test getting authors page with null dates."""
        import json
        
        cached_data = {
            "data": [
                {
                    "id": 1,
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "birth_date": None,
                    "death_date": None,
                    "nationality": None,
                    "bio": None,
                    "photo_url": None,
                    "created_at": None,
                    "updated_at": None,
                }
            ],
            "meta": {"total": 1, "page": 1, "size": 10, "count": 1}
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = await cache_service.get_authors_page(1, 10)
        
        assert result is not None
        assert result.data[0].birth_date is None
        assert result.data[0].death_date is None
        assert result.data[0].created_at is None

    @pytest.mark.asyncio
    async def test_set_authors_page_not_connected(self):
        """Test setting authors page when not connected."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        
        authors = [AuthorEntity(id=1, first_name="John", last_name="Doe")]
        meta = PaginationMeta(total=1, page=1, size=10, count=1)
        result = PaginatedResult(data=authors, meta=meta)
        
        # Should not raise error
        await service.set_authors_page(1, 10, result)

    @pytest.mark.asyncio
    async def test_set_authors_page_success(self, cache_service, mock_redis):
        """Test setting authors page successfully."""
        authors = [
            AuthorEntity(
                id=1,
                first_name="John",
                last_name="Doe",
                birth_date=date(1950, 1, 1),
                death_date=date(2020, 12, 31),
                nationality="USA",
                bio="Test bio",
                photo_url="http://example.com/photo.jpg",
                created_at=datetime(2023, 1, 1, 12, 0, 0),
                updated_at=datetime(2023, 1, 2, 12, 0, 0),
            )
        ]
        meta = PaginationMeta(total=10, page=2, size=5, count=1)
        result = PaginatedResult(data=authors, meta=meta)
        
        await cache_service.set_authors_page(2, 5, result)
        
        mock_redis.setex.assert_awaited_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "authors:page:2:size:5"
        assert call_args[0][1] == 3600  # TTL

    @pytest.mark.asyncio
    async def test_invalidate_authors_cache_with_keys(self, cache_service, mock_redis):
        """Test invalidating authors cache with multiple keys."""
        mock_redis.keys.return_value = [
            "authors:page:1:size:10",
            "authors:page:2:size:10",
        ]
        
        await cache_service.invalidate_authors_cache()
        
        mock_redis.delete.assert_awaited_once()
        call_args = mock_redis.delete.call_args[0]
        assert len(call_args) == 2


class TestCacheServiceHelpers:
    """Tests for helper methods."""

    def test_book_entity_to_dict(self):
        """Test converting BookEntity to dictionary."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        
        book = BookEntity(
            id=1,
            title="Test Book",
            authors=[1, 2],
            authors_details=[{"id": 1, "name": "Author 1"}],
            authors_number=2,
        )
        
        result = service._book_entity_to_dict(book)
        
        assert result["id"] == 1
        assert result["title"] == "Test Book"
        assert result["authors"] == [1, 2]
        assert result["authors_number"] == 2

    def test_dict_to_book_entity(self):
        """Test converting dictionary to BookEntity."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        
        data = {
            "id": 1,
            "title": "Test Book",
            "authors": [1, 2],
            "authors_details": [{"id": 1, "name": "Author 1"}],
            "authors_number": 2,
        }
        
        result = service._dict_to_book_entity(data)
        
        assert result.id == 1
        assert result.title == "Test Book"
        assert result.authors == [1, 2]

    def test_author_entity_to_dict_with_all_fields(self):
        """Test converting AuthorEntity to dictionary with all fields."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        
        author = AuthorEntity(
            id=1,
            first_name="John",
            last_name="Doe",
            birth_date=date(1950, 1, 1),
            death_date=date(2020, 12, 31),
            nationality="USA",
            bio="Test bio",
            photo_url="http://example.com/photo.jpg",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 2, 12, 0, 0),
        )
        
        result = service._author_entity_to_dict(author)
        
        assert result["id"] == 1
        assert result["first_name"] == "John"
        assert result["birth_date"] == "1950-01-01"
        assert result["death_date"] == "2020-12-31"
        assert result["created_at"] == "2023-01-01T12:00:00"

    def test_author_entity_to_dict_with_null_fields(self):
        """Test converting AuthorEntity to dictionary with null fields."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        
        author = AuthorEntity(
            id=1,
            first_name="Jane",
            last_name="Smith",
            birth_date=None,
            death_date=None,
            nationality=None,
            bio=None,
            photo_url=None,
            created_at=None,
            updated_at=None,
        )
        
        result = service._author_entity_to_dict(author)
        
        assert result["birth_date"] is None
        assert result["death_date"] is None
        assert result["created_at"] is None
        assert result["updated_at"] is None

    def test_dict_to_author_entity(self):
        """Test converting dictionary to AuthorEntity."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        
        data = {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "birth_date": "1950-01-01",
            "death_date": "2020-12-31",
            "nationality": "USA",
            "bio": "Test bio",
            "photo_url": "http://example.com/photo.jpg",
            "created_at": "2023-01-01T12:00:00",
            "updated_at": "2023-01-02T12:00:00",
        }
        
        result = service._dict_to_author_entity(data)
        
        assert result.id == 1
        assert result.first_name == "John"
        assert result.birth_date == date(1950, 1, 1)
        assert result.created_at == datetime(2023, 1, 1, 12, 0, 0)


# --- ERROR HANDLING TESTS ---


class TestRedisCacheServiceErrorHandling:
    """Test error handling in Redis cache service."""

    @pytest.mark.asyncio
    async def test_get_authors_page_redis_error(self):
        """Test get_authors_page handles Redis errors gracefully."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        service._redis = mock_redis
        
        # Make Redis.get() raise an exception
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        result = await service.get_authors_page(1, 10)
        
        # Should return None instead of crashing
        assert result is None

    @pytest.mark.asyncio
    async def test_set_authors_page_redis_error(self):
        """Test set_authors_page handles Redis errors gracefully."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        service._redis = mock_redis
        
        # Make Redis.setex() raise an exception
        mock_redis.setex.side_effect = Exception("Redis connection error")
        
        result = PaginatedResult(
            data=[],
            meta=PaginationMeta(total=0, page=1, size=10, count=0),
        )
        
        # Should not crash
        await service.set_authors_page(1, 10, result)
        # No assertion needed - just verifying it doesn't crash

    @pytest.mark.asyncio
    async def test_invalidate_authors_cache_redis_error(self):
        """Test invalidate_authors_cache handles Redis errors gracefully."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        service._redis = mock_redis
        
        # Make Redis.keys() raise an exception
        mock_redis.keys.side_effect = Exception("Redis connection error")
        
        # Should not crash
        await service.invalidate_authors_cache()
        # No assertion needed - just verifying it doesn't crash

    @pytest.mark.asyncio
    async def test_get_books_page_redis_error(self):
        """Test get_books_page handles Redis errors gracefully."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        service._redis = mock_redis
        
        # Make Redis.get() raise an exception
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        result = await service.get_books_page(1, 10)
        
        # Should return None instead of crashing
        assert result is None

    @pytest.mark.asyncio
    async def test_set_books_page_redis_error(self):
        """Test set_books_page handles Redis errors gracefully."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        service._redis = mock_redis
        
        # Make Redis.setex() raise an exception
        mock_redis.setex.side_effect = Exception("Redis connection error")
        
        result = PaginatedResult(
            data=[],
            meta=PaginationMeta(total=0, page=1, size=10, count=0),
        )
        
        # Should not crash
        await service.set_books_page(1, 10, result)
        # No assertion needed - just verifying it doesn't crash

    @pytest.mark.asyncio
    async def test_invalidate_books_cache_redis_error(self):
        """Test invalidate_books_cache handles Redis errors gracefully."""
        service = RedisCacheService(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        service._redis = mock_redis
        
        # Make Redis.keys() raise an exception
        mock_redis.keys.side_effect = Exception("Redis connection error")
        
        # Should not crash
        await service.invalidate_books_cache()
        # No assertion needed - just verifying it doesn't crash

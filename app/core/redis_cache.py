import json

import redis.asyncio as redis


class RedisCache:
    def __init__(self, url: str):
        self.url = url
        self.redis = None

    async def connect(self):
        try:
            self.redis = redis.from_url(self.url)
        except Exception:  # pragma: no cover - environment dependent
            # Fallback to no-op mode if Redis is unavailable
            self.redis = None

    async def get_books_page(self, page: int, size: int):
        key = f"books:page:{page}:size:{size}"
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
        except Exception:  # pragma: no cover - rare at runtime
            return None
        if data:
            return json.loads(data)
        return None

    async def set_books_page(self, page: int, size: int, value, expire: int = 60):
        key = f"books:page:{page}:size:{size}"
        if not self.redis:
            return
        try:
            await self.redis.set(key, json.dumps(value), ex=expire)
        except Exception:  # pragma: no cover - rare at runtime
            return

    async def get_authors_page(self, page: int, size: int):
        # Use a distinct namespace for authors
        key = f"authors:page:{page}:size:{size}"
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
        except Exception:  # pragma: no cover - rare at runtime
            return None
        if data:
            return json.loads(data)
        return None

    async def set_authors_page(self, page: int, size: int, value, expire: int = 60):
        key = f"authors:page:{page}:size:{size}"
        if not self.redis:
            return
        try:
            await self.redis.set(key, json.dumps(value), ex=expire)
        except Exception:  # pragma: no cover - rare at runtime
            return

    async def get_authors_page_search(self, page: int, size: int, search: str):
        key = f"authors:page:{page}:size:{size}:search:{search}"
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
        except Exception:  # pragma: no cover
            return None
        if data:
            return json.loads(data)
        return None

    async def set_authors_page_search(
        self, page: int, size: int, search: str, value, expire: int = 60
    ):
        key = f"authors:page:{page}:size:{size}:search:{search}"
        if not self.redis:
            return
        try:
            await self.redis.set(key, json.dumps(value), ex=expire)
        except Exception:  # pragma: no cover
            return

    async def close(self):
        if self.redis:
            try:
                await self.redis.close()
            except Exception:  # pragma: no cover - close rarely fails
                return

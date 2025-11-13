from __future__ import annotations

import json
from typing import Any


class FakeRedis:
    """Flexible fake redis client used in tests.

    Supports three modes used across tests:
    - ping-only (fail_ping)
    - get/set behavior with optional failures (fail_get, fail_set)
    """

    def __init__(
        self, *, fail_get: bool = False, fail_set: bool = False, fail_ping: bool = False
    ):
        self.store: dict[str, Any] = {}
        self.fail_get = fail_get
        self.fail_set = fail_set
        self._fail_ping = fail_ping

    async def get(self, key: str) -> bytes | None:
        if self.fail_get:
            raise RuntimeError("get failed")
        val = self.store.get(key)
        return json.dumps(val).encode() if val is not None else None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if self.fail_set:
            raise RuntimeError("set failed")
        # value is a JSON string; tests often encode via json.dumps
        self.store[key] = json.loads(value)

    async def ping(self) -> None:
        if self._fail_ping:
            raise RuntimeError("ping failed")

    async def close(self) -> None:
        return None

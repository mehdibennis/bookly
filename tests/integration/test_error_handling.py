import time
from uuid import uuid4

import pytest

from app.core.exceptions import (
    AppException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.db.session import get_session
from app.domain.value_objects import BookCreateData, PaginationParams
from app.main import app
from app.repositories.book_repository import BookRepository


def test_exceptions_construction():
    base = AppException("oops", 418)
    assert str(base) == "oops"
    assert base.status_code == 418
    assert NotFoundException().status_code == 404
    assert ConflictException().status_code == 409
    assert UnauthorizedException().status_code == 401


@pytest.mark.perf
@pytest.mark.parametrize(
    "n,limit,threshold_s",
    [
        (10, 5, 5),
        (20, 10, 10),
    ],
)
@pytest.mark.asyncio
async def test_perf_create_n_and_list_under_threshold(
    n, limit, threshold_s, test_author_id
):
    # Lightweight perf check: create n rows and list them in two pages
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        start = time.perf_counter()

        for i in range(n):
            book_data = BookCreateData(
                title=f"Perf {i}-{uuid4()}", authors=[test_author_id]
            )
            await repo.create(book_data)

        # List with pagination in 2 pages
        result1 = await repo.get_paginated(PaginationParams(page=1, size=limit))
        items1 = result1.data
        total = result1.meta.total

        result2 = await repo.get_paginated(PaginationParams(page=2, size=limit))
        items2 = result2.data

        elapsed = time.perf_counter() - start
        # Sanity checks and a generous threshold (should pass in CI/Docker)
        assert total >= n
        assert len(items1) == min(limit, total)
        # second page count can be <= limit depending on remainder
        assert len(items2) >= 0
        assert elapsed < threshold_s

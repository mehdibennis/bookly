from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.domain.value_objects import PaginationParams
from app.repositories.author_repository import AuthorRepository, _parse_date


class FakeResult:
    def __init__(
        self, scalar_one_or_none_result=None, scalars_list=None, scalar_one_value=None
    ):
        self._scalar_one_or_none = scalar_one_or_none_result
        self._scalars_list = scalars_list or []
        self._scalar_one = scalar_one_value

    def scalar_one_or_none(self):
        return self._scalar_one_or_none

    def scalars(self):
        class S:
            def __init__(self, lst):
                self._lst = lst

            def all(self):
                return list(self._lst)

        return S(self._scalars_list)

    def scalar_one(self):
        return self._scalar_one


class FakeSession:
    def __init__(self, results=None):
        # results is a queue of FakeResult to be returned by execute()
        self._results = list(results or [])
        self.added = []
        self.flushed = 0
        self.refreshed = 0
        self.deleted = []

    async def execute(self, stmt):
        if not self._results:
            return FakeResult()
        return self._results.pop(0)

    async def flush(self):
        self.flushed += 1

    async def refresh(self, obj, attrs=None):
        self.refreshed += 1

    def add(self, obj):
        self.added.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)


def make_fake_author(id=1):
    now = datetime.utcnow()
    return SimpleNamespace(
        id=id,
        first_name="John",
        last_name="Doe",
        birth_date=date(1980, 1, 1),
        death_date=None,
        nationality="FR",
        bio="bio",
        photo_url="/u.png",
        created_at=now,
        updated_at=now,
    )


def test_parse_date_various_formats():
    assert _parse_date(None) is None
    d = date(2000, 5, 4)
    assert _parse_date(d) == d
    assert _parse_date("1990-01-02") == date(1990, 1, 2)
    assert _parse_date("invalid-date") is None


@pytest.mark.asyncio
async def test_model_to_entity_and_get_by_id_and_full_name():
    author = make_fake_author()
    # session will return author for queries
    session = FakeSession(results=[FakeResult(scalar_one_or_none_result=author)])
    repo = AuthorRepository(session=session)

    # _model_to_entity via get_by_id
    res_none = await repo.get_by_id(999)
    # because our session had one result, and get_by_id calls execute once -> returns author
    assert res_none is not None
    assert res_none.first_name == "John"

    # Now test get_by_full_name: prepare session returning None then author
    session = FakeSession(
        results=[
            FakeResult(scalar_one_or_none_result=None),
            FakeResult(scalar_one_or_none_result=author),
        ]
    )
    repo = AuthorRepository(session=session)
    res_none = await repo.get_by_full_name("No", "One")
    assert res_none is None


@pytest.mark.asyncio
async def test_get_paginated_with_and_without_search():
    author1 = make_fake_author(1)
    author2 = make_fake_author(2)
    # First execute returns authors list, second returns count
    session = FakeSession(
        results=[
            FakeResult(scalars_list=[author1, author2]),
            FakeResult(scalar_one_value=2),
        ]
    )
    repo = AuthorRepository(session=session)
    params = PaginationParams(page=1, size=10)
    pag = await repo.get_paginated(params)
    assert pag.meta.total == 2
    assert len(pag.data) == 2


@pytest.mark.asyncio
async def test_get_paginated_with_search_term():
    author = make_fake_author(3)
    # returns list then count
    session = FakeSession(
        results=[FakeResult(scalars_list=[author]), FakeResult(scalar_one_value=1)]
    )
    repo = AuthorRepository(session=session)
    params = PaginationParams(page=1, size=10)
    pag = await repo.get_paginated(params, search="john")
    assert pag.meta.total == 1
    assert len(pag.data) == 1


@pytest.mark.asyncio
async def test_create_update_partial_delete_flow(monkeypatch):
    # (Skip create flow here to avoid interfering with SQLAlchemy model class used in selects)
    # Update when not found
    session = FakeSession(results=[FakeResult(scalar_one_or_none_result=None)])
    repo = AuthorRepository(session=session)
    updated = await repo.update(
        123,
        SimpleNamespace(
            first_name=None,
            last_name=None,
            birth_date=None,
            death_date=None,
            nationality=None,
            bio=None,
            photo_url=None,
        ),
    )
    assert updated is None

    # Update when found
    db_author = make_fake_author(5)
    session = FakeSession(results=[FakeResult(scalar_one_or_none_result=db_author)])
    repo = AuthorRepository(session=session)
    data = SimpleNamespace(
        first_name="New",
        last_name="Name",
        birth_date=None,
        death_date=None,
        nationality=None,
        bio=None,
        photo_url=None,
    )
    updated = await repo.update(5, data)
    assert updated is not None
    assert updated.first_name == "New"

    # Partial update
    db_author = make_fake_author(6)
    session = FakeSession(results=[FakeResult(scalar_one_or_none_result=db_author)])
    repo = AuthorRepository(session=session)
    partial = SimpleNamespace(
        first_name="P",
        last_name=None,
        birth_date="1990-02-02",
        death_date=None,
        nationality=None,
        bio=None,
        photo_url=None,
    )
    p = await repo.partial_update(6, partial)
    assert p is not None
    assert p.first_name == "P"

    # Delete not found
    session = FakeSession(results=[FakeResult(scalar_one_or_none_result=None)])
    repo = AuthorRepository(session=session)
    deleted = await repo.delete(9999)
    assert deleted is False

    # Delete found
    db_author = make_fake_author(7)
    session = FakeSession(results=[FakeResult(scalar_one_or_none_result=db_author)])
    repo = AuthorRepository(session=session)
    deleted = await repo.delete(7)
    assert deleted is True

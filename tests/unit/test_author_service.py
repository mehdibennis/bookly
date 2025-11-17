from typing import cast

import pytest

from app.domain.entities import AuthorEntity
from app.domain.exceptions import ConflictException, NotFoundException
from app.domain.unit_of_work import IUnitOfWork
from app.domain.value_objects import AuthorCreateData, AuthorUpdateData
from app.services.author_service import AuthorService


class FakeUoW:
    def __init__(self):
        self.entered = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeRepo:
    def __init__(self, by_id=None, by_full_name=None):
        self._by_id = by_id
        self._by_full_name = by_full_name

    async def get_by_id(self, id):
        return self._by_id

    async def get_by_full_name(self, first, last):
        return self._by_full_name

    async def get_paginated(self, pagination, search=None):
        return None

    async def create(self, data):
        return AuthorEntity(id=1, first_name=data.first_name, last_name=data.last_name)

    async def partial_update(self, id, data):
        return AuthorEntity(
            id=id, first_name=data.first_name or "x", last_name=data.last_name or "y"
        )

    async def delete(self, id):
        return True


def make_service(repo, uow=None):
    if uow is None:
        uow = cast(IUnitOfWork, FakeUoW())
    return AuthorService(repo=repo, uow=uow)


@pytest.mark.asyncio
async def test_list_authors_validation():
    svc = make_service(repo=FakeRepo())
    with pytest.raises(ValueError):
        await svc.list_authors_by_page(0, 10)
    with pytest.raises(ValueError):
        await svc.list_authors_by_page(1, 0)


@pytest.mark.asyncio
async def test_get_author_not_found_and_invalid():
    svc = make_service(repo=FakeRepo(by_id=None))
    with pytest.raises(ValueError):
        await svc.get_author(0)
    with pytest.raises(NotFoundException):
        await svc.get_author(999)


@pytest.mark.asyncio
async def test_create_author_conflict():
    existing = AuthorEntity(id=2, first_name="A", last_name="B")
    svc = make_service(repo=FakeRepo(by_full_name=existing))
    with pytest.raises(ConflictException):
        await svc.create_author(
            AuthorCreateData(
                first_name="A",
                last_name="B",
                nationality=None,
                birth_date=None,
                death_date=None,
                bio=None,
                photo_url=None,
            )
        )


@pytest.mark.asyncio
async def test_partial_update_returns_existing_if_no_fields():
    existing = AuthorEntity(id=3, first_name="A", last_name="B")
    svc = make_service(repo=FakeRepo(by_id=existing))
    res = await svc.partial_update_author(
        3,
        AuthorUpdateData(
            first_name=None,
            last_name=None,
            nationality=None,
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        ),
    )
    assert res is existing


@pytest.mark.asyncio
async def test_delete_author_not_found():
    svc = make_service(repo=FakeRepo(by_id=None))
    with pytest.raises(NotFoundException):
        await svc.delete_author(123)

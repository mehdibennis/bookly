import pytest

from app.domain.entities import StoreEntity
from app.domain.exceptions import ConflictException, NotFoundException
from app.domain.value_objects import (
    PaginatedResult,
    PaginationMeta,
    StoreCreateData,
    StoreUpdateData,
)
from app.services.store_service import StoreService


class FakeUoW:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeStoreRepo:
    def __init__(self):
        self.stores = {}
        self.inventory = {}  # (store_id, book_id) -> quantity
        self.next_id = 1

    async def list(self, pagination):
        items = list(self.stores.values())
        # Mock pagination logic roughly
        start = (pagination.page - 1) * pagination.size
        end = start + pagination.size
        page_items = items[start:end]

        return PaginatedResult(
            data=page_items,
            meta=PaginationMeta(
                total=len(items),
                page=pagination.page,
                size=pagination.size,
                count=len(page_items),
            ),
        )

    async def get_by_id(self, store_id):
        return self.stores.get(store_id)

    async def get_by_name(self, name):
        for s in self.stores.values():
            if s.name == name:
                return s
        return None

    async def create(self, data):
        store = StoreEntity(id=self.next_id, name=data.name, location=data.location)
        self.stores[self.next_id] = store
        self.next_id += 1
        return store

    async def update(self, store_id, data):
        if store_id not in self.stores:
            return None
        store = self.stores[store_id]
        if data.name is not None:
            store.name = data.name
        if data.location is not None:
            store.location = data.location
        return store

    async def delete(self, store_id):
        if store_id in self.stores:
            del self.stores[store_id]
            return True
        return False

    async def add_book_stock(self, store_id, book_id, quantity):
        key = (store_id, book_id)
        self.inventory[key] = self.inventory.get(key, 0) + quantity

    async def remove_book_stock(self, store_id, book_id, quantity):
        key = (store_id, book_id)
        current = self.inventory.get(key, 0)
        self.inventory[key] = max(0, current - quantity)

    async def get_stock(self, store_id, book_id):
        return self.inventory.get((store_id, book_id), 0)


@pytest.fixture
def repo():
    return FakeStoreRepo()


@pytest.fixture
def service(repo):
    return StoreService(repo, FakeUoW())


@pytest.mark.asyncio
async def test_create_store(service):
    data = StoreCreateData(name="My Store", location="Paris")
    store = await service.create_store(data)
    assert store.id == 1
    assert store.name == "My Store"
    assert store.location == "Paris"


@pytest.mark.asyncio
async def test_create_store_conflict(service, repo):
    await repo.create(StoreCreateData(name="Existing Store"))

    with pytest.raises(ConflictException):
        await service.create_store(StoreCreateData(name="Existing Store"))


@pytest.mark.asyncio
async def test_get_store(service, repo):
    created = await repo.create(StoreCreateData(name="My Store"))
    fetched = await service.get_store(created.id)
    assert fetched == created


@pytest.mark.asyncio
async def test_get_store_not_found(service):
    with pytest.raises(NotFoundException):
        await service.get_store(999)


@pytest.mark.asyncio
async def test_update_store(service, repo):
    created = await repo.create(StoreCreateData(name="Old Name", location="Old Loc"))

    updated = await service.update_store(created.id, StoreUpdateData(name="New Name"))
    assert updated.name == "New Name"
    assert updated.location == "Old Loc"


@pytest.mark.asyncio
async def test_update_store_conflict(service, repo):
    await repo.create(StoreCreateData(name="Store A"))
    store_b = await repo.create(StoreCreateData(name="Store B"))

    with pytest.raises(ConflictException):
        await service.update_store(store_b.id, StoreUpdateData(name="Store A"))


@pytest.mark.asyncio
async def test_delete_store(service, repo):
    created = await repo.create(StoreCreateData(name="To Delete"))
    await service.delete_store(created.id)
    assert await repo.get_by_id(created.id) is None


@pytest.mark.asyncio
async def test_inventory_management(service, repo):
    store = await repo.create(StoreCreateData(name="Stock Store"))

    # Initial stock should be 0
    assert await service.get_stock(store.id, 1) == 0

    # Add stock
    await service.add_stock(store.id, 1, 10)
    assert await service.get_stock(store.id, 1) == 10

    # Add more
    await service.add_stock(store.id, 1, 5)
    assert await service.get_stock(store.id, 1) == 15

    # Remove stock
    await service.remove_stock(store.id, 1, 3)
    assert await service.get_stock(store.id, 1) == 12

    # Remove more than available (should floor at 0 based on fake repo logic)
    await service.remove_stock(store.id, 1, 100)
    assert await service.get_stock(store.id, 1) == 0

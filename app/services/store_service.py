from app.domain.entities import StoreEntity
from app.domain.exceptions import ConflictException, NotFoundException
from app.domain.repositories import IStoreRepository
from app.domain.unit_of_work import IUnitOfWork
from app.domain.value_objects import (
    PaginatedResult,
    PaginationParams,
    StoreCreateData,
    StoreUpdateData,
)


class StoreService:
    """
    Service layer for store-related business logic.
    """

    def __init__(self, repo: IStoreRepository, uow: IUnitOfWork):
        self.repo = repo
        self.uow = uow

    async def list_stores(
        self, page: int = 1, size: int = 10
    ) -> PaginatedResult[StoreEntity]:
        pagination = PaginationParams(page=page, size=size)
        return await self.repo.list(pagination)

    async def get_store(self, store_id: int) -> StoreEntity:
        if store_id <= 0:
            raise ValueError("Store ID must be a positive integer.")
        store = await self.repo.get_by_id(store_id)
        if not store:
            raise NotFoundException(f"Store with id={store_id} not found.")
        return store

    async def create_store(self, store_data: StoreCreateData) -> StoreEntity:
        # Normalize
        name = store_data.name.strip().title()

        # Check uniqueness
        existing = await self.repo.get_by_name(name)
        if existing:
            raise ConflictException(f"Store with name '{name}' already exists.")

        normalized_data = StoreCreateData(
            name=name,
            location=store_data.location.strip() if store_data.location else None,
        )

        async with self.uow:
            return await self.repo.create(normalized_data)

    async def update_store(
        self, store_id: int, store_data: StoreUpdateData
    ) -> StoreEntity:
        if store_id <= 0:
            raise ValueError("Store ID must be a positive integer.")

        existing = await self.repo.get_by_id(store_id)
        if not existing:
            raise NotFoundException(f"Store with id={store_id} not found.")

        normalized_name = None
        if store_data.name is not None:
            normalized_name = store_data.name.strip().title()
            # Check conflict
            conflict = await self.repo.get_by_name(normalized_name)
            if conflict and conflict.id != store_id:
                raise ConflictException(
                    f"Store with name '{normalized_name}' already exists."
                )

        normalized_data = StoreUpdateData(
            name=normalized_name,
            location=store_data.location.strip() if store_data.location else None,
        )

        async with self.uow:
            updated = await self.repo.update(store_id, normalized_data)
            assert updated is not None
            return updated

    async def delete_store(self, store_id: int) -> bool:
        if store_id <= 0:
            raise ValueError("Store ID must be a positive integer.")

        existing = await self.repo.get_by_id(store_id)
        if not existing:
            raise NotFoundException(f"Store with id={store_id} not found.")

        async with self.uow:
            return await self.repo.delete(store_id)

    async def add_stock(self, store_id: int, book_id: int, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        # Verify store exists
        await self.get_store(store_id)
        # Verify book exists? Ideally yes, but repo might handle FK constraint.
        # For clean arch, we might want to check existence via BookService or Repo,
        # but that introduces coupling.
        # We'll rely on DB constraints or assume valid book_id for now,
        # or inject BookRepository if needed.
        # Let's assume valid book_id for simplicity or catch integrity error.

        async with self.uow:
            await self.repo.add_book_stock(store_id, book_id, quantity)

    async def remove_stock(self, store_id: int, book_id: int, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        await self.get_store(store_id)

        async with self.uow:
            await self.repo.remove_book_stock(store_id, book_id, quantity)

    async def get_stock(self, store_id: int, book_id: int) -> int:
        await self.get_store(store_id)
        return await self.repo.get_stock(store_id, book_id)

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.store_model import Store, StoreInventory
from app.domain.entities import StoreEntity
from app.domain.repositories import IStoreRepository
from app.domain.value_objects import (
    PaginatedResult,
    PaginationMeta,
    PaginationParams,
    StoreCreateData,
    StoreUpdateData,
)


class StoreRepository(IStoreRepository):
    """SQLAlchemy implementation of the store repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, store: Store) -> StoreEntity:
        return StoreEntity(
            id=store.id,  # type: ignore[arg-type]
            name=store.name,  # type: ignore[arg-type]
            location=store.location,  # type: ignore[arg-type]
            created_at=store.created_at,  # type: ignore[arg-type]
            updated_at=store.updated_at,  # type: ignore[arg-type]
        )

    async def get_by_name(self, name: str) -> StoreEntity | None:
        stmt = select(Store).where(Store.name == name)
        result = await self.session.execute(stmt)
        store = result.scalar_one_or_none()
        return self._to_entity(store) if store else None

    async def get_by_id(self, store_id: int) -> StoreEntity | None:
        stmt = select(Store).where(Store.id == store_id)
        result = await self.session.execute(stmt)
        store = result.scalar_one_or_none()
        return self._to_entity(store) if store else None

    async def list(self, pagination: PaginationParams) -> PaginatedResult[StoreEntity]:
        # Count total
        count_stmt = select(func.count()).select_from(Store)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # Get page
        stmt = (
            select(Store)
            .order_by(Store.name)
            .offset(pagination.skip)
            .limit(pagination.limit)
        )
        result = await self.session.execute(stmt)
        stores = result.scalars().all()

        return PaginatedResult(
            data=[self._to_entity(store) for store in stores],
            meta=PaginationMeta(
                total=total,
                page=pagination.page,
                size=pagination.size,
                count=len(stores),
            ),
        )

    async def create(self, store_data: StoreCreateData) -> StoreEntity:
        store = Store(name=store_data.name, location=store_data.location)
        self.session.add(store)
        await self.session.flush()
        await self.session.refresh(store)
        return self._to_entity(store)

    async def update(
        self, store_id: int, store_data: StoreUpdateData
    ) -> StoreEntity | None:
        stmt = select(Store).where(Store.id == store_id)
        result = await self.session.execute(stmt)
        store = result.scalar_one_or_none()

        if not store:
            return None

        if store_data.name is not None:
            store.name = store_data.name  # type: ignore[assignment]
        if store_data.location is not None:
            store.location = store_data.location  # type: ignore[assignment]

        await self.session.flush()
        await self.session.refresh(store)
        return self._to_entity(store)

    async def delete(self, store_id: int) -> bool:
        stmt = select(Store).where(Store.id == store_id)
        result = await self.session.execute(stmt)
        store = result.scalar_one_or_none()

        if not store:
            return False

        await self.session.delete(store)
        return True

    async def add_book_stock(self, store_id: int, book_id: int, quantity: int) -> None:
        # Check if inventory exists
        stmt = select(StoreInventory).where(
            StoreInventory.store_id == store_id, StoreInventory.book_id == book_id
        )
        result = await self.session.execute(stmt)
        inventory = result.scalar_one_or_none()

        if inventory:
            inventory.quantity += quantity  # type: ignore[assignment]
        else:
            inventory = StoreInventory(
                store_id=store_id, book_id=book_id, quantity=quantity
            )
            self.session.add(inventory)

    async def remove_book_stock(
        self, store_id: int, book_id: int, quantity: int
    ) -> None:
        stmt = select(StoreInventory).where(
            StoreInventory.store_id == store_id, StoreInventory.book_id == book_id
        )
        result = await self.session.execute(stmt)
        inventory = result.scalar_one_or_none()

        if inventory:
            new_qty = max(0, int(inventory.quantity) - quantity)
            inventory.quantity = new_qty  # type: ignore[assignment]
            if inventory.quantity == 0:
                # Optional: remove row if 0? Or keep it? Keeping it is safer for history usually.
                # But let's say we keep it at 0.
                pass

    async def get_stock(self, store_id: int, book_id: int) -> int:
        stmt = select(StoreInventory.quantity).where(
            StoreInventory.store_id == store_id, StoreInventory.book_id == book_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() or 0

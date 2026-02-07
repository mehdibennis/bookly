from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_store_service
from app.api.mappers import PaginationMapper, StoreMapper
from app.schemas.pagination import PaginatedResponse
from app.schemas.store_schema import (
    Store,
    StoreCreate,
    StoreInventoryBase,
    StoreUpdate,
)
from app.services.store_service import StoreService

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get(
    "/",
    response_model=PaginatedResponse[Store],
    name="stores:list",
    summary="List stores",
)
async def list_stores(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    service: StoreService = Depends(get_store_service),
):
    result = await service.list_stores(page, size)
    return PaginationMapper.result_to_response(result, StoreMapper.entities_to_dtos)


@router.post(
    "/",
    response_model=Store,
    status_code=status.HTTP_201_CREATED,
    name="stores:create",
    summary="Create a new store",
)
async def create_store(
    store_data: StoreCreate,
    service: StoreService = Depends(get_store_service),
):
    domain_data = StoreMapper.to_domain_create(store_data)
    store = await service.create_store(domain_data)
    return StoreMapper.to_api(store)


@router.get(
    "/{store_id}",
    response_model=Store,
    name="stores:get",
    summary="Get a store by ID",
)
async def get_store(
    store_id: int,
    service: StoreService = Depends(get_store_service),
):
    store = await service.get_store(store_id)
    return StoreMapper.to_api(store)


@router.patch(
    "/{store_id}",
    response_model=Store,
    name="stores:update",
    summary="Update a store",
)
async def update_store(
    store_id: int,
    store_data: StoreUpdate,
    service: StoreService = Depends(get_store_service),
):
    domain_data = StoreMapper.to_domain_update(store_data)
    store = await service.update_store(store_id, domain_data)
    return StoreMapper.to_api(store)


@router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="stores:delete",
    summary="Delete a store",
)
async def delete_store(
    store_id: int,
    service: StoreService = Depends(get_store_service),
):
    await service.delete_store(store_id)


@router.post(
    "/{store_id}/inventory/add",
    status_code=status.HTTP_204_NO_CONTENT,
    name="stores:add_stock",
    summary="Add stock for a book",
)
async def add_stock(
    store_id: int,
    inventory_data: StoreInventoryBase,
    service: StoreService = Depends(get_store_service),
):
    await service.add_stock(store_id, inventory_data.book_id, inventory_data.quantity)


@router.post(
    "/{store_id}/inventory/remove",
    status_code=status.HTTP_204_NO_CONTENT,
    name="stores:remove_stock",
    summary="Remove stock for a book",
)
async def remove_stock(
    store_id: int,
    inventory_data: StoreInventoryBase,
    service: StoreService = Depends(get_store_service),
):
    await service.remove_stock(
        store_id, inventory_data.book_id, inventory_data.quantity
    )


@router.get(
    "/{store_id}/inventory/{book_id}",
    response_model=int,
    name="stores:get_stock",
    summary="Get stock for a book",
)
async def get_stock(
    store_id: int,
    book_id: int,
    service: StoreService = Depends(get_store_service),
):
    return await service.get_stock(store_id, book_id)

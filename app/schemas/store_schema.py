from datetime import datetime

from pydantic import BaseModel, Field


class StoreBase(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the store")
    location: str | None = Field(None, description="Physical location or address")


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    location: str | None = None


class Store(StoreBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class StockUpdate(BaseModel):
    quantity: int = Field(..., gt=0, description="Quantity to add or remove")


class StoreInventoryBase(BaseModel):
    book_id: int = Field(..., gt=0, description="ID of the book")
    quantity: int = Field(..., gt=0, description="Quantity to add or remove")

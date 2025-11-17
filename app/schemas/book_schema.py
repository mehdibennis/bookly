from datetime import datetime

from pydantic import BaseModel


# --- Shared properties ---
class BookBase(BaseModel):
    title: str
    authors: list[int]
    authors_details: list[dict] | None = None
    authors_number: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- For creation ---
class BookCreate(BookBase):
    pass


# --- For update ---
class BookUpdate(BaseModel):
    title: str | None = None
    authors: list[int] | None = None


# --- For reading / response ---
class Book(BookBase):
    id: int

    class ConfigDict:
        from_attributes = True  # ✅ replace orm_mode=True (Pydantic v2)

from pydantic import BaseModel


# --- Shared properties ---
class BookBase(BaseModel):
    title: str
    authors: list[int]
    authors_details: list[dict] | None = None
    authors_number: int | None = None


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


class BookWithDetails(Book):
    created_at: str | None = None
    updated_at: str | None = None
    # authors already included in BookBase

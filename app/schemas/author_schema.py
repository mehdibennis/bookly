from datetime import date, datetime

from pydantic import BaseModel, field_validator


# --- Shared properties ---
class AuthorBase(BaseModel):
    first_name: str
    last_name: str
    birth_date: date | str | None = None
    death_date: date | str | None = None
    nationality: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("birth_date", "death_date", mode="before")
    @classmethod
    def parse_date(cls, value):
        """Parse date from multiple formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY"""
        if value is None or isinstance(value, date):
            return value

        if isinstance(value, str):
            # Try common date formats
            formats = [
                "%Y-%m-%d",  # ISO: 1826-04-12
                "%d/%m/%Y",  # European: 12/04/1826
                "%m/%d/%Y",  # American: 04/12/1826
                "%Y/%m/%d",  # Alternative ISO: 1826/04/12
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            # If no format matches, raise error
            raise ValueError(
                f"Date '{value}' ne correspond à aucun format accepté. "
                f"Formats valides: YYYY-MM-DD (ex: 1826-04-12), DD/MM/YYYY (ex: 12/04/1826), MM/DD/YYYY (ex: 04/12/1826)"
            )

        return value


# --- For creation ---
class AuthorCreate(AuthorBase):
    pass


# --- For update ---
class AuthorUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | str | None = None
    death_date: date | str | None = None
    nationality: str | None = None
    bio: str | None = None
    photo_url: str | None = None

    @field_validator("birth_date", "death_date", mode="before")
    @classmethod
    def parse_date(cls, value):
        """Parse date from multiple formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY"""
        if value is None or isinstance(value, date):
            return value

        if isinstance(value, str):
            # Try common date formats
            formats = [
                "%Y-%m-%d",  # ISO: 1826-04-12
                "%d/%m/%Y",  # European: 12/04/1826
                "%m/%d/%Y",  # American: 04/12/1826
                "%Y/%m/%d",  # Alternative ISO: 1826/04/12
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            # If no format matches, raise error
            raise ValueError(
                f"Date '{value}' ne correspond à aucun format accepté. "
                f"Formats valides: YYYY-MM-DD (ex: 1826-04-12), DD/MM/YYYY (ex: 12/04/1826), MM/DD/YYYY (ex: 04/12/1826)"
            )

        return value


# --- For reading / response ---
class Author(AuthorBase):
    id: int

    class ConfigDict:
        from_attributes = True  # ✅ replace orm_mode=True (Pydantic v2)

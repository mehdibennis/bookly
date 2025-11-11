from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class AuthorEntity:
    id: int | None
    first_name: str
    last_name: str
    birth_date: date | None = None
    death_date: date | None = None
    nationality: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def normalize(self):
        self.first_name = self.first_name.strip().title()
        self.last_name = self.last_name.strip().title()
        self.nationality = self.nationality.strip().title() if self.nationality else None
        self.bio = self.bio.strip() if self.bio else None
        self.photo_url = self.photo_url.strip() if self.photo_url else None
        return self


@dataclass
class BookEntity:
    id: int | None
    title: str
    authors: list[int] = field(default_factory=list)  # Multiple authors (M2M)
    authors_details: list[dict] = field(default_factory=list)  # Multiple authors (M2M)
    authors_number: int | None = None  # Number of authors

    def normalize(self):
        self.title = self.title.strip().title()
        return self

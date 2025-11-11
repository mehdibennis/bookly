from sqlalchemy import Column, Date, Integer, String
from sqlalchemy.orm import relationship

from app.db.models.associations import book_authors
from app.db.models.mixins import TimestampMixin
from app.db.session import Base


class Author(Base, TimestampMixin):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True, nullable=False)
    last_name = Column(String, index=True, nullable=False)
    bio = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    death_date = Column(Date, nullable=True)
    nationality = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)

    # Many-to-many: books where this author is one of the authors
    books = relationship(
        "Book",
        secondary=book_authors,
        back_populates="authors",
        lazy="selectin",
    )

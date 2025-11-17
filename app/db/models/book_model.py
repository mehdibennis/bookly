from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.models.associations import book_authors
from app.db.models.mixins import TimestampMixin
from app.db.session import Base


class Book(Base, TimestampMixin):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    # Many-to-many: authors list
    authors = relationship(
        "Author",
        secondary=book_authors,
        back_populates="books",
        lazy="selectin",
    )

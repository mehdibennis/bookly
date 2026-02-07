from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.models.mixins import TimestampMixin
from app.db.session import Base


class Store(Base, TimestampMixin):
    """Represents a physical or digital store managing book stock."""

    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    location = Column(String, nullable=True)

    inventories = relationship(
        "StoreInventory",
        back_populates="store",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class StoreInventory(Base, TimestampMixin):
    """Association table storing per-store stock levels for each book."""

    __tablename__ = "store_inventories"

    store_id = Column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True
    )
    book_id = Column(
        Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    quantity = Column(Integer, nullable=False, default=0)

    store = relationship("Store", back_populates="inventories")
    book = relationship("Book", back_populates="store_entries")

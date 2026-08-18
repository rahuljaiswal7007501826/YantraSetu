"""Farmer model.

A farmer is the "demand" side of YantraSetu - the person who needs a machine for
an operation on one of their fields. Latitude/longitude is the farmer's home/base
point; individual field locations live on the Field model.
"""
from typing import TYPE_CHECKING

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.demand_request import DemandRequest
    from app.models.field import Field


class Farmer(Base):
    __tablename__ = "farmers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    village: Mapped[str] = mapped_column(String(120), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationship: one farmer has many fields.
    fields: Mapped[list["Field"]] = relationship(
        back_populates="farmer",
        cascade="all, delete-orphan",
    )
    # One farmer can raise many machinery requests.
    demand_requests: Mapped[list["DemandRequest"]] = relationship(
        back_populates="farmer", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Farmer id={self.id} name={self.name!r}>"

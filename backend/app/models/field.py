"""Field model.

A field is a specific plot owned by a farmer, with a crop and a location. A
machinery request always targets a field, which is how we know where the machine
has to go and what operation fits.
"""
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.demand_request import DemandRequest
    from app.models.farmer import Farmer


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("farmers.id"), nullable=False, index=True
    )
    crop_type: Mapped[str] = mapped_column(String(80), nullable=False)
    area: Mapped[float] = mapped_column(Float, default=0.0)  # in acres
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationship: many fields -> one farmer.
    farmer: Mapped["Farmer"] = relationship(back_populates="fields")
    # Requests raised against this field.
    demand_requests: Mapped[list["DemandRequest"]] = relationship(
        back_populates="field", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Field id={self.id} crop={self.crop_type!r} farmer_id={self.farmer_id}>"

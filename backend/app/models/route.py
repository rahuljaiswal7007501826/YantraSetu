"""Route and RouteStop models.

A Route is one optimized visiting plan for a machine (produced by the route
engine). Each RouteStop is a single ordered point on that plan - the depot first
(sequence 0), then the farmer stops in visit order, each with arrival/service
times. Together they let the frontend redraw 'Depot -> Farmer 1 -> ...' with ETAs
without re-running the solver.
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.machine import Machine


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="optimized", index=True)
    depot_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    depot_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    total_distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    total_travel_time_min: Mapped[int] = mapped_column(Integer, default=0)
    total_route_duration_min: Mapped[int] = mapped_column(Integer, default=0)
    returned_to_depot: Mapped[bool] = mapped_column(Boolean, default=False)
    # Farmers that could not be fitted into the plan (from the engine).
    dropped_stop_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    machine: Mapped["Machine"] = relationship()
    stops: Mapped[list["RouteStop"]] = relationship(
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteStop.sequence_number",
    )

    def __repr__(self) -> str:
        return f"<Route #{self.id} machine={self.machine_id}>"


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(
        ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # The DemandRequest this stop serves (NULL for the depot). Kept as a plain
    # int (not a hard FK) so the engine stays generic - a stop could later be a
    # booking instead of a request.
    request_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_depot: Mapped[bool] = mapped_column(Boolean, default=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    arrival_min: Mapped[int] = mapped_column(Integer, default=0)
    service_start_min: Mapped[int] = mapped_column(Integer, default=0)
    service_end_min: Mapped[int] = mapped_column(Integer, default=0)
    service_duration_min: Mapped[int] = mapped_column(Integer, default=0)

    route: Mapped["Route"] = relationship(back_populates="stops")

    def __repr__(self) -> str:
        return f"<RouteStop route={self.route_id} seq={self.sequence_number} req={self.request_id}>"

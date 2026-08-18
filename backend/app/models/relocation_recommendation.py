"""RelocationRecommendation model.

A recommendation to move one machine from its home CHC to a shortage cluster.
The system only ever *recommends* (status starts 'pending'); a CHC operator must
approve or reject it. Nothing is relocated automatically.

Note: clusters in this MVP are labels derived from CHC.location (there is no
separate Cluster table), so the destination is stored as a string `to_cluster`
rather than a foreign-key id.
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.chc import CHC
    from app.models.machine import Machine


class RelocationRecommendation(Base):
    __tablename__ = "relocation_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_chc_id: Mapped[int] = mapped_column(
        ForeignKey("chcs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_cluster: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    machine_type: Mapped[str] = mapped_column(String(80), nullable=False)

    net_benefit: Mapped[float] = mapped_column(Float, nullable=False)
    relocation_cost: Mapped[float] = mapped_column(Float, default=0.0)
    expected_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    expected_farmers_served: Mapped[int] = mapped_column(Integer, default=0)

    # pending | approved | rejected | completed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    # Full explainable term-by-term breakdown of the NetBenefit calculation.
    benefit_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # One-directional links (no back-collection needed on Machine/CHC).
    machine: Mapped["Machine"] = relationship()
    from_chc: Mapped["CHC"] = relationship()

    def __repr__(self) -> str:
        return (f"<RelocationRecommendation #{self.id} machine={self.machine_id} "
                f"-> {self.to_cluster} status={self.status}>")

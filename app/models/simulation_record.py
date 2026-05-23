"""ORM model for persisted simulation runs."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SimulationRecord(Base):
    """Stored result of a material preparation and coating simulation."""

    __tablename__ = "simulation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material: Mapped[str] = mapped_column(String(64), nullable=False)
    coating: Mapped[str] = mapped_column(String(64), nullable=False)
    panel_width_m: Mapped[float] = mapped_column(Float, nullable=False)
    panel_height_m: Mapped[float] = mapped_column(Float, nullable=False)
    panel_area_sqm: Mapped[float] = mapped_column(Float, nullable=False)
    prep_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    coating_thickness_microns: Mapped[int] = mapped_column(Integer, nullable=False)
    total_process_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    waste_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    waste_mass_kg: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

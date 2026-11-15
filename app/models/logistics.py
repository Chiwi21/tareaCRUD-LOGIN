from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Carrier(Base):
    __tablename__ = "carriers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    carrier_type: Mapped[str] = mapped_column(String(20), default="OCEAN")
    contact: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    shipments: Mapped[list[Shipment]] = relationship(back_populates="carrier")


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), unique=True, index=True
    )
    carrier_id: Mapped[int | None] = mapped_column(
        ForeignKey("carriers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tracking_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    origin_port_id: Mapped[int | None] = mapped_column(
        ForeignKey("ports.id", ondelete="SET NULL"), nullable=True
    )
    destination_port_id: Mapped[int | None] = mapped_column(
        ForeignKey("ports.id", ondelete="SET NULL"), nullable=True
    )
    departure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_arrival: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_arrival: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    operation: Mapped[Operation] = relationship(back_populates="shipment")
    carrier: Mapped[Carrier | None] = relationship(back_populates="shipments")
    origin_port: Mapped[Port | None] = relationship(foreign_keys=[origin_port_id])
    destination_port: Mapped[Port | None] = relationship(foreign_keys=[destination_port_id])

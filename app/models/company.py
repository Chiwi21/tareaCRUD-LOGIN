from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    tax_id: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    country: Mapped[Country | None] = relationship(back_populates="companies")
    users: Mapped[list[User]] = relationship(back_populates="company")
    operations: Mapped[list[Operation]] = relationship(back_populates="company")

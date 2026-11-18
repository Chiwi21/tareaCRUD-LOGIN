"""Extensiones aditivas del Core: no requieren alterar las tablas heredadas."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class OperationTradeProfile(Base):
    __tablename__ = 'operation_trade_profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey('operations.id', ondelete='CASCADE'), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(30), default='general')
    product_name: Mapped[str] = mapped_column(String(160), default='')
    product_description: Mapped[str] = mapped_column(Text, default='')
    hs_code: Mapped[str] = mapped_column(String(20), default='')
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    budget: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    operation = relationship('Operation')

class FreightComparison(Base):
    __tablename__ = 'freight_comparisons'
    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey('operations.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    mode: Mapped[str] = mapped_column(String(10))
    inputs_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    operation = relationship('Operation')

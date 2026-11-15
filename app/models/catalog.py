from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    iso_code: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    ports: Mapped[list[Port]] = relationship(back_populates="country")
    companies: Mapped[list[Company]] = relationship(back_populates="country")


class Port(Base):
    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    port_type: Mapped[str] = mapped_column(String(20), default="SEAPORT")
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    country: Mapped[Country] = relationship(back_populates="ports")
    operations_origin: Mapped[list[Operation]] = relationship(
        back_populates="origin_port", foreign_keys="Operation.origin_port_id"
    )
    operations_destination: Mapped[list[Operation]] = relationship(
        back_populates="destination_port", foreign_keys="Operation.destination_port_id"
    )


class Currency(Base):
    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(5), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    symbol: Mapped[str] = mapped_column(String(8), default="$")

    operations: Mapped[list[Operation]] = relationship(back_populates="currency")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="currency")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    products: Mapped[list[Product]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unit: Mapped[str] = mapped_column(String(20), default="UND")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    category: Mapped[Category | None] = relationship(back_populates="products")
    operation_items: Mapped[list[OperationItem]] = relationship(back_populates="product")


class Incoterm(Base):
    __tablename__ = "incoterms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    operations: Mapped[list[Operation]] = relationship(back_populates="incoterm")


class CostConcept(Base):
    __tablename__ = "cost_concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    calculation_type: Mapped[str] = mapped_column(String(20), default="FIXED")
    category: Mapped[str] = mapped_column(String(20), default="OTHER")
    default_rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    scenario_items: Mapped[list[CostScenarioItem]] = relationship(back_populates="concept")


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    applies_to: Mapped[str] = mapped_column(String(10), default="BOTH")
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_expiry: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    documents: Mapped[list[Document]] = relationship(back_populates="document_type")

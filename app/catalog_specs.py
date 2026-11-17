"""Especificaciones declarativas de los catálogos administrables.

Una sola plantilla y un solo servicio genérico atienden diez catálogos. Cada
catálogo declara sus campos y columnas; agregar uno nuevo no obliga a duplicar
rutas ni formularios.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.constants import (
    CALCULATION_TYPES,
    CARRIER_TYPES,
    COST_CATEGORIES,
    DOCUMENT_APPLIES_TO,
    PORT_TYPES,
)
from app.models import (
    Carrier,
    Category,
    Company,
    CostConcept,
    Country,
    Currency,
    DocumentType,
    Incoterm,
    Port,
    Product,
)


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: str = "text"  # text, textarea, integer, decimal, checkbox, select
    required: bool = False
    options_source: str | None = None
    choices: tuple[tuple[str, str], ...] | None = None
    help_text: str = ""
    step: str = "0.01"


@dataclass(frozen=True)
class CatalogSpec:
    key: str
    title: str
    singular: str
    description: str
    model: type[Any]
    fields: tuple[FieldSpec, ...]
    columns: tuple[tuple[str, str], ...]
    search_fields: tuple[str, ...]


def _choices(mapping: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(mapping.items())


COMPANIES = CatalogSpec(
    key="companies",
    title="Empresas",
    singular="empresa",
    description="Clientes, proveedores y empresas vinculadas a las operaciones.",
    model=Company,
    fields=(
        FieldSpec("name", "Razón social", required=True),
        FieldSpec("tax_id", "RUC / Tax ID"),
        FieldSpec("email", "Correo electrónico"),
        FieldSpec("phone", "Teléfono"),
        FieldSpec("address", "Dirección", kind="textarea"),
        FieldSpec("country_id", "País", kind="select", options_source="countries"),
        FieldSpec("is_active", "Activa", kind="checkbox"),
    ),
    columns=(("name", "Razón social"), ("tax_id", "RUC"), ("country_id", "País"), ("email", "Correo"), ("is_active", "Activa")),
    search_fields=("name", "tax_id", "email"),
)

COUNTRIES = CatalogSpec(
    key="countries",
    title="Países",
    singular="país",
    description="Países de origen y destino del comercio exterior.",
    model=Country,
    fields=(
        FieldSpec("iso_code", "Código ISO", required=True, help_text="Ejemplo: ECU, CHN, USA."),
        FieldSpec("name", "Nombre", required=True),
    ),
    columns=(("iso_code", "ISO"), ("name", "País")),
    search_fields=("iso_code", "name"),
)

PORTS = CatalogSpec(
    key="ports",
    title="Puertos y aeropuertos",
    singular="puerto",
    description="Puntos de salida y llegada para las operaciones.",
    model=Port,
    fields=(
        FieldSpec("country_id", "País", kind="select", required=True, options_source="countries"),
        FieldSpec("name", "Nombre", required=True),
        FieldSpec("code", "Código", required=True, help_text="Código tipo UN/LOCODE, por ejemplo ECGYE."),
        FieldSpec("port_type", "Tipo", kind="select", required=True, choices=_choices(PORT_TYPES)),
        FieldSpec("city", "Ciudad"),
    ),
    columns=(("name", "Puerto"), ("code", "Código"), ("country_id", "País"), ("port_type", "Tipo")),
    search_fields=("name", "code", "city"),
)

CURRENCIES = CatalogSpec(
    key="currencies",
    title="Monedas",
    singular="moneda",
    description="Monedas usadas en operaciones y facturación.",
    model=Currency,
    fields=(
        FieldSpec("code", "Código", required=True, help_text="ISO 4217: USD, EUR, CNY."),
        FieldSpec("name", "Nombre", required=True),
        FieldSpec("symbol", "Símbolo", required=True),
    ),
    columns=(("code", "Código"), ("name", "Moneda"), ("symbol", "Símbolo")),
    search_fields=("code", "name"),
)

CATEGORIES = CatalogSpec(
    key="categories",
    title="Categorías",
    singular="categoría",
    description="Clasificación del catálogo de productos.",
    model=Category,
    fields=(
        FieldSpec("name", "Nombre", required=True),
        FieldSpec("description", "Descripción", kind="textarea"),
    ),
    columns=(("name", "Categoría"), ("description", "Descripción")),
    search_fields=("name",),
)

PRODUCTS = CatalogSpec(
    key="products",
    title="Productos",
    singular="producto",
    description="Catálogo de bienes con SKU, precio y peso de referencia.",
    model=Product,
    fields=(
        FieldSpec("sku", "SKU", required=True),
        FieldSpec("name", "Nombre", required=True),
        FieldSpec("category_id", "Categoría", kind="select", options_source="categories"),
        FieldSpec("unit", "Unidad", required=True, help_text="UND, CAJA, KG, LITRO..."),
        FieldSpec("unit_price", "Precio unitario", kind="decimal", required=True),
        FieldSpec("weight_kg", "Peso por unidad (kg)", kind="decimal"),
        FieldSpec("is_active", "Activo", kind="checkbox"),
    ),
    columns=(("sku", "SKU"), ("name", "Producto"), ("category_id", "Categoría"), ("unit", "Unidad"), ("unit_price", "Precio"), ("is_active", "Activo")),
    search_fields=("sku", "name"),
)

INCOTERMS = CatalogSpec(
    key="incoterms",
    title="Incoterms",
    singular="incoterm",
    description="Condiciones de entrega internacionales (FOB, CIF, DAP...).",
    model=Incoterm,
    fields=(
        FieldSpec("code", "Código", required=True),
        FieldSpec("name", "Nombre", required=True),
        FieldSpec("description", "Descripción", kind="textarea"),
    ),
    columns=(("code", "Código"), ("name", "Incoterm"), ("description", "Descripción")),
    search_fields=("code", "name"),
)

COST_CONCEPTS = CatalogSpec(
    key="cost-concepts",
    title="Conceptos de costo",
    singular="concepto",
    description="Componentes configurables para los escenarios: producto, flete, seguro y cargos.",
    model=CostConcept,
    fields=(
        FieldSpec("code", "Código", required=True),
        FieldSpec("name", "Nombre", required=True),
        FieldSpec("calculation_type", "Tipo de cálculo", kind="select", required=True, choices=_choices(CALCULATION_TYPES)),
        FieldSpec("category", "Categoría", kind="select", required=True, choices=_choices(COST_CATEGORIES)),
        FieldSpec("default_rate", "Valor por defecto", kind="decimal", required=True),
        FieldSpec("is_active", "Activo", kind="checkbox"),
    ),
    columns=(("code", "Código"), ("name", "Concepto"), ("calculation_type", "Cálculo"), ("category", "Categoría"), ("default_rate", "Valor"), ("is_active", "Activo")),
    search_fields=("code", "name"),
)

DOCUMENT_TYPES = CatalogSpec(
    key="document-types",
    title="Tipos de documento",
    singular="tipo de documento",
    description="Documentos exigidos para importar o exportar y su vigencia.",
    model=DocumentType,
    fields=(
        FieldSpec("code", "Código", required=True),
        FieldSpec("name", "Nombre", required=True),
        FieldSpec("applies_to", "Aplica a", kind="select", required=True, choices=_choices(DOCUMENT_APPLIES_TO)),
        FieldSpec("is_required", "Obligatorio", kind="checkbox"),
        FieldSpec("requires_expiry", "Controla vencimiento", kind="checkbox"),
        FieldSpec("description", "Descripción", kind="textarea"),
    ),
    columns=(("code", "Código"), ("name", "Documento"), ("applies_to", "Aplica a"), ("is_required", "Obligatorio"), ("requires_expiry", "Vence")),
    search_fields=("code", "name"),
)

CARRIERS = CatalogSpec(
    key="carriers",
    title="Transportistas",
    singular="transportista",
    description="Navieras, aerolíneas, transporte terrestre y couriers.",
    model=Carrier,
    fields=(
        FieldSpec("name", "Nombre", required=True),
        FieldSpec("code", "Código", required=True),
        FieldSpec("carrier_type", "Tipo", kind="select", required=True, choices=_choices(CARRIER_TYPES)),
        FieldSpec("contact", "Contacto"),
        FieldSpec("is_active", "Activo", kind="checkbox"),
    ),
    columns=(("name", "Transportista"), ("code", "Código"), ("carrier_type", "Tipo"), ("contact", "Contacto"), ("is_active", "Activo")),
    search_fields=("name", "code"),
)

CATALOG_SPECS: dict[str, CatalogSpec] = {
    spec.key: spec
    for spec in (
        COMPANIES,
        COUNTRIES,
        PORTS,
        CURRENCIES,
        CATEGORIES,
        PRODUCTS,
        INCOTERMS,
        COST_CONCEPTS,
        DOCUMENT_TYPES,
        CARRIERS,
    )
}

OPTION_SOURCES: dict[str, tuple[type[Any], str, str]] = {
    "countries": (Country, "name", "name"),
    "categories": (Category, "name", "name"),
    "currencies": (Currency, "code", "code"),
    "companies": (Company, "name", "name"),
}

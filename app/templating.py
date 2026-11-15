from datetime import date, datetime
from decimal import Decimal

from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.constants import (
    ALERT_STATUSES,
    ALERT_TYPES,
    CALCULATION_TYPES,
    CARRIER_TYPES,
    COST_CATEGORIES,
    DOCUMENT_APPLIES_TO,
    DOCUMENT_STATUSES,
    INVOICE_STATUSES,
    OPERATION_STATUSES,
    OPERATION_TYPES,
    PAYMENT_METHODS,
    PERSON_TYPES,
    PORT_TYPES,
    ROLES,
    SEVERITIES,
    SHIPMENT_STATUSES,
)
from app.flash import get_flashed_messages

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
templates.env.globals.update(
    ROLES=ROLES,
    PERSON_TYPES=PERSON_TYPES,
    OPERATION_TYPES=OPERATION_TYPES,
    OPERATION_STATUSES=OPERATION_STATUSES,
    DOCUMENT_STATUSES=DOCUMENT_STATUSES,
    DOCUMENT_APPLIES_TO=DOCUMENT_APPLIES_TO,
    SHIPMENT_STATUSES=SHIPMENT_STATUSES,
    INVOICE_STATUSES=INVOICE_STATUSES,
    PAYMENT_METHODS=PAYMENT_METHODS,
    CALCULATION_TYPES=CALCULATION_TYPES,
    COST_CATEGORIES=COST_CATEGORIES,
    PORT_TYPES=PORT_TYPES,
    CARRIER_TYPES=CARRIER_TYPES,
    ALERT_TYPES=ALERT_TYPES,
    ALERT_STATUSES=ALERT_STATUSES,
    SEVERITIES=SEVERITIES,
    get_flashed_messages=get_flashed_messages,
)


def money(value) -> str:
    if value is None or value == "":
        return "0.00"
    try:
        return f"{Decimal(str(value)):,.2f}"
    except Exception:
        return str(value)


def datefmt(value, fmt: str = "%Y-%m-%d") -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, date):
        return value.strftime(fmt)
    return str(value)


def status_class(value: str | None) -> str:
    mapping = {
        "PENDING": "pending",
        "IN_PROGRESS": "progress",
        "SHIPPED": "info",
        "DONE": "success",
        "CANCELLED": "danger",
        "APPROVED": "success",
        "RECEIVED": "info",
        "REJECTED": "danger",
        "EXPIRED": "danger",
        "PAID": "success",
        "PARTIAL": "warning",
        "OVERDUE": "danger",
        "ISSUED": "info",
        "DRAFT": "pending",
        "IN_TRANSIT": "info",
        "DELIVERED": "success",
        "DELAYED": "danger",
        "OPEN": "warning",
        "RESOLVED": "success",
        "INFO": "info",
        "WARNING": "warning",
        "CRITICAL": "danger",
    }
    return mapping.get(value or "", "pending")


templates.env.filters["money"] = money
templates.env.filters["datefmt"] = datefmt
templates.env.filters["status_class"] = status_class

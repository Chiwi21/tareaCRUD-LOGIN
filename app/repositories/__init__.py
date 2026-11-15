"""Repositorios SQLAlchemy que implementan los protocolos de dominio."""

from app.repositories.alert_repository import SqlAlchemyAlertRepository
from app.repositories.audit_repository import SqlAlchemyAuditRepository
from app.repositories.billing_repository import SqlAlchemyBillingRepository
from app.repositories.catalog_repository import SqlAlchemyCatalogRepository
from app.repositories.cost_repository import SqlAlchemyCostRepository
from app.repositories.dashboard_repository import SqlAlchemyDashboardRepository
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.repositories.logistics_repository import SqlAlchemyLogisticsRepository
from app.repositories.operation_repository import SqlAlchemyOperationRepository

__all__ = [
    "SqlAlchemyAlertRepository",
    "SqlAlchemyAuditRepository",
    "SqlAlchemyBillingRepository",
    "SqlAlchemyCatalogRepository",
    "SqlAlchemyCostRepository",
    "SqlAlchemyDashboardRepository",
    "SqlAlchemyDocumentRepository",
    "SqlAlchemyLogisticsRepository",
    "SqlAlchemyOperationRepository",
]

"""Proveedores de dependencias (DIP + ISP).

Los routers piden interfaces; estas funciones entregan implementaciones
concretas. En pruebas se reemplazan con ``app.dependency_overrides``.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import (
    SqlAlchemyAlertRepository,
    SqlAlchemyAuditRepository,
    SqlAlchemyBillingRepository,
    SqlAlchemyCatalogRepository,
    SqlAlchemyCostRepository,
    SqlAlchemyDashboardRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyLogisticsRepository,
    SqlAlchemyOperationRepository,
)
from app.repositories.protocols import (
    AlertRepository,
    AuditRepository,
    BillingRepository,
    CatalogRepository,
    CostRepository,
    DashboardRepository,
    DocumentRepository,
    LogisticsRepository,
    OperationReader,
    OperationWriter,
)
from app.services import (
    AlertService,
    AuditService,
    BillingService,
    CatalogService,
    CostService,
    DashboardService,
    DocumentService,
    LogisticsService,
    OperationService,
)


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------
def get_audit_repository(db: Session = Depends(get_db)) -> AuditRepository:
    return SqlAlchemyAuditRepository(db)


def get_audit_service(
    repository: AuditRepository = Depends(get_audit_repository),
) -> AuditService:
    return AuditService(repository)


# ---------------------------------------------------------------------------
# Operaciones
# ---------------------------------------------------------------------------
def get_operation_repository(db: Session = Depends(get_db)) -> SqlAlchemyOperationRepository:
    return SqlAlchemyOperationRepository(db)


def get_operation_reader(
    repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
) -> OperationReader:
    """Entrega la implementación concreta que consume la interfaz de lectura."""
    return repository


def get_operation_writer(
    repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
) -> OperationWriter:
    return repository


def get_operation_service(
    reader: OperationReader = Depends(get_operation_reader),
    writer: OperationWriter = Depends(get_operation_writer),
    audit: AuditService = Depends(get_audit_service),
) -> OperationService:
    return OperationService(reader, writer, audit)


# ---------------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------------
def get_catalog_repository(db: Session = Depends(get_db)) -> CatalogRepository:
    return SqlAlchemyCatalogRepository(db)


def get_catalog_service(
    repository: CatalogRepository = Depends(get_catalog_repository),
) -> CatalogService:
    return CatalogService(repository)


# ---------------------------------------------------------------------------
# Costos
# ---------------------------------------------------------------------------
def get_cost_repository(db: Session = Depends(get_db)) -> CostRepository:
    return SqlAlchemyCostRepository(db)


def get_cost_service(
    repository: CostRepository = Depends(get_cost_repository),
) -> CostService:
    return CostService(repository)


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------
def get_document_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    return SqlAlchemyDocumentRepository(db)


def get_document_service(
    repository: DocumentRepository = Depends(get_document_repository),
    operations: OperationReader = Depends(get_operation_reader),
    audit: AuditService = Depends(get_audit_service),
) -> DocumentService:
    return DocumentService(repository, operations, audit)


# ---------------------------------------------------------------------------
# Facturación
# ---------------------------------------------------------------------------
def get_billing_repository(db: Session = Depends(get_db)) -> BillingRepository:
    return SqlAlchemyBillingRepository(db)


def get_billing_service(
    repository: BillingRepository = Depends(get_billing_repository),
    operations: OperationReader = Depends(get_operation_reader),
    audit: AuditService = Depends(get_audit_service),
) -> BillingService:
    return BillingService(repository, operations, audit)


# ---------------------------------------------------------------------------
# Logística
# ---------------------------------------------------------------------------
def get_logistics_repository(db: Session = Depends(get_db)) -> LogisticsRepository:
    return SqlAlchemyLogisticsRepository(db)


def get_logistics_service(
    repository: LogisticsRepository = Depends(get_logistics_repository),
    operations: OperationReader = Depends(get_operation_reader),
    audit: AuditService = Depends(get_audit_service),
) -> LogisticsService:
    return LogisticsService(repository, operations, audit)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------
def get_alert_repository(db: Session = Depends(get_db)) -> AlertRepository:
    return SqlAlchemyAlertRepository(db)


def get_alert_service(
    repository: AlertRepository = Depends(get_alert_repository),
    operations: OperationReader = Depends(get_operation_reader),
    documents: DocumentRepository = Depends(get_document_repository),
    billing: BillingRepository = Depends(get_billing_repository),
    logistics: LogisticsRepository = Depends(get_logistics_repository),
) -> AlertService:
    return AlertService(repository, operations, documents, billing, logistics)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def get_dashboard_repository(db: Session = Depends(get_db)) -> DashboardRepository:
    return SqlAlchemyDashboardRepository(db)


def get_dashboard_service(
    repository: DashboardRepository = Depends(get_dashboard_repository),
) -> DashboardService:
    return DashboardService(repository)

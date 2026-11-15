"""Pruebas de los principios SOLID aplicados en TradeLab.

No usan base de datos: los servicios se construyen con implementaciones falsas
de los protocolos. También se prueba el reemplazo de dependencias de FastAPI.

Ejecutar:
    python -m unittest tests.test_solid -v
"""

from __future__ import annotations

import unittest
from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import get_protocol_members

from app.core.costing import (
    CostCalculator,
    CostCalculatorFactory,
    FixedCostCalculator,
    PercentageCostCalculator,
    PerUnitCostCalculator,
    money,
)
from app.dependencies import get_operation_service
from app.repositories.protocols import OperationReader, OperationWriter
from app.routers import operations as operations_router
from app.schemas import OperationCreate
from app.security import require_login
from app.services.errors import ValidationError
from app.services.operation_service import OperationService


class FakeOperationReader:
    """Implementación en memoria del contrato de lectura (ISP)."""

    def __init__(self, operation=None):
        self.operation = operation

    def list(self, filters=None):
        return [self.operation] if self.operation else []

    def get(self, operation_id):
        if self.operation and self.operation.id == operation_id:
            return self.operation
        return None

    def get_by_code(self, code):
        return self.operation if self.operation and self.operation.code == code else None

    def list_assignable_users(self):
        return [SimpleNamespace(id=2, username="importer")]

    def list_companies(self):
        return [SimpleNamespace(id=1, name="Empresa")]

    def list_ports(self):
        return [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    def list_currencies(self):
        return [SimpleNamespace(id=1, code="USD")]

    def list_incoterms(self):
        return [SimpleNamespace(id=1, code="FOB")]

    def list_products(self):
        return [SimpleNamespace(id=10, sku="SKU-1")]

    def list_document_types(self):
        return []

    def list_carriers(self):
        return []

    def list_cost_concepts(self):
        return []

    def list_for_user(self, user_id):
        return self.list()


class FakeOperationWriter:
    """Implementación en memoria del contrato de escritura (ISP)."""

    def __init__(self):
        self.created = None
        self.status_changes = []

    def create(self, data, changed_by_id=None):
        self.created = SimpleNamespace(id=99, code="OP-TEST-0099", status=data.status)
        return self.created

    def update(self, operation_id, data, changed_by_id=None):
        return SimpleNamespace(id=operation_id, code="OP-TEST-0099")

    def delete(self, operation_id):
        return None

    def add_item(self, operation_id, data):
        return SimpleNamespace(id=1)

    def remove_item(self, operation_id, item_id):
        return None

    def change_status(self, operation_id, new_status, changed_by_id, note=None):
        self.status_changes.append((operation_id, new_status, changed_by_id, note))
        return SimpleNamespace(id=operation_id, code="OP-TEST-0099", status=new_status)


class FakeAuditService:
    def __init__(self):
        self.entries = []

    def log(self, user_id, action, entity, entity_id=None, detail=None):
        self.entries.append((user_id, action, entity, entity_id, detail))


class CostCalculatorTests(unittest.TestCase):
    def test_fixed_percentage_and_per_unit(self):
        fixed = FixedCostCalculator()
        percentage = PercentageCostCalculator()
        per_unit = PerUnitCostCalculator()

        self.assertEqual(fixed.calculate(base=Decimal("1000"), quantity=Decimal("2"), rate=Decimal("150")), Decimal("150.00"))
        self.assertEqual(
            percentage.calculate(base=Decimal("1000"), quantity=Decimal("1"), rate=Decimal("1.5")),
            Decimal("15.00"),
        )
        self.assertEqual(
            per_unit.calculate(base=Decimal("0"), quantity=Decimal("12"), rate=Decimal("4.5")),
            Decimal("54.00"),
        )

    def test_lsp_all_strategies_are_interchangeable(self):
        strategies = (FixedCostCalculator(), PercentageCostCalculator(), PerUnitCostCalculator())
        for strategy in strategies:
            with self.subTest(strategy=type(strategy).__name__):
                self.assertIsInstance(strategy, CostCalculator)
                result = strategy.calculate(
                    base=Decimal("100"), quantity=Decimal("3"), rate=Decimal("10")
                )
                self.assertIsInstance(result, Decimal)
                self.assertEqual(result, money(result))

    def test_ocp_register_new_strategy_without_modifying_existing_ones(self):
        class DoubleRateCalculator(CostCalculator):
            def calculate(self, *, base, quantity, rate):
                return money(rate * 2)

        CostCalculatorFactory.register("DOUBLE_RATE_TEST", DoubleRateCalculator())
        try:
            calculator = CostCalculatorFactory.get("DOUBLE_RATE_TEST")
            self.assertIsInstance(calculator, DoubleRateCalculator)
            self.assertEqual(
                calculator.calculate(
                    base=Decimal("0"), quantity=Decimal("1"), rate=Decimal("25")
                ),
                Decimal("50.00"),
            )
        finally:
            CostCalculatorFactory._calculators.pop("DOUBLE_RATE_TEST", None)


class InterfaceSegregationTests(unittest.TestCase):
    def test_reader_and_writer_contracts_do_not_overlap(self):
        reader_methods = set(get_protocol_members(OperationReader))
        writer_methods = set(get_protocol_members(OperationWriter))
        self.assertTrue(reader_methods)
        self.assertTrue(writer_methods)
        self.assertEqual(reader_methods & writer_methods, set())

    def test_service_accepts_separate_read_and_write_implementations(self):
        reader = FakeOperationReader()
        writer = FakeOperationWriter()
        service = OperationService(reader, writer, FakeAuditService())
        data = OperationCreate(
            type="IMPORT",
            company_id=1,
            user_id=2,
            origin_port_id=1,
            destination_port_id=2,
            currency_id=1,
            incoterm_id=1,
        )
        operation = service.create(data, actor_id=7)
        self.assertEqual(operation.code, "OP-TEST-0099")
        self.assertIs(writer.created, operation)


class SolidServiceTests(unittest.TestCase):
    def setUp(self):
        self.reader = FakeOperationReader(
            SimpleNamespace(id=1, code="OP-TEST-0001", status="PENDING")
        )
        self.writer = FakeOperationWriter()
        self.audit = FakeAuditService()
        self.service = OperationService(self.reader, self.writer, self.audit)

    def test_srp_service_delegates_persistence_and_audit(self):
        data = OperationCreate(type="IMPORT", user_id=2, company_id=1)
        operation = self.service.create(data, actor_id=7)
        self.assertIs(operation, self.writer.created)
        self.assertEqual(
            self.audit.entries[0][:4],
            (7, "CREATE", "operations", operation.id),
        )

    def test_dip_service_depends_on_protocols_not_sqlalchemy(self):
        self.assertFalse(hasattr(self.service, "db"))
        self.assertIs(self.service.reader, self.reader)
        self.assertIs(self.service.writer, self.writer)

    def test_status_flow_is_enforced_in_business_layer(self):
        with self.assertRaises(ValidationError):
            self.service.change_status(1, "DONE", actor_id=7)
        self.assertEqual(self.writer.status_changes, [])

        changed = self.service.change_status(1, "IN_PROGRESS", actor_id=7, note="inicio")
        self.assertEqual(changed.status, "IN_PROGRESS")
        self.assertEqual(len(self.writer.status_changes), 1)
        self.assertEqual(self.audit.entries[-1][1], "STATUS_CHANGE")


class DependencyInjectionTests(unittest.TestCase):
    def test_fastapi_dependency_override_replaces_operation_service(self):
        class FakeOperationService:
            def list(self, filters=None):
                return []

        test_app = FastAPI()
        test_app.include_router(operations_router.router)
        test_app.dependency_overrides[require_login] = lambda: SimpleNamespace(
            id=1, role="ADMIN"
        )
        test_app.dependency_overrides[get_operation_service] = lambda: FakeOperationService()

        client = TestClient(test_app)
        response = client.get("/api/operations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


if __name__ == "__main__":
    unittest.main()

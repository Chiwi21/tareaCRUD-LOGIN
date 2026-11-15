"""Pruebas de integración de los flujos HTML y REST de TradeLab.

Se ejecutan con una base SQLite temporal y ``dependency_overrides`` para no
tocar la base local ``data/app.db``. El seed se reutiliza para tener catálogos,
usuarios y operaciones reales.

Ejecutar:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin123"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, engine as app_engine, get_db
from app.main import app
from app.models import (
    Alert,
    Carrier,
    Company,
    CostConcept,
    CostScenario,
    Country,
    Currency,
    Document,
    DocumentType,
    Incoterm,
    Invoice,
    Operation,
    OperationItem,
    Payment,
    Port,
    Product,
    Shipment,
    User,
)
from app.security import verify_password
from app.user_validation import es_cedula_ecuatoriana_valida
from seed import (
    create_admin,
    generate_alerts,
    seed_catalogs,
    seed_demo_operations,
    seed_users,
)


class TradeLabFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "tradelab_test.db"
        cls.engine = create_engine(
            f"sqlite:///{cls.db_path}", connect_args={"check_same_thread": False}
        )

        @event.listens_for(cls.engine, "connect")
        def _enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(bind=cls.engine)
        cls.Session = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

        db = cls.Session()
        try:
            create_admin(db)
            cls.catalog_data = seed_catalogs(db)
            cls.demo_users = seed_users(db, cls.catalog_data)
            seed_demo_operations(db, cls.catalog_data, cls.demo_users)
            generate_alerts(db)
        finally:
            db.close()

        def override_get_db():
            session = cls.Session()
            try:
                yield session
            finally:
                session.close()

        cls._override_get_db = staticmethod(override_get_db)
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
        response = cls.client.post(
            "/login", data={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 303, response.text

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_db, None)
        cls.client.close()
        cls.engine.dispose()
        app_engine.dispose()
        cls.temp_dir.cleanup()

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def assert_redirect(self, response, location: str | None = None):
        self.assertEqual(response.status_code, 303, response.text[:800])
        if location is not None:
            self.assertEqual(response.headers.get("location"), location)

    def session(self):
        return self.Session()

    def test_01_catalog_crud(self):
        response = self.client.post(
            "/catalogs/countries/new",
            data={"iso_code": "TST", "name": "País de Prueba"},
        )
        self.assert_redirect(response)

        db = self.session()
        try:
            country = db.query(Country).filter_by(iso_code="TST").one()
            country_id = country.id
        finally:
            db.close()

        response = self.client.post(
            f"/catalogs/countries/{country_id}/edit",
            data={"iso_code": "TST", "name": "País de Prueba Editado"},
        )
        self.assert_redirect(response)

        db = self.session()
        try:
            db.expire_all()
            self.assertEqual(db.get(Country, country_id).name, "País de Prueba Editado")
        finally:
            db.close()

        self.assert_redirect(self.client.post(f"/catalogs/countries/{country_id}/delete"))
        db = self.session()
        try:
            db.expire_all()
            self.assertIsNone(db.get(Country, country_id))
        finally:
            db.close()

        response = self.client.post(
            "/catalogs/products/new",
            data={
                "sku": "TST-001",
                "name": "Producto de prueba",
                "category_id": "",
                "unit": "UND",
                "unit_price": "10.50",
                "weight_kg": "0.5",
                "is_active": "1",
            },
        )
        self.assert_redirect(response)

        db = self.session()
        try:
            product = db.query(Product).filter_by(sku="TST-001").one()
            product_id = product.id
        finally:
            db.close()

        response = self.client.post(
            f"/catalogs/products/{product_id}/edit",
            data={
                "sku": "TST-001",
                "name": "Producto de prueba editado",
                "category_id": "",
                "unit": "CAJA",
                "unit_price": "11.25",
                "weight_kg": "0.6",
                "is_active": "1",
            },
        )
        self.assert_redirect(response)

        db = self.session()
        try:
            db.expire_all()
            updated = db.get(Product, product_id)
            self.assertTrue(updated.name.endswith("editado"))
            self.assertEqual(updated.unit, "CAJA")
        finally:
            db.close()

        self.assert_redirect(self.client.post(f"/catalogs/products/{product_id}/delete"))
        db = self.session()
        try:
            db.expire_all()
            self.assertIsNone(db.get(Product, product_id))
        finally:
            db.close()

    def test_02_admin_user_crud(self):
        db = self.session()
        try:
            used = {user.cedula for user in db.query(User).all() if user.cedula}
        finally:
            db.close()

        cedula = next(
            (
                f"{number:010d}"
                for number in range(1700000000, 1700000200)
                if f"{number:010d}" not in used
                and es_cedula_ecuatoriana_valida(f"{number:010d}")
            ),
            None,
        )
        self.assertIsNotNone(cedula)

        response = self.client.post(
            "/admin/users/new",
            data={
                "user_type": "IMPORTER",
                "person_type": "NATURAL",
                "username": "flow.user",
                "password": "flow1234",
                "confirm_password": "flow1234",
                "full_name": "Flow User",
                "cedula": cedula,
                "company_id": "",
                "is_active": "1",
            },
        )
        self.assert_redirect(response)

        db = self.session()
        try:
            user = db.query(User).filter_by(username="flow.user").one()
            user_id = user.id
        finally:
            db.close()

        response = self.client.post(
            f"/admin/users/{user_id}/edit",
            data={
                "user_type": "EXPORTER",
                "person_type": "JURIDICA",
                "username": "flow.user",
                "password": "",
                "confirm_password": "",
                "ruc": "1799999999001",
                "razon_social": "Flow Export S.A.",
                "company_id": "",
                "is_active": "1",
            },
        )
        self.assert_redirect(response)

        db = self.session()
        try:
            db.expire_all()
            updated = db.get(User, user_id)
            self.assertEqual(updated.role, "EXPORTER")
            self.assertEqual(updated.ruc, "1799999999001")
            self.assertTrue(verify_password("flow1234", updated.password_hash))
        finally:
            db.close()

        self.assert_redirect(self.client.post(f"/admin/users/{user_id}/delete"))
        db = self.session()
        try:
            db.expire_all()
            self.assertIsNone(db.get(User, user_id))
        finally:
            db.close()

    def test_03_operation_lifecycle_and_modules(self):
        db = self.session()
        try:
            company_id = db.query(Company).first().id
            importer_id = db.query(User).filter_by(username="carlos.import").one().id
            port_ids = [port.id for port in db.query(Port).limit(2).all()]
            currency_id = db.query(Currency).filter_by(code="USD").one().id
            incoterm_id = db.query(Incoterm).filter_by(code="FOB").one().id
            product_id = db.query(Product).filter_by(sku="ELE-001").one().id
            doc_type_id = db.query(DocumentType).filter_by(code="FACTURA_COM").one().id
            expiry_doc_type_id = db.query(DocumentType).filter_by(code="CERT_ORIGEN").one().id
            concept_id = db.query(CostConcept).filter_by(code="FLETE_MAR").one().id
            carrier_id = db.query(Carrier).first().id
        finally:
            db.close()

        payload = {
            "type": "IMPORT",
            "company_id": str(company_id),
            "user_id": str(importer_id),
            "operation_date": date.today().isoformat(),
            "origin_port_id": str(port_ids[0]),
            "destination_port_id": str(port_ids[1]),
            "currency_id": str(currency_id),
            "incoterm_id": str(incoterm_id),
            "status": "PENDING",
            "notes": "Operación creada por prueba de flujo",
        }
        self.assert_redirect(self.client.post("/operations/new", data=payload))

        db = self.session()
        try:
            operation = db.query(Operation).filter_by(
                notes="Operación creada por prueba de flujo"
            ).one()
            operation_id = operation.id
        finally:
            db.close()

        response = self.client.post(
            f"/operations/{operation_id}/edit",
            data={
                **payload,
                "notes": "Operación editada por prueba de flujo",
                "status": "PENDING",
            },
        )
        self.assert_redirect(response)
        db = self.session()
        try:
            self.assertTrue(
                db.get(Operation, operation_id).notes.endswith("editada por prueba de flujo")
            )
        finally:
            db.close()

        response = self.client.post(
            f"/operations/{operation_id}/items",
            data={
                "product_id": str(product_id),
                "quantity": "3",
                "unit_price": "720",
                "description": "Laptops",
            },
        )
        self.assert_redirect(response)
        db = self.session()
        try:
            item = db.query(OperationItem).filter_by(operation_id=operation_id).one()
            self.assertEqual(float(item.subtotal), 2160.0)
            item_id = item.id
        finally:
            db.close()

        self.assert_redirect(
            self.client.post(f"/operations/{operation_id}/items/{item_id}/delete")
        )
        db = self.session()
        try:
            self.assertIsNone(db.get(OperationItem, item_id))
        finally:
            db.close()
        self.assert_redirect(
            self.client.post(
                f"/operations/{operation_id}/items",
                data={
                    "product_id": str(product_id),
                    "quantity": "3",
                    "unit_price": "720",
                    "description": "Laptops",
                },
            )
        )

        # Un salto inválido PENDING -> DONE no debe cambiar el estado.
        self.assert_redirect(
            self.client.post(
                f"/operations/{operation_id}/status",
                data={"status": "DONE", "note": "salto inválido"},
            )
        )
        db = self.session()
        try:
            self.assertEqual(db.get(Operation, operation_id).status, "PENDING")
        finally:
            db.close()

        self.assert_redirect(
            self.client.post(
                f"/operations/{operation_id}/status",
                data={"status": "IN_PROGRESS", "note": "inicio"},
            )
        )
        db = self.session()
        try:
            self.assertEqual(db.get(Operation, operation_id).status, "IN_PROGRESS")
        finally:
            db.close()

        self.assert_redirect(
            self.client.post(
                f"/operations/{operation_id}/scenarios",
                data={"name": "Marítimo FOB prueba", "description": "Escenario de flujo"},
            )
        )
        db = self.session()
        try:
            scenario_id = (
                db.query(CostScenario).filter_by(operation_id=operation_id).one().id
            )
        finally:
            db.close()

        self.assert_redirect(
            self.client.post(
                f"/scenarios/{scenario_id}/items",
                data={
                    "concept_id": str(concept_id),
                    "description": "Flete",
                    "calculation_type": "FIXED",
                    "rate": "1200",
                    "quantity": "1",
                    "base_amount": "0",
                },
            )
        )
        self.assert_redirect(self.client.post(f"/scenarios/{scenario_id}/select"))
        db = self.session()
        try:
            scenario = db.get(CostScenario, scenario_id)
            self.assertTrue(scenario.is_selected)
            self.assertEqual(float(scenario.total), 1200.0)
        finally:
            db.close()

        response = self.client.post(
            "/documents/new",
            data={
                "operation_id": str(operation_id),
                "document_type_id": str(doc_type_id),
                "name": "Factura comercial de prueba",
                "status": "APPROVED",
                "file_url": "https://example.com/factura.pdf",
                "issue_date": date.today().isoformat(),
                "expiry_date": "",
                "notes": "doc flow",
            },
        )
        self.assert_redirect(response)
        db = self.session()
        try:
            document_id = (
                db.query(Document).filter_by(name="Factura comercial de prueba").one().id
            )
        finally:
            db.close()

        response = self.client.post(
            "/documents/new",
            data={
                "operation_id": str(operation_id),
                "document_type_id": str(expiry_doc_type_id),
                "name": "Certificado sin vencimiento",
                "status": "PENDING",
                "file_url": "",
                "issue_date": date.today().isoformat(),
                "expiry_date": "",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            f"/documents/{document_id}/edit",
            data={
                "document_type_id": str(doc_type_id),
                "name": "Factura comercial actualizada",
                "status": "APPROVED",
                "file_url": "https://example.com/factura2.pdf",
                "issue_date": date.today().isoformat(),
                "expiry_date": "",
                "notes": "editada",
            },
        )
        self.assert_redirect(response)
        db = self.session()
        try:
            self.assertTrue(db.get(Document, document_id).name.endswith("actualizada"))
        finally:
            db.close()

        response = self.client.post(
            "/shipments/new",
            data={
                "operation_id": str(operation_id),
                "carrier_id": str(carrier_id),
                "tracking_number": "TEST-TRACK-001",
                "origin_port_id": str(port_ids[0]),
                "destination_port_id": str(port_ids[1]),
                "departure_date": date.today().isoformat(),
                "estimated_arrival": (date.today() + timedelta(days=10)).isoformat(),
                "actual_arrival": "",
                "status": "IN_TRANSIT",
                "notes": "embarque flow",
            },
        )
        self.assert_redirect(response)
        db = self.session()
        try:
            shipment_id = db.query(Shipment).filter_by(operation_id=operation_id).one().id
        finally:
            db.close()

        response = self.client.post(
            f"/shipments/{shipment_id}/edit",
            data={
                "carrier_id": str(carrier_id),
                "tracking_number": "TEST-TRACK-002",
                "origin_port_id": str(port_ids[0]),
                "destination_port_id": str(port_ids[1]),
                "departure_date": date.today().isoformat(),
                "estimated_arrival": (date.today() + timedelta(days=12)).isoformat(),
                "actual_arrival": "",
                "status": "DELAYED",
                "notes": "editado",
            },
        )
        self.assert_redirect(response)
        db = self.session()
        try:
            self.assertEqual(
                db.get(Shipment, shipment_id).tracking_number, "TEST-TRACK-002"
            )
        finally:
            db.close()

        response = self.client.post(
            "/invoices/new",
            data={
                "operation_id": str(operation_id),
                "currency_id": "",
                "issue_date": date.today().isoformat(),
                "due_date": (date.today() + timedelta(days=15)).isoformat(),
                "tax_amount": "100",
                "notes": "factura flow",
            },
        )
        self.assert_redirect(response)
        db = self.session()
        try:
            invoice = db.query(Invoice).filter_by(operation_id=operation_id).one()
            invoice_id = invoice.id
            invoice_total = float(invoice.total)
        finally:
            db.close()

        self.assert_redirect(
            self.client.post(
                f"/invoices/{invoice_id}/payments",
                data={
                    "amount": f"{invoice_total / 2:.2f}",
                    "payment_date": date.today().isoformat(),
                    "method": "TRANSFER",
                    "reference": "PAY-TEST-1",
                    "notes": "pago parcial",
                },
            )
        )
        db = self.session()
        try:
            invoice = db.get(Invoice, invoice_id)
            self.assertEqual(invoice.status, "PARTIAL")
            payment_id = db.query(Payment).filter_by(invoice_id=invoice_id).one().id
        finally:
            db.close()

        self.assert_redirect(
            self.client.post(
                f"/invoices/{invoice_id}/payments",
                data={
                    "amount": f"{invoice_total / 2:.2f}",
                    "payment_date": date.today().isoformat(),
                    "method": "CARD",
                    "reference": "PAY-TEST-2",
                    "notes": "pago final",
                },
            )
        )
        db = self.session()
        try:
            invoice = db.get(Invoice, invoice_id)
            self.assertEqual(invoice.status, "PAID")
            self.assertEqual(float(invoice.balance), 0.0)
        finally:
            db.close()

        # El sobrepago se rechaza y no crea un tercer pago.
        self.assert_redirect(
            self.client.post(
                f"/invoices/{invoice_id}/payments",
                data={
                    "amount": "1",
                    "payment_date": date.today().isoformat(),
                    "method": "CASH",
                    "reference": "",
                    "notes": "sobrepago",
                },
            )
        )
        db = self.session()
        try:
            self.assertEqual(
                db.query(Payment).filter_by(invoice_id=invoice_id).count(), 2
            )
        finally:
            db.close()

        self.assert_redirect(self.client.post(f"/payments/{payment_id}/delete"))
        db = self.session()
        try:
            self.assertEqual(db.get(Invoice, invoice_id).status, "PARTIAL")
        finally:
            db.close()

        self.assert_redirect(self.client.post("/alerts/generate"))
        db = self.session()
        try:
            alert_id = db.query(Alert).filter_by(status="OPEN").first().id
        finally:
            db.close()
        self.assert_redirect(self.client.post(f"/alerts/{alert_id}/resolve"))
        db = self.session()
        try:
            self.assertEqual(db.get(Alert, alert_id).status, "RESOLVED")
        finally:
            db.close()

        self.assertEqual(
            self.client.get(f"/api/operations/{operation_id}").status_code, 200
        )
        self.assertEqual(
            self.client.get(f"/api/operations/{operation_id}/scenarios").status_code, 200
        )
        self.assertEqual(self.client.get("/api/alerts?status=").status_code, 200)

        # API REST de operaciones: crear, actualizar y eliminar.
        response = self.client.post(
            "/api/operations",
            json={
                "type": "EXPORT",
                "company_id": company_id,
                "user_id": importer_id,
                "operation_date": date.today().isoformat(),
                "origin_port_id": port_ids[0],
                "destination_port_id": port_ids[1],
                "currency_id": currency_id,
                "incoterm_id": incoterm_id,
                "notes": "Operación API",
            },
        )
        self.assertEqual(response.status_code, 200, response.text[:800])
        api_operation_id = response.json()["id"]
        response = self.client.put(
            f"/api/operations/{api_operation_id}",
            json={"type": "IMPORT"},
        )
        self.assertEqual(response.status_code, 200, response.text[:800])
        self.assertEqual(response.json()["type"], "IMPORT")
        self.assertEqual(
            self.client.delete(f"/api/operations/{api_operation_id}").status_code, 200
        )

        # Limpieza de hijos y de la operación principal.
        self.assert_redirect(self.client.post(f"/shipments/{shipment_id}/delete"))
        self.assert_redirect(self.client.post(f"/invoices/{invoice_id}/delete"))
        self.assert_redirect(self.client.post(f"/documents/{document_id}/delete"))
        self.assert_redirect(self.client.post(f"/scenarios/{scenario_id}/delete"))
        self.assert_redirect(self.client.post(f"/operations/{operation_id}/delete"))
        db = self.session()
        try:
            self.assertIsNone(db.get(Operation, operation_id))
        finally:
            db.close()

    def test_04_permissions(self):
        client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
        response = client.post(
            "/login", data={"username": "carlos.import", "password": "demo123"}
        )
        self.assert_redirect(response, "/dashboard")

        for path in (
            "/operations/new",
            "/catalogs",
            "/documents",
            "/alerts",
            "/admin/users",
            "/invoices",
        ):
            response = client.get(path)
            self.assertEqual(response.status_code, 403, path)

        self.assertEqual(client.get("/dashboard").status_code, 200)
        self.assertEqual(client.get("/api/admin/users").status_code, 403)


if __name__ == "__main__":
    unittest.main()

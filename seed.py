"""Datos iniciales y demostración de TradeLab.

Crea catálogos maestros, usuarios de prueba, operaciones con ítems, escenarios
de costo, documentos, embarques, facturas y alertas. Es idempotente: los
catálogos se completan por código y las operaciones demo solo se crean si la
tabla está vacía.

Uso:
    python seed.py
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.constants import (
    CALC_FIXED,
    CALC_PERCENTAGE,
    CALC_PER_UNIT,
    COST_CATEGORY_CHARGES,
    COST_CATEGORY_FREIGHT,
    COST_CATEGORY_INSURANCE,
    COST_CATEGORY_PRODUCT,
    DOC_APPROVED,
    DOC_PENDING,
    DOC_RECEIVED,
    INVOICE_OVERDUE,
    INVOICE_PAID,
    OPERATION_EXPORT,
    OPERATION_IMPORT,
    ROLE_ADMIN,
    ROLE_EXPORTER,
    ROLE_IMPORTER,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    STATUS_SHIPPED,
)
from app.core.costing import CostCalculatorFactory, money
from app.database import SessionLocal, init_database
from app.models import (
    Alert,
    AuditLog,
    Carrier,
    Category,
    Company,
    CostConcept,
    CostScenario,
    CostScenarioItem,
    Country,
    Currency,
    Document,
    DocumentType,
    Incoterm,
    Invoice,
    Operation,
    OperationItem,
    OperationStatusHistory,
    Payment,
    Port,
    Product,
    Shipment,
    User,
)
from app.security import hash_password

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo123")

COUNTRIES = [
    ("ECU", "Ecuador"),
    ("CHN", "China"),
    ("USA", "Estados Unidos"),
    ("COL", "Colombia"),
    ("PER", "Perú"),
    ("ESP", "España"),
    ("MEX", "México"),
    ("BRA", "Brasil"),
    ("CHL", "Chile"),
    ("PAN", "Panamá"),
]

PORTS = [
    ("ECGYE", "Puerto de Guayaquil", "ECU", "SEAPORT", "Guayaquil"),
    ("ECUIO", "Aeropuerto Mariscal Sucre", "ECU", "AIRPORT", "Quito"),
    ("CNSHA", "Puerto de Shanghái", "CHN", "SEAPORT", "Shanghái"),
    ("CNPEK", "Aeropuerto de Pekín", "CHN", "AIRPORT", "Pekín"),
    ("USMIA", "Puerto de Miami", "USA", "SEAPORT", "Miami"),
    ("USLAX", "Puerto de Los Ángeles", "USA", "SEAPORT", "Los Ángeles"),
    ("COBOG", "Aeropuerto El Dorado", "COL", "AIRPORT", "Bogotá"),
    ("PECAL", "Puerto del Callao", "PER", "SEAPORT", "Callao"),
    ("ESVLC", "Puerto de Valencia", "ESP", "SEAPORT", "Valencia"),
    ("MXMEX", "Aeropuerto de Ciudad de México", "MEX", "AIRPORT", "Ciudad de México"),
    ("BRSSZ", "Puerto de Santos", "BRA", "SEAPORT", "Santos"),
    ("CLVAP", "Puerto de Valparaíso", "CHL", "SEAPORT", "Valparaíso"),
]

CURRENCIES = [
    ("USD", "Dólar estadounidense", "$"),
    ("EUR", "Euro", "€"),
    ("CNY", "Yuan chino", "¥"),
    ("COP", "Peso colombiano", "COL$"),
    ("PEN", "Sol peruano", "S/"),
    ("MXN", "Peso mexicano", "MX$"),
    ("BRL", "Real brasileño", "R$"),
    ("CLP", "Peso chileno", "CLP$"),
]

CATEGORIES = [
    ("Textiles y confecciones", "Prendas, telas e insumos textiles."),
    ("Electrónica", "Computadoras, monitores y componentes."),
    ("Alimentos", "Productos agrícolas y alimentos procesados."),
    ("Maquinaria", "Equipos industriales y repuestos."),
    ("Químicos", "Insumos químicos y fertilizantes."),
    ("Insumos médicos", "Dispositivos y material médico."),
    ("Automotriz", "Vehículos, partes y accesorios."),
    ("Muebles", "Mobiliario y accesorios de oficina."),
]

PRODUCTS = [
    ("TEX-001", "Camisetas de algodón", "Textiles y confecciones", "UND", "8.50", "0.25"),
    ("TEX-002", "Jeans denim", "Textiles y confecciones", "UND", "18.00", "0.70"),
    ("TEX-003", "Tela de algodón", "Textiles y confecciones", "MTR", "3.20", "0.40"),
    ("ELE-001", "Laptop empresarial 14\"", "Electrónica", "UND", "720.00", "1.80"),
    ("ELE-002", "Monitor 27\"", "Electrónica", "UND", "185.00", "4.50"),
    ("ELE-003", "Teclado inalámbrico", "Electrónica", "UND", "22.00", "0.60"),
    ("ALI-001", "Banano fresco", "Alimentos", "CAJA", "6.50", "18.00"),
    ("ALI-002", "Cacao en grano", "Alimentos", "QQ", "145.00", "45.00"),
    ("ALI-003", "Café verde", "Alimentos", "QQ", "180.00", "45.00"),
    ("MAQ-001", "Compresor industrial", "Maquinaria", "UND", "1850.00", "120.00"),
    ("MAQ-002", "Bomba hidráulica", "Maquinaria", "UND", "420.00", "18.00"),
    ("QUI-001", "Fertilizante NPK", "Químicos", "KG", "1.10", "1.00"),
    ("MED-001", "Guantes quirúrgicos", "Insumos médicos", "CAJA", "12.00", "2.50"),
    ("MED-002", "Mascarillas N95", "Insumos médicos", "CAJA", "9.50", "1.20"),
    ("AUT-001", "Filtro de aceite", "Automotriz", "UND", "14.00", "0.90"),
    ("MUE-001", "Silla ergonómica", "Muebles", "UND", "95.00", "12.00"),
]

INCOTERMS = [
    ("EXW", "Ex Works", "El comprador retira en las instalaciones del vendedor."),
    ("FCA", "Free Carrier", "El vendedor entrega al transportista designado."),
    ("FOB", "Free On Board", "El vendedor entrega a bordo del buque en el puerto de origen."),
    ("CFR", "Cost and Freight", "El vendedor paga el flete hasta el puerto de destino."),
    ("CIF", "Cost, Insurance and Freight", "Flete y seguro pagados por el vendedor."),
    ("CPT", "Carriage Paid To", "Transporte pagado hasta el destino convenido."),
    ("DAP", "Delivered at Place", "El vendedor entrega en el lugar de destino."),
    ("DDP", "Delivered Duty Paid", "El vendedor asume todos los costos y derechos."),
]

COST_CONCEPTS = [
    ("PRODUCTO", "Valor de productos", CALC_FIXED, COST_CATEGORY_PRODUCT, "0"),
    ("FLETE_MAR", "Flete marítimo", CALC_FIXED, COST_CATEGORY_FREIGHT, "1200"),
    ("FLETE_AER", "Flete aéreo", CALC_FIXED, COST_CATEGORY_FREIGHT, "2400"),
    ("SEGURO", "Seguro de carga", CALC_PERCENTAGE, COST_CATEGORY_INSURANCE, "1.5"),
    ("CARGOS_ORIGEN", "Cargos en origen", CALC_FIXED, COST_CATEGORY_CHARGES, "180"),
    ("CARGOS_DESTINO", "Cargos en destino", CALC_FIXED, COST_CATEGORY_CHARGES, "240"),
    ("AGENTE_ADUANA", "Agente de aduana", CALC_FIXED, COST_CATEGORY_CHARGES, "150"),
    ("TRANSPORTE_INTERNO", "Transporte interno", CALC_PER_UNIT, COST_CATEGORY_CHARGES, "18"),
    ("MANIPULEO", "Manipuleo portuario", CALC_PER_UNIT, COST_CATEGORY_CHARGES, "4.5"),
    ("IMPUESTO_SALIDA", "Impuesto de salida", CALC_PERCENTAGE, COST_CATEGORY_CHARGES, "0.5"),
]

DOCUMENT_TYPES = [
    ("FACTURA_COM", "Factura comercial", "BOTH", True, False),
    ("PACKING", "Packing list", "BOTH", True, False),
    ("BL", "Bill of Lading / conocimiento de embarque", "BOTH", True, False),
    ("CERT_ORIGEN", "Certificado de origen", "BOTH", True, True),
    ("POLIZA", "Póliza de seguro de carga", "BOTH", True, True),
    ("DAE", "Declaración Aduanera de Exportación", "EXPORT", True, False),
    ("PERMISO_IMP", "Permiso de importación", "IMPORT", True, True),
    ("FITO", "Certificado fitosanitario", "EXPORT", True, True),
    ("CALIDAD", "Certificado de calidad", "BOTH", False, True),
    ("GUIA_AEREA", "Guía aérea (AWB)", "BOTH", False, False),
]

CARRIERS = [
    ("MAERSK", "Maersk", "OCEAN", "operaciones@maersk.example"),
    ("MSC", "MSC", "OCEAN", "booking@msc.example"),
    ("HAPAG", "Hapag-Lloyd", "OCEAN", "sales@hapag.example"),
    ("EMIRATES", "Emirates SkyCargo", "AIR", "cargo@emirates.example"),
    ("AVIANCA", "Avianca Cargo", "AIR", "cargo@avianca.example"),
    ("DHL", "DHL Express", "COURIER", "soporte@dhl.example"),
    ("FEDEX", "FedEx", "COURIER", "soporte@fedex.example"),
    ("TRANSAND", "TransAndino", "LAND", "logistica@transandino.example"),
]

COMPANIES = [
    ("Importadora Andina S.A.", "1792345678001", "compras@andina.example", "022345678", "Av. Amazonas y Naciones Unidas, Quito", "ECU"),
    ("Textiles del Pacífico Cía. Ltda.", "0991234567001", "exportaciones@textilpacifico.example", "042345678", "Km 12 vía Daule, Guayaquil", "ECU"),
    ("Global Tech Import S.A.", "1798765432001", "import@globaltech.example", "022987654", "Av. República E7-50, Quito", "ECU"),
    ("AgroExport Ecuador S.A.", "1391234567001", "ventas@agroexport.example", "052345678", "Vía a la Costa, Guayaquil", "ECU"),
    ("Ferretería Central", "1791239876001", "compras@ferreteriacentral.example", "022456789", "Av. 10 de Agosto, Quito", "ECU"),
    ("Pacific Trading LLC", "US-987654321", "sales@pacifictrading.example", "+1 305 555 0101", "1200 Brickell Ave, Miami", "USA"),
]

DEMO_USERS = [
    ("alfredo1", ROLE_IMPORTER, "NATURAL", "Alfredo Chiguano", "1700000001", None, None),
    ("pepito", ROLE_IMPORTER, "NATURAL", "José Pérez", "3040000006", None, None),
    ("carlos.import", ROLE_IMPORTER, "NATURAL", "Carlos Andrade", "1712345678", None, None),
    ("maria.export", ROLE_EXPORTER, "JURIDICA", None, None, "0991234567001", "Textiles del Pacífico Cía. Ltda."),
    ("agro.export", ROLE_EXPORTER, "JURIDICA", None, None, "1391234567001", "AgroExport Ecuador S.A."),
]


def get_or_create(db, model, defaults: dict | None = None, **filters):
    instance = db.query(model).filter_by(**filters).first()
    if instance is not None:
        return instance, False
    instance = model(**filters, **(defaults or {}))
    db.add(instance)
    db.flush()
    return instance, True


def create_admin(db) -> User:
    if not ADMIN_USERNAME.strip():
        raise SystemExit("ADMIN_USERNAME no puede estar vacío.")
    if len(ADMIN_PASSWORD) < 6:
        raise SystemExit("ADMIN_PASSWORD debe tener al menos 6 caracteres.")
    admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if admin is None:
        admin = User(
            username=ADMIN_USERNAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            role=ROLE_ADMIN,
            person_type=None,
            full_name="Administrador TradeLab",
            is_active=True,
        )
        db.add(admin)
        db.flush()
        print(f"Administrador creado: {ADMIN_USERNAME}")
    else:
        admin.role = ROLE_ADMIN
        admin.is_active = True
        print(f"Administrador existente conservado: {ADMIN_USERNAME}")
    return admin


def seed_catalogs(db) -> dict:
    countries = {}
    for iso, name in COUNTRIES:
        country, _ = get_or_create(db, Country, {"name": name}, iso_code=iso)
        countries[iso] = country

    ports = {}
    for code, name, iso, port_type, city in PORTS:
        port, _ = get_or_create(
            db,
            Port,
            {"country_id": countries[iso].id, "name": name, "port_type": port_type, "city": city},
            code=code,
        )
        ports[code] = port

    currencies = {}
    for code, name, symbol in CURRENCIES:
        currency, _ = get_or_create(db, Currency, {"name": name, "symbol": symbol}, code=code)
        currencies[code] = currency

    categories = {}
    for name, description in CATEGORIES:
        category, _ = get_or_create(db, Category, {"description": description}, name=name)
        categories[name] = category

    products = {}
    for sku, name, category_name, unit, price, weight in PRODUCTS:
        product, _ = get_or_create(
            db,
            Product,
            {
                "name": name,
                "category_id": categories[category_name].id,
                "unit": unit,
                "unit_price": Decimal(price),
                "weight_kg": Decimal(weight),
                "is_active": True,
            },
            sku=sku,
        )
        products[sku] = product

    incoterms = {}
    for code, name, description in INCOTERMS:
        incoterm, _ = get_or_create(db, Incoterm, {"name": name, "description": description}, code=code)
        incoterms[code] = incoterm

    concepts = {}
    for code, name, calc_type, category, rate in COST_CONCEPTS:
        concept, _ = get_or_create(
            db,
            CostConcept,
            {
                "name": name,
                "calculation_type": calc_type,
                "category": category,
                "default_rate": Decimal(rate),
                "is_active": True,
            },
            code=code,
        )
        concepts[code] = concept

    document_types = {}
    for code, name, applies_to, required, requires_expiry in DOCUMENT_TYPES:
        doc_type, _ = get_or_create(
            db,
            DocumentType,
            {
                "name": name,
                "applies_to": applies_to,
                "is_required": required,
                "requires_expiry": requires_expiry,
            },
            code=code,
        )
        document_types[code] = doc_type

    carriers = {}
    for code, name, carrier_type, contact in CARRIERS:
        carrier, _ = get_or_create(
            db,
            Carrier,
            {"name": name, "carrier_type": carrier_type, "contact": contact, "is_active": True},
            code=code,
        )
        carriers[code] = carrier

    companies = {}
    for name, tax_id, email, phone, address, iso in COMPANIES:
        company, _ = get_or_create(
            db,
            Company,
            {
                "tax_id": tax_id,
                "email": email,
                "phone": phone,
                "address": address,
                "country_id": countries[iso].id,
                "is_active": True,
            },
            name=name,
        )
        companies[name] = company

    db.commit()
    return {
        "countries": countries,
        "ports": ports,
        "currencies": currencies,
        "categories": categories,
        "products": products,
        "incoterms": incoterms,
        "concepts": concepts,
        "document_types": document_types,
        "carriers": carriers,
        "companies": companies,
    }


def seed_users(db, data: dict) -> dict:
    users = {}
    company_by_name = data["companies"]
    for username, role, person_type, full_name, cedula, ruc, razon_social in DEMO_USERS:
        company_id = None
        if razon_social and razon_social in company_by_name:
            company_id = company_by_name[razon_social].id
        user, created = get_or_create(
            db,
            User,
            {
                "password_hash": hash_password(DEMO_PASSWORD),
                "role": role,
                "person_type": person_type,
                "full_name": full_name,
                "cedula": cedula,
                "ruc": ruc,
                "razon_social": razon_social,
                "company_id": company_id,
                "is_active": True,
            },
            username=username,
        )
        if created:
            print(f"Usuario demo creado: {username} / {DEMO_PASSWORD}")
        users[username] = user
    db.commit()
    return users


def add_operation(
    db,
    *,
    data: dict,
    users: dict,
    type_: str,
    company_name: str,
    username: str,
    status: str,
    incoterm_code: str,
    origin_code: str,
    destination_code: str,
    items: list[tuple[str, str, str]],
    days_ago: int,
    notes: str,
) -> Operation:
    operation = Operation(
        code="TEMP",
        user_id=users[username].id,
        company_id=data["companies"][company_name].id,
        type=type_,
        status=status,
        operation_date=date.today() - timedelta(days=days_ago),
        origin_port_id=data["ports"][origin_code].id,
        destination_port_id=data["ports"][destination_code].id,
        currency_id=data["currencies"]["USD"].id,
        incoterm_id=data["incoterms"][incoterm_code].id,
        notes=notes,
    )
    db.add(operation)
    db.flush()
    operation.code = f"OP-{operation.operation_date.year}-{operation.id:04d}"

    for sku, quantity, unit_price in items:
        product = data["products"][sku]
        qty = Decimal(quantity)
        price = Decimal(unit_price)
        operation.items.append(
            OperationItem(
                product_id=product.id,
                quantity=qty,
                unit_price=price,
                subtotal=money(qty * price),
            )
        )

    created = datetime.now() - timedelta(days=days_ago)
    operation.created_at = created
    operation.updated_at = created + timedelta(days=max(days_ago - 2, 0))
    db.add(
        OperationStatusHistory(
            operation_id=operation.id,
            from_status=None,
            to_status=STATUS_PENDING,
            changed_by_id=users["carlos.import"].id,
            note="Operación creada",
            created_at=created,
        )
    )
    if status != STATUS_PENDING:
        db.add(
            OperationStatusHistory(
                operation_id=operation.id,
                from_status=STATUS_PENDING,
                to_status=status,
                changed_by_id=users["carlos.import"].id,
                note="Avance de la operación",
                created_at=created + timedelta(days=2),
            )
        )
    db.flush()
    return operation


def add_scenario(db, operation: Operation, data: dict, name: str, lines: list[tuple], selected: bool = False) -> CostScenario:
    scenario = CostScenario(
        operation_id=operation.id,
        name=name,
        description="Escenario demo generado por el seed",
        is_selected=selected,
    )
    db.add(scenario)
    db.flush()
    for order, (concept_code, calc_type, rate, quantity, base) in enumerate(lines):
        concept = data["concepts"][concept_code]
        base_amount = Decimal(str(base))
        quantity_value = Decimal(str(quantity))
        rate_value = Decimal(str(rate))
        amount = CostCalculatorFactory.get(calc_type).calculate(
            base=base_amount, quantity=quantity_value, rate=rate_value
        )
        db.add(
            CostScenarioItem(
                scenario_id=scenario.id,
                concept_id=concept.id,
                description=concept.name,
                calculation_type=calc_type,
                rate=rate_value,
                quantity=quantity_value,
                base_amount=base_amount,
                amount=amount,
                sort_order=order,
            )
        )
    db.flush()
    return scenario


def add_document(
    db,
    operation: Operation,
    data: dict,
    code: str,
    status: str,
    *,
    issue_days_ago: int | None = None,
    expiry_days: int | None = None,
    uploaded_by: int | None = None,
) -> Document:
    doc_type = data["document_types"][code]
    document = Document(
        operation_id=operation.id,
        document_type_id=doc_type.id,
        name=f"{doc_type.name} · {operation.code}",
        status=status,
        file_url=f"https://docs.tradelab.example/{operation.code.lower()}/{code.lower()}.pdf",
        issue_date=date.today() - timedelta(days=issue_days_ago) if issue_days_ago is not None else None,
        expiry_date=date.today() + timedelta(days=expiry_days) if expiry_days is not None else None,
        notes="Documento de demostración",
        uploaded_by_id=uploaded_by,
    )
    db.add(document)
    db.flush()
    return document


def add_invoice(db, operation: Operation, data: dict, *, issue_days_ago: int, due_days: int, paid_ratio: str, status: str) -> Invoice:
    subtotal = operation.product_subtotal
    tax = money(subtotal * Decimal("0.15"))
    total = money(subtotal + tax)
    invoice = Invoice(
        operation_id=operation.id,
        currency_id=operation.currency_id,
        number=f"INV-{operation.operation_date.year}-{operation.id:04d}",
        issue_date=date.today() - timedelta(days=issue_days_ago),
        due_date=date.today() + timedelta(days=due_days),
        subtotal=subtotal,
        tax_amount=tax,
        total=total,
        status=status,
        notes="Factura de demostración",
    )
    db.add(invoice)
    db.flush()
    paid = money(total * Decimal(paid_ratio))
    if paid > 0:
        db.add(
            Payment(
                invoice_id=invoice.id,
                amount=paid,
                payment_date=date.today() - timedelta(days=max(issue_days_ago - 5, 0)),
                method="TRANSFER",
                reference=f"TRX-{invoice.id:05d}",
                notes="Pago parcial demo" if paid < total else "Pago total demo",
            )
        )
    db.flush()
    if paid >= total:
        invoice.status = INVOICE_PAID
    elif invoice.due_date and invoice.due_date < date.today() and invoice.balance > 0:
        invoice.status = INVOICE_OVERDUE
    db.flush()
    return invoice


def seed_demo_operations(db, data: dict, users: dict) -> None:
    if os.getenv("SEED_DEMO", "1") == "0":
        print("SEED_DEMO=0: no se crean operaciones demo.")
        return
    marker = (
        db.query(AuditLog)
        .filter(AuditLog.action == "SEED", AuditLog.entity == "demo_data")
        .first()
    )
    if marker is not None:
        print("Los datos demo ya fueron creados; no se duplican.")
        return
    if db.query(Operation).count() > 0:
        print("Se conservan las operaciones existentes y se agregan las operaciones demo.")

    today = date.today()

    op1 = add_operation(
        db,
        data=data,
        users=users,
        type_=OPERATION_IMPORT,
        company_name="Global Tech Import S.A.",
        username="carlos.import",
        status=STATUS_IN_PROGRESS,
        incoterm_code="FOB",
        origin_code="CNSHA",
        destination_code="ECGYE",
        items=[("ELE-001", "25", "720"), ("ELE-002", "40", "185"), ("ELE-003", "60", "22")],
        days_ago=20,
        notes="Importación de equipos de cómputo para renovación de oficinas.",
    )
    add_scenario(
        db, op1, data, "Marítimo FOB",
        [
            ("PRODUCTO", CALC_FIXED, op1.product_subtotal, 1, op1.product_subtotal),
            ("FLETE_MAR", CALC_FIXED, 1850, 1, 0),
            ("SEGURO", CALC_PERCENTAGE, "1.5", 1, op1.product_subtotal),
            ("CARGOS_ORIGEN", CALC_FIXED, 220, 1, 0),
            ("CARGOS_DESTINO", CALC_FIXED, 280, 1, 0),
            ("AGENTE_ADUANA", CALC_FIXED, 180, 1, 0),
        ],
        selected=True,
    )
    add_scenario(
        db, op1, data, "Aéreo DAP",
        [
            ("PRODUCTO", CALC_FIXED, op1.product_subtotal, 1, op1.product_subtotal),
            ("FLETE_AER", CALC_FIXED, 4200, 1, 0),
            ("SEGURO", CALC_PERCENTAGE, "2.2", 1, op1.product_subtotal),
            ("CARGOS_ORIGEN", CALC_FIXED, 150, 1, 0),
            ("TRANSPORTE_INTERNO", CALC_PER_UNIT, 22, 65, 0),
            ("AGENTE_ADUANA", CALC_FIXED, 180, 1, 0),
        ],
    )
    add_document(db, op1, data, "FACTURA_COM", DOC_APPROVED, issue_days_ago=22, uploaded_by=users["carlos.import"].id)
    add_document(db, op1, data, "PACKING", DOC_APPROVED, issue_days_ago=22, uploaded_by=users["carlos.import"].id)
    add_document(db, op1, data, "BL", DOC_RECEIVED, issue_days_ago=10, uploaded_by=users["carlos.import"].id)
    add_document(db, op1, data, "POLIZA", DOC_APPROVED, issue_days_ago=18, expiry_days=12, uploaded_by=users["carlos.import"].id)
    add_document(db, op1, data, "CERT_ORIGEN", DOC_PENDING, issue_days_ago=5, expiry_days=60, uploaded_by=users["carlos.import"].id)
    db.add(
        Shipment(
            operation_id=op1.id,
            carrier_id=data["carriers"]["MAERSK"].id,
            tracking_number="MAEU-784512369",
            origin_port_id=op1.origin_port_id,
            destination_port_id=op1.destination_port_id,
            departure_date=today - timedelta(days=8),
            estimated_arrival=today + timedelta(days=9),
            status="IN_TRANSIT",
            notes="Contenedor 40 HC",
        )
    )
    add_invoice(db, op1, data, issue_days_ago=30, due_days=-6, paid_ratio="0.35", status=INVOICE_OVERDUE)

    op2 = add_operation(
        db,
        data=data,
        users=users,
        type_=OPERATION_EXPORT,
        company_name="AgroExport Ecuador S.A.",
        username="agro.export",
        status=STATUS_SHIPPED,
        incoterm_code="FOB",
        origin_code="ECGYE",
        destination_code="USMIA",
        items=[("ALI-001", "1200", "6.50"), ("ALI-002", "80", "145")],
        days_ago=16,
        notes="Exportación de banano y cacao certificado.",
    )
    add_scenario(
        db, op2, data, "Marítimo FOB",
        [
            ("PRODUCTO", CALC_FIXED, op2.product_subtotal, 1, op2.product_subtotal),
            ("FLETE_MAR", CALC_FIXED, 2400, 1, 0),
            ("SEGURO", CALC_PERCENTAGE, "1.2", 1, op2.product_subtotal),
            ("CARGOS_ORIGEN", CALC_FIXED, 190, 1, 0),
            ("IMPUESTO_SALIDA", CALC_PERCENTAGE, "0.5", 1, op2.product_subtotal),
        ],
        selected=True,
    )
    add_document(db, op2, data, "FACTURA_COM", DOC_APPROVED, issue_days_ago=15, uploaded_by=users["agro.export"].id)
    add_document(db, op2, data, "PACKING", DOC_APPROVED, issue_days_ago=15, uploaded_by=users["agro.export"].id)
    add_document(db, op2, data, "BL", DOC_APPROVED, issue_days_ago=12, uploaded_by=users["agro.export"].id)
    add_document(db, op2, data, "DAE", DOC_APPROVED, issue_days_ago=14, uploaded_by=users["agro.export"].id)
    add_document(db, op2, data, "FITO", DOC_APPROVED, issue_days_ago=14, expiry_days=20, uploaded_by=users["agro.export"].id)
    add_document(db, op2, data, "CERT_ORIGEN", DOC_RECEIVED, issue_days_ago=13, expiry_days=90, uploaded_by=users["agro.export"].id)
    db.add(
        Shipment(
            operation_id=op2.id,
            carrier_id=data["carriers"]["MSC"].id,
            tracking_number="MSCU-99231457",
            origin_port_id=op2.origin_port_id,
            destination_port_id=op2.destination_port_id,
            departure_date=today - timedelta(days=12),
            estimated_arrival=today - timedelta(days=2),
            status="IN_TRANSIT",
            notes="Llegada estimada incumplida: revisar con la naviera.",
        )
    )
    add_invoice(db, op2, data, issue_days_ago=15, due_days=15, paid_ratio="0.5", status="PARTIAL")

    op3 = add_operation(
        db,
        data=data,
        users=users,
        type_=OPERATION_IMPORT,
        company_name="Importadora Andina S.A.",
        username="alfredo1",
        status=STATUS_PENDING,
        incoterm_code="CIF",
        origin_code="USMIA",
        destination_code="ECUIO",
        items=[("MED-001", "300", "12"), ("MED-002", "500", "9.50")],
        days_ago=18,
        notes="Compra de insumos médicos. Pendiente de permisos y pago inicial.",
    )
    add_scenario(
        db, op3, data, "Aéreo CIF",
        [
            ("PRODUCTO", CALC_FIXED, op3.product_subtotal, 1, op3.product_subtotal),
            ("FLETE_AER", CALC_FIXED, 1600, 1, 0),
            ("SEGURO", CALC_PERCENTAGE, "1.8", 1, op3.product_subtotal),
            ("CARGOS_DESTINO", CALC_FIXED, 210, 1, 0),
        ],
        selected=True,
    )
    add_document(db, op3, data, "FACTURA_COM", DOC_RECEIVED, issue_days_ago=17, uploaded_by=users["alfredo1"].id)
    add_document(db, op3, data, "PERMISO_IMP", DOC_PENDING, issue_days_ago=10, expiry_days=-3, uploaded_by=users["alfredo1"].id)
    add_invoice(db, op3, data, issue_days_ago=25, due_days=-12, paid_ratio="0", status=INVOICE_OVERDUE)
    op3.updated_at = datetime.now() - timedelta(days=14)

    op4 = add_operation(
        db,
        data=data,
        users=users,
        type_=OPERATION_EXPORT,
        company_name="Textiles del Pacífico Cía. Ltda.",
        username="maria.export",
        status=STATUS_DONE,
        incoterm_code="CFR",
        origin_code="ECGYE",
        destination_code="ESVLC",
        items=[("TEX-001", "900", "8.50"), ("TEX-002", "400", "18"), ("TEX-003", "250", "3.20")],
        days_ago=60,
        notes="Primer embarque del año a Europa. Operación cerrada.",
    )
    add_scenario(
        db, op4, data, "Marítimo CFR",
        [
            ("PRODUCTO", CALC_FIXED, op4.product_subtotal, 1, op4.product_subtotal),
            ("FLETE_MAR", CALC_FIXED, 2100, 1, 0),
            ("SEGURO", CALC_PERCENTAGE, "1.1", 1, op4.product_subtotal),
            ("CARGOS_ORIGEN", CALC_FIXED, 175, 1, 0),
        ],
        selected=True,
    )
    for code in ("FACTURA_COM", "PACKING", "BL", "DAE", "CERT_ORIGEN"):
        add_document(db, op4, data, code, DOC_APPROVED, issue_days_ago=58, expiry_days=120, uploaded_by=users["maria.export"].id)
    db.add(
        Shipment(
            operation_id=op4.id,
            carrier_id=data["carriers"]["HAPAG"].id,
            tracking_number="HLCU-3388771",
            origin_port_id=op4.origin_port_id,
            destination_port_id=op4.destination_port_id,
            departure_date=today - timedelta(days=52),
            estimated_arrival=today - timedelta(days=24),
            actual_arrival=today - timedelta(days=23),
            status="DELIVERED",
        )
    )
    add_invoice(db, op4, data, issue_days_ago=58, due_days=30, paid_ratio="1", status=INVOICE_PAID)

    op5 = add_operation(
        db,
        data=data,
        users=users,
        type_=OPERATION_IMPORT,
        company_name="Ferretería Central",
        username="pepito",
        status=STATUS_IN_PROGRESS,
        incoterm_code="DAP",
        origin_code="COBOG",
        destination_code="ECUIO",
        items=[("MAQ-001", "6", "1850"), ("MAQ-002", "14", "420"), ("AUT-001", "120", "14")],
        days_ago=9,
        notes="Importación de maquinaria y repuestos desde Colombia.",
    )
    add_scenario(
        db, op5, data, "Aéreo DAP",
        [
            ("PRODUCTO", CALC_FIXED, op5.product_subtotal, 1, op5.product_subtotal),
            ("FLETE_AER", CALC_FIXED, 3100, 1, 0),
            ("SEGURO", CALC_PERCENTAGE, "1.9", 1, op5.product_subtotal),
            ("TRANSPORTE_INTERNO", CALC_PER_UNIT, 15, 140, 0),
            ("AGENTE_ADUANA", CALC_FIXED, 220, 1, 0),
        ],
    )
    add_scenario(
        db, op5, data, "Terrestre DAP",
        [
            ("PRODUCTO", CALC_FIXED, op5.product_subtotal, 1, op5.product_subtotal),
            ("FLETE_MAR", CALC_FIXED, 1250, 1, 0),
            ("SEGURO", CALC_PERCENTAGE, "1.2", 1, op5.product_subtotal),
            ("TRANSPORTE_INTERNO", CALC_PER_UNIT, 9, 140, 0),
            ("CARGOS_DESTINO", CALC_FIXED, 160, 1, 0),
        ],
        selected=True,
    )
    add_document(db, op5, data, "FACTURA_COM", DOC_APPROVED, issue_days_ago=8, uploaded_by=users["pepito"].id)
    add_document(db, op5, data, "PACKING", DOC_RECEIVED, issue_days_ago=8, uploaded_by=users["pepito"].id)
    add_invoice(db, op5, data, issue_days_ago=8, due_days=22, paid_ratio="0", status="ISSUED")

    db.commit()
    db.add(
        AuditLog(
            user_id=None,
            action="SEED",
            entity="demo_data",
            entity_id=None,
            detail="Operaciones, escenarios, documentos, embarques y facturas de demostración.",
        )
    )
    db.commit()
    print("Operaciones demo creadas: 5")


def generate_alerts(db) -> None:
    from app.repositories import (
        SqlAlchemyAlertRepository,
        SqlAlchemyBillingRepository,
        SqlAlchemyDocumentRepository,
        SqlAlchemyLogisticsRepository,
        SqlAlchemyOperationRepository,
    )
    from app.repositories.protocols import InvoiceFilters
    from app.services.alert_service import AlertService

    service = AlertService(
        repository=SqlAlchemyAlertRepository(db),
        operations=SqlAlchemyOperationRepository(db),
        documents=SqlAlchemyDocumentRepository(db),
        billing=SqlAlchemyBillingRepository(db),
        logistics=SqlAlchemyLogisticsRepository(db),
    )
    generated = service.generate_all()
    print(f"Alertas evaluadas: {generated}")


def main() -> None:
    init_database()
    db = SessionLocal()
    try:
        create_admin(db)
        data = seed_catalogs(db)
        users = seed_users(db, data)
        seed_demo_operations(db, data, users)
        generate_alerts(db)
        print("Seed de International Trade completado.")
        print(f"Catálogos: {len(data['products'])} productos, {len(data['ports'])} puertos, {len(data['concepts'])} conceptos de costo.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

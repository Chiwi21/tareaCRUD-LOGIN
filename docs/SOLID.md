# Principios SOLID en TradeLab

TradeLab separa las rutas HTTP, las reglas de negocio, el acceso a datos y las
plantillas. Los cinco principios SOLID se aplican en el código de producción y
tienen pruebas en `tests/test_solid.py` y `tests/test_flows.py`.

## Resumen

| Principio | Dónde se aplica | Archivo principal |
|---|---|---|
| **S**RP | Rutas delgadas, servicios de negocio, repositorios y esquemas separados | `app/routers/`, `app/services/`, `app/repositories/`, `app/schemas/` |
| **O**CP | Estrategias de cálculo de costos y fábrica extensible | `app/core/costing.py` |
| **L**SP | `FixedCostCalculator`, `PercentageCostCalculator`, `PerUnitCostCalculator` son intercambiables | `app/core/costing.py` |
| **I**SP | `OperationReader` / `OperationWriter` y repositorios pequeños por dominio | `app/repositories/protocols.py` |
| **D**IP | Servicios que dependen de `Protocol` y se conectan con `Depends` | `app/services/`, `app/dependencies.py` |

## SRP — Responsabilidad única

Cada capa tiene una razón de cambio distinta:

- `app/routers/*.py`: reciben la petición, validan formularios, eligen la
  plantilla o respuesta HTTP y redirigen. No contienen consultas SQL ni reglas
  de negocio.
- `app/services/*.py`: validan reglas del dominio (por ejemplo, que un pago no
  supere el saldo o que una operación no salte de `PENDING` a `DONE`).
- `app/repositories/*.py`: consultan y persisten con SQLAlchemy.
- `app/schemas/*.py`: validan la forma de los datos de entrada y salida.
- `app/templates/` y `app/static/`: presentación.

Ejemplo: crear una operación.

```python
# app/routers/operations.py
operation = service.create(data, user.id)
```

```python
# app/services/operation_service.py
def create(self, data: OperationCreate, actor_id: int | None) -> tuple:
    errors = self.validate(data)
    if errors:
        raise ValidationError(errors)
    operation = self.writer.create(data, actor_id)
    self.audit.log(actor_id, "CREATE", "operations", operation.id, ...)
    return operation
```

El router no sabe cómo se genera el código `OP-2026-0001`; el servicio no sabe
cómo se guarda en SQLite o PostgreSQL. La prueba
`test_srp_service_delegates_persistence_and_audit` demuestra que el servicio
delega la persistencia y la auditoría en colaboradores separados.

## OCP — Abierto/cerrado

Los tipos de cálculo de costo son estrategias. Para agregar un cálculo nuevo no
se modifica el servicio ni las clases existentes: se crea otra subclase y se
registra en la fábrica.

```python
# app/core/costing.py
class CostCalculator(ABC):
    @abstractmethod
    def calculate(self, *, base: Decimal, quantity: Decimal, rate: Decimal) -> Decimal:
        ...

class FixedCostCalculator(CostCalculator):
    def calculate(self, *, base, quantity, rate):
        return money(rate)

class PercentageCostCalculator(CostCalculator):
    def calculate(self, *, base, quantity, rate):
        return money(base * rate / Decimal("100"))

class PerUnitCostCalculator(CostCalculator):
    def calculate(self, *, base, quantity, rate):
        return money(quantity * rate)

class CostCalculatorFactory:
    _calculators = {
        "FIXED": FixedCostCalculator(),
        "PERCENTAGE": PercentageCostCalculator(),
        "PER_UNIT": PerUnitCostCalculator(),
    }

    @classmethod
    def get(cls, calculation_type: str) -> CostCalculator:
        return cls._calculators.get(calculation_type, cls._calculators["FIXED"])

    @classmethod
    def register(cls, calculation_type: str, calculator: CostCalculator) -> None:
        cls._calculators[calculation_type] = calculator
```

Extensión sin tocar lo existente:

```python
class StaggeredCostCalculator(CostCalculator):
    def calculate(self, *, base, quantity, rate):
        return money(base * rate / Decimal("100"))

CostCalculatorFactory.register("STAGGERED", StaggeredCostCalculator())
```

La prueba `test_ocp_register_new_strategy_without_modifying_existing_ones`
registra una estrategia nueva y verifica que la fábrica la devuelve.

## LSP — Sustitución de Liskov

Todas las estrategias respetan el mismo contrato: reciben `base`, `quantity` y
`rate` por nombre, y devuelven un `Decimal` con dos decimales. Cualquier
estrategia puede reemplazar a otra sin que `CostService` cambie.

```python
# app/services/cost_service.py
def calculate_amount(self, calculation_type, base, quantity, rate):
    calculator = CostCalculatorFactory.get(calculation_type)
    return calculator.calculate(base=base, quantity=quantity, rate=rate)
```

`test_lsp_all_strategies_are_interchangeable` recorre las tres estrategias y
comprueba que todas pueden usarse con la misma llamada. Si una subclase
devolviera un tipo distinto o ignorara la firma, la prueba fallaría.

## ISP — Segregación de interfaces

Las interfaces son pequeñas y por dominio. En operaciones se separa lectura y
escritura:

```python
# app/repositories/protocols.py
class OperationReader(Protocol):
    def list(self, filters: OperationFilters | None = None) -> Sequence[Operation]: ...
    def get(self, operation_id: int) -> Operation | None: ...
    def list_assignable_users(self) -> Sequence[User]: ...
    # ...

class OperationWriter(Protocol):
    def create(self, data: OperationCreate, changed_by_id: int | None = None) -> Operation: ...
    def update(self, operation_id: int, data: OperationUpdate, changed_by_id: int | None = None) -> Operation: ...
    def delete(self, operation_id: int) -> None: ...
    def add_item(self, operation_id: int, data: OperationItemCreate) -> OperationItem: ...
    # ...
```

El servicio recibe ambas porque necesita leer y escribir, pero otros
colaboradores pueden recibir solo la que usan. Por ejemplo,
`DocumentService` recibe `OperationReader` para consultar la operación, no un
repositorio completo de operaciones.

```python
# app/dependencies.py
def get_operation_repository(db: Session = Depends(get_db)) -> SqlAlchemyOperationRepository:
    return SqlAlchemyOperationRepository(db)

def get_operation_reader(
    repository: SqlAlchemyOperationRepository = Depends(get_operation_repository),
) -> OperationReader:
    return repository
```

La prueba `test_reader_and_writer_contracts_do_not_overlap` verifica que los
métodos de lectura y escritura no se mezclan. La prueba
`test_service_accepts_separate_read_and_write_implementations` construye el
servicio con dos objetos distintos.

## DIP — Inversión de dependencias

Los servicios dependen de abstracciones (`Protocol`), no de SQLAlchemy. Las
implementaciones concretas se inyectan en `app/dependencies.py` con
`Depends`.

```python
# app/services/operation_service.py
class OperationService:
    def __init__(
        self,
        reader: OperationReader,
        writer: OperationWriter,
        audit: AuditService,
    ):
        self.reader = reader
        self.writer = writer
        self.audit = audit
```

```python
# app/dependencies.py
def get_operation_service(
    reader: OperationReader = Depends(get_operation_reader),
    writer: OperationWriter = Depends(get_operation_writer),
    audit: AuditService = Depends(get_audit_service),
) -> OperationService:
    return OperationService(reader, writer, audit)
```

En producción, `get_operation_reader` y `get_operation_writer` devuelven
`SqlAlchemyOperationRepository`. En pruebas se reemplazan con
`app.dependency_overrides`:

```python
# tests/test_solid.py
test_app.dependency_overrides[require_login] = lambda: SimpleNamespace(id=1, role="ADMIN")
test_app.dependency_overrides[get_operation_service] = lambda: FakeOperationService()

response = TestClient(test_app).get("/api/operations")
assert response.json() == []
```

La prueba `test_dip_service_depends_on_protocols_not_sqlalchemy` comprueba que
el servicio no tiene una sesión de base de datos y que usa los objetos
inyectados. La prueba de integración usa una base SQLite temporal y
`dependency_overrides[get_db]`, sin tocar `data/app.db`.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas de integración requieren `httpx2` (dependencia de desarrollo):

```bash
pip install -r requirements-dev.txt
```

Resultado esperado:

- `tests/test_cedula.py`: validación de cédula ecuatoriana.
- `tests/test_flows.py`: CRUD de catálogos, usuarios, operaciones, escenarios,
  documentos, embarques, facturas, pagos, alertas y permisos.
- `tests/test_solid.py`: SRP, OCP, LSP, ISP y DIP.

## Dónde mirar cada principio en el código

- SRP: compare `app/routers/operations.py` (HTTP) con
  `app/services/operation_service.py` (reglas) y
  `app/repositories/operation_repository.py` (persistencia).
- OCP: `app/core/costing.py` y `CostCalculatorFactory.register`.
- LSP: `app/core/costing.py` y `tests/test_solid.py`.
- ISP: `OperationReader`, `OperationWriter`, `DocumentRepository`,
  `BillingRepository` en `app/repositories/protocols.py`.
- DIP: `app/dependencies.py`, `app/services/operation_service.py` y
  `tests/test_solid.py`.

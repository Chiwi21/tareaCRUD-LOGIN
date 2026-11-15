# TradeLab — Planificación de comercio exterior

TradeLab es una aplicación web para planificar, comparar y dar seguimiento a
operaciones de **importación y exportación**. Centraliza la operación, sus
productos, los escenarios de costo, la documentación, los embarques, la
facturación y las alertas operativas en un solo flujo de trabajo.

Proyecto desarrollado para la materia **Ingeniería Web**. Evoluciona el CRUD y
el login de la Tarea 3 hacia un sistema con 22 tablas, arquitectura por capas y
principios **SOLID** en FastAPI.

---

## Tabla de contenidos

- [Características](#características)
- [Módulos](#módulos)
- [Roles y permisos](#roles-y-permisos)
- [Escenarios de costo](#escenarios-de-costo)
- [Alertas operativas](#alertas-operativas)
- [Base de datos](#base-de-datos)
- [Arquitectura y SOLID](#arquitectura-y-solid)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación local](#instalación-local)
- [Variables de entorno](#variables-de-entorno)
- [Migración desde la Tarea 3](#migración-desde-la-tarea-3)
- [Datos de demostración](#datos-de-demostración)
- [Pruebas](#pruebas)
- [API REST](#api-rest)
- [Despliegue en Render + Neon](#despliegue-en-render--neon)
- [Alcance y limitaciones](#alcance-y-limitaciones)
- [Autor](#autor)

---

## Características

- **Autenticación con sesiones firmadas** y contraseñas almacenadas con
  **bcrypt**.
- **Tres roles**: administrador, importador y exportador.
- **Registro público** solo para importadores y exportadores, con validación
  backend de **cédula ecuatoriana** (módulo 10) y RUC para personas jurídicas.
- **Operaciones de importación/exportación** con ítems, puertos, moneda,
  incoterm, empresa, responsable y flujo de estados controlado.
- **Escenarios de costo configurables** con cálculos fijos, porcentuales y por
  unidad; comparación lado a lado y selección del escenario ganador.
- **Gestión documental** con checklist por tipo de documento, estados,
  vencimientos y enlaces al archivo.
- **Embarques** con transportista, tracking, puertos, fechas y estado.
- **Facturación y pagos** con cálculo automático de saldo y estado
  (`ISSUED`, `PARTIAL`, `PAID`, `OVERDUE`).
- **Alertas automáticas** por operaciones estancadas, documentos faltantes o
  por vencer, facturas vencidas y embarques retrasados.
- **Dashboard** con indicadores, operaciones recientes, productos principales,
  próximos embarques y alertas abiertas.
- **Auditoría** de las acciones sobre operaciones, documentos, facturas,
  usuarios y catálogos.
- **Catálogos maestros** administrables desde la interfaz.
- **API REST** con los mismos permisos que las vistas HTML.
- **SQLite** en desarrollo y **PostgreSQL (Neon)** en producción, sin cambiar
  el código.

## Módulos

| Módulo | Rutas principales | Qué resuelve |
|---|---|---|
| Panel | `/dashboard` | Resumen de operaciones, montos, productos, embarques y alertas |
| Operaciones | `/operations` | CRUD, ítems, responsables, puertos, incoterm y cambios de estado |
| Costos | `/operations/{id}` | Escenarios, líneas de costo, comparación y ahorro potencial |
| Documentos | `/documents` | Checklist documental, estados y fechas de vencimiento |
| Embarques | `/shipments` | Transportista, tracking, ruta, fechas y estado logístico |
| Facturación | `/invoices` | Facturas, impuestos, pagos, saldo y estado de cobro |
| Alertas | `/alerts` | Generación por reglas, severidad y resolución |
| Catálogos | `/catalogs` | 10 catálogos maestros con CRUD y búsqueda |
| Usuarios | `/admin/users` | Alta, edición, detalle y baja controlada de usuarios |
| Auditoría | `/admin/audit` | Trazabilidad de acciones con filtros |
| API REST | `/api/*` | Operaciones, documentos, facturas, alertas, catálogos y usuarios |

## Roles y permisos

| Rol | Acceso |
|---|---|
| `ADMIN` | Todos los módulos, catálogos, usuarios, auditoría y CRUD completo |
| `IMPORTER` | Panel, listado y detalle de **sus propias** operaciones |
| `EXPORTER` | Panel, listado y detalle de **sus propias** operaciones |

Reglas de protección:

- Vistas HTML sin sesión → redirección a `/login`.
- Endpoints REST sin sesión → `401 Unauthorized`.
- Rutas administrativas con rol distinto de `ADMIN` → `403 Forbidden`.
- Un importador/exportador no puede abrir una operación ajena aunque conozca el
  identificador.
- La cuenta administrador creada por el seed no puede registrarse públicamente
  ni eliminarse desde la interfaz.

## Escenarios de costo

Cada operación puede tener varios escenarios (por ejemplo, **Marítimo FOB** y
**Aéreo DAP**). Cada escenario agrupa líneas de costo por categoría:

- Producto
- Flete
- Seguro
- Cargos
- Otros

Tipos de cálculo disponibles:

| Tipo | Fórmula | Uso típico |
|---|---|---|
| `FIXED` | `rate` | Flete contratado, agente de aduana |
| `PERCENTAGE` | `base × rate / 100` | Seguro sobre el valor de la mercancía |
| `PER_UNIT` | `quantity × rate` | Transporte interno por caja o unidad |

El servicio calcula el total del escenario, permite marcar uno como
seleccionado y muestra el **ahorro potencial** entre el escenario más caro y el
más económico. Los cálculos viven en `app/core/costing.py` como estrategias
intercambiables.

## Alertas operativas

Las reglas se ejecutan con `POST /alerts/generate` o
`POST /api/alerts/generate`:

| Tipo | Condición | Severidad |
|---|---|---|
| `STALLED_OPERATION` | Operación sin cambios por más de 7 días | Advertencia |
| `MISSING_DOCUMENT` | Documento requerido no registrado o no aprobado | Advertencia |
| `EXPIRING_DOCUMENT` | Documento vence en ≤ 30 días o ya venció | Advertencia / Crítica |
| `OVERDUE_INVOICE` | Factura con saldo y fecha de vencimiento pasada | Crítica |
| `DELAYED_SHIPMENT` | Llegada estimada superada sin entrega | Crítica |

Las alertas se identifican por una huella (`fingerprint`) para no duplicarse en
cada ejecución. Al resolverse conservan la fecha y el usuario que las atendió.

## Base de datos

**22 tablas** agrupadas por dominio:

| Dominio | Tablas |
|---|---|
| Seguridad y organización | `users`, `companies`, `audit_logs` |
| Catálogos | `countries`, `ports`, `currencies`, `categories`, `products`, `incoterms`, `cost_concepts`, `document_types`, `carriers` |
| Operación | `operations`, `operation_items`, `operation_status_history` |
| Costos | `cost_scenarios`, `cost_scenario_items` |
| Logística | `shipments` |
| Documentos | `documents` |
| Facturación | `invoices`, `payments` |
| Alertas | `alerts` |

El esquema se crea automáticamente con SQLAlchemy al iniciar la aplicación. Las
relaciones usan claves foráneas y borrados controlados (`RESTRICT`,
`SET NULL`, `CASCADE` según el caso).

## Arquitectura y SOLID

TradeLab aplica separación por capas y los cinco principios SOLID. El detalle
con ejemplos y referencias está en **[`docs/SOLID.md`](docs/SOLID.md)**.

| Principio | Implementación |
|---|---|
| **SRP** | Routers HTTP, servicios de negocio, repositorios y esquemas Pydantic separados |
| **OCP** | Nuevas estrategias de costo se registran en `CostCalculatorFactory` sin modificar las existentes |
| **LSP** | `FixedCostCalculator`, `PercentageCostCalculator` y `PerUnitCostCalculator` son intercambiables |
| **ISP** | Protocolos pequeños por dominio; `OperationReader` y `OperationWriter` separados |
| **DIP** | Servicios que reciben `Protocol` y se conectan con `Depends()` en `app/dependencies.py` |

Flujo de una petición:

```
Router (HTTP) → Service (reglas) → Repository (SQLAlchemy) → Base de datos
                      ↑
                 Protocol (ISP/DIP)
```

## Estructura del proyecto

```
tarea3-crud-login/
├── app/
│   ├── main.py                 # App FastAPI, sesiones, routers y errores
│   ├── config.py               # SECRET_KEY y configuración de sesión
│   ├── constants.py            # Roles, estados, categorías y tipos
│   ├── database.py             # Motor SQLite/PostgreSQL y sesión
│   ├── dependencies.py         # Proveedores concretos para Depends()
│   ├── catalog_specs.py        # Definición declarativa de catálogos
│   ├── security.py             # bcrypt y guards de autenticación
│   ├── user_validation.py      # Cédula, RUC, contraseñas y duplicados
│   ├── core/
│   │   └── costing.py          # Estrategias OCP/LSP y fábrica
│   ├── models/                 # 22 modelos SQLAlchemy
│   ├── schemas/                # Esquemas Pydantic de entrada/salida
│   ├── repositories/           # Protocolos y repositorios SQLAlchemy
│   ├── services/               # Reglas de negocio y auditoría
│   ├── routers/                # Vistas HTML y endpoints REST
│   ├── templates/              # Jinja2
│   └── static/                 # CSS y JavaScript
├── docs/
│   └── SOLID.md                # Explicación de los cinco principios
├── tests/
│   ├── test_cedula.py          # Validación de cédula ecuatoriana
│   ├── test_flows.py           # Integración HTML/API con SQLite temporal
│   └── test_solid.py           # SRP, OCP, LSP, ISP y DIP
├── migrate_legacy.py           # Migración desde el esquema de la Tarea 3
├── seed.py                     # Catálogos, usuarios y datos demo idempotentes
├── render.yaml                 # Blueprint de despliegue
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Instalación local

Requisitos: **Python 3.11+** (probado con 3.14) y `pip`.

```bash
git clone https://github.com/Chiwi21/tareaCRUD-LOGIN.git
cd tareaCRUD-LOGIN
python -m venv .venv
```

Activar el entorno:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source .venv/bin/activate
```

Instalar dependencias y preparar la base:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python seed.py
```

Ejecutar la aplicación:

```bash
uvicorn app.main:app --reload
```

Abrir:

- Aplicación: <http://127.0.0.1:8000>
- Documentación interactiva: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

En Windows, si `uvicorn` no se reconoce, usar
`.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.

## Variables de entorno

| Variable | Obligatoria | Valor por defecto | Descripción |
|---|---|---|---|
| `DATABASE_URL` | No | SQLite `data/app.db` | Cadena de PostgreSQL en producción |
| `SECRET_KEY` | Recomendada | Clave de desarrollo | Firma de la cookie de sesión |
| `ADMIN_USERNAME` | No | `admin` | Usuario administrador del seed |
| `ADMIN_PASSWORD` | Recomendada | `admin123` | Contraseña del administrador |
| `DEMO_PASSWORD` | No | `demo123` | Contraseña de los usuarios demo nuevos |
| `SEED_DEMO` | No | `1` | `0` evita crear operaciones de demostración |

`DATABASE_URL` acepta el formato de Neon
(`postgresql://usuario:clave@host/base?sslmode=require`); la aplicación lo
normaliza a `postgresql+psycopg://`.

## Migración desde la Tarea 3

El esquema anterior guardaba un solo producto por operación en columnas de
texto. `migrate_legacy.py`:

1. Detecta si `operations` tiene las columnas antiguas (`product` sin `code`).
2. Conserva **usuarios** y **operaciones** existentes.
3. Crea un producto legado por cada nombre de producto.
4. Convierte cada operación en una operación TradeLab con su ítem e historial.
5. Deja el resto de módulos listos para el seed.

```bash
python migrate_legacy.py
python seed.py
```

Es idempotente: si la base ya tiene el esquema nuevo, no borra ni duplica nada.
Si se ejecuta la aplicación contra una base antigua sin migrar, `init_database`
detiene el arranque con un mensaje que indica ejecutar la migración.

> **Importante:** no se debe resetear Neon ni borrar `data/app.db` para
> "arreglar" el esquema. Ejecutar primero la migración conserva los datos.

## Datos de demostración

`seed.py` es idempotente y crea:

- 10 catálogos maestros (países, puertos, monedas, categorías, productos,
  incoterms, conceptos de costo, tipos de documento, empresas y transportistas).
- Usuarios de prueba.
- 5 operaciones demo con ítems, escenarios, documentos, embarques, facturas,
  pagos y alertas.
- Un marcador de auditoría `SEED / demo_data` para no duplicar los datos demo.

Credenciales:

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador |
| `carlos.import` | `demo123` | Importador |
| `maria.export` | `demo123` | Exportador |
| `agro.export` | `demo123` | Exportador |
| `pepito` | `demo123` | Importador |
| `alfredo1` | `demo123` | Importador |

> `alfredo1` y otros usuarios que ya existían antes del seed conservan su
> contraseña original; el seed no la sobrescribe. En producción, cambiar
> `ADMIN_PASSWORD` y `DEMO_PASSWORD` antes del primer despliegue.

Para crear solo catálogos y administrador, sin operaciones demo:

```bash
SEED_DEMO=0 python seed.py
```

## Pruebas

La suite usa `unittest` y una base **SQLite temporal** con
`dependency_overrides[get_db]`; no modifica `data/app.db`.

```powershell
# Windows PowerShell
$env:PYTHONPATH=(Get-Location).Path
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

```bash
# Linux / macOS
PYTHONPATH=. python -m unittest discover -s tests -v
```

Cobertura:

- `test_cedula.py`: formato, provincia, tercer dígito, módulo 10, serie 30,
  duplicados y rechazo de perfiles inválidos.
- `test_flows.py`: CRUD de catálogos y usuarios, ciclo completo de una
  operación, ítems, transiciones válidas e inválidas, escenarios, documentos,
  embarques, facturas, pagos, sobrepago, alertas, API REST y permisos.
- `test_solid.py`: SRP, OCP, LSP, ISP, DIP y reemplazo de dependencias de
  FastAPI.

Resultado esperado: **21 pruebas OK**.

## API REST

La API comparte autenticación por sesión y permisos con las vistas. Los
endpoints de escritura requieren `ADMIN`; los de lectura de operaciones
respetan la asignación del usuario.

| Recurso | Endpoints |
|---|---|
| Autenticación | `GET /api/auth/me` |
| Operaciones | `GET/POST /api/operations`, `GET/PUT/DELETE /api/operations/{id}` |
| Ítems | `POST /api/operations/{id}/items`, `DELETE /api/operations/{id}/items/{item_id}` |
| Estados | `POST /api/operations/{id}/status` |
| Escenarios | `GET/POST /api/operations/{id}/scenarios`, `POST /api/scenarios/{id}/select`, `DELETE /api/scenarios/{id}` |
| Documentos | `GET/POST /api/documents`, `GET/PUT/DELETE /api/documents/{id}` |
| Embarques | `GET/POST /api/shipments`, `GET/PUT/DELETE /api/shipments/{id}` |
| Facturas | `GET/POST /api/invoices`, `GET/DELETE /api/invoices/{id}`, `POST /api/invoices/{id}/payments` |
| Alertas | `GET /api/alerts`, `POST /api/alerts/generate`, `POST /api/alerts/{id}/resolve` |
| Catálogos | `GET/POST /api/catalogs/{key}`, `GET/PUT/DELETE /api/catalogs/{key}/{id}` |
| Usuarios | `GET /api/admin/users`, `GET/DELETE /api/admin/users/{id}` |
| Auditoría | `GET /api/admin/audit` |

Ejemplo:

```bash
curl -c cookies.txt -X POST http://127.0.0.1:8000/login \
  -d "username=admin&password=admin123"

curl -b cookies.txt http://127.0.0.1:8000/api/operations
```

## Despliegue en Render + Neon

### 1. Crear la base en Neon

1. Crear un proyecto en <https://neon.tech>.
2. Copiar la cadena de conexión de PostgreSQL.
3. Guardarla como `DATABASE_URL`; no hace falta cambiar el prefijo, la
   aplicación lo adapta a `psycopg`.

### 2. Crear el servicio en Render

Opción A — Blueprint con `render.yaml`:

1. En Render, elegir **New → Blueprint** y conectar el repositorio.
2. Render lee `render.yaml` y solicita las variables marcadas con `sync: false`.

Opción B — Web Service manual:

| Campo | Valor |
|---|---|
| Runtime | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python migrate_legacy.py && python seed.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

### 3. Configurar variables

En **Environment** del servicio:

- `DATABASE_URL`: cadena de Neon.
- `SECRET_KEY`: generar un valor seguro.
- `ADMIN_PASSWORD`: contraseña real del administrador.
- `DEMO_PASSWORD`: contraseña para usuarios demo.
- `SEED_DEMO`: `1` para datos de demostración o `0` para producción limpia.

### 4. Desplegar y verificar

1. Render ejecuta la migración y el seed en cada arranque; ambos son
   idempotentes.
2. Verificar `https://<servicio>.onrender.com/health`.
3. Iniciar sesión con el administrador configurado.
4. Revisar `/dashboard`, `/operations` y `/alerts`.

> En el plan gratuito el servicio se suspende por inactividad. Al despertar,
> el comando de arranque vuelve a ejecutar migración y seed sin duplicar datos.

## Alcance y limitaciones

- **No hay integración aduanera real** ni conexión con sistemas de puertos,
  transportistas o autoridades.
- Los documentos guardan metadatos y una **URL** al archivo; no se suben
  binarios al servidor.
- Los costos son **estimaciones de planificación**; no reemplazan una
  liquidación aduanera ni contable.
- No se realiza conversión automática entre monedas: cada operación y factura
  conserva su moneda.
- El proyecto es académico y no implementa firma electrónica, notificaciones
  por correo ni integración con pasarelas de pago.

## Autor

**Alfredo Chiguano** — Ingeniería Web

Repositorio: <https://github.com/Chiwi21/tareaCRUD-LOGIN>

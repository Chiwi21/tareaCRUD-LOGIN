# Sistema Import/Export — CRUD y Login con MVC

Aplicación web desarrollada para la **Tarea 3 (CRUD / Login grupal)** de la materia **Ingeniería Web**.
Implementa el patrón **MVC**, un sistema de **autenticación con roles** y un **CRUD completo** de operaciones de importación/exportación, con protección de rutas HTML y REST.

> **Video de demostración:** _(agregar enlace de Loom o YouTube aquí)_

---

## Tabla de contenidos

- [Características](#características)
- [Roles del sistema](#roles-del-sistema)
- [Tecnologías](#tecnologías)
- [Arquitectura MVC](#arquitectura-mvc)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Despliegue en Render con Neon PostgreSQL](#despliegue-en-render-con-neon-postgresql)
- [Credenciales de prueba](#credenciales-de-prueba)
- [Rutas y protección](#rutas-y-protección)
- [Protección de rutas en detalle](#protección-de-rutas-en-detalle)
- [Capturas de pantalla](#capturas-de-pantalla)
- [Autores](#autores)

---

## Características

- **Login** con usuario y contraseña; las contraseñas se almacenan únicamente como **hash (bcrypt)**.
- **Registro público** solo para usuarios **Importador** y **Exportador**, con validación condicional según el tipo de persona (Natural o Jurídica).
- **Administrador** creado automáticamente mediante un **seed**; no puede registrarse públicamente.
- **CRUD administrativo de usuarios** Importador/Exportador con validación backend de cédula obligatoria y única. La cuenta ADMIN del seed está protegida.
- **CRUD de operaciones** (Crear, Leer, Actualizar, Eliminar) exclusivo del administrador.
- Cada operación se asigna a un Importador/Exportador existente mediante un dropdown; el backend valida la clave foránea.
- SQLite para desarrollo local y PostgreSQL online mediante `DATABASE_URL` para despliegue.
- **Protección de rutas**:
  - Vistas HTML sin sesión → redirección a `/login`.
  - Endpoints REST sin sesión → `401 Unauthorized`.
  - Usuarios sin rol admin → `403 Forbidden`.
- API REST mínima: `GET /api/admin/users`, `GET /api/admin/users/{id}`, `DELETE /api/admin/users/{id}` y `GET /api/operations`.

## Roles del sistema

| Rol (código) | Equivalente visual | Acceso |
|---|---|---|
| `ADMIN` | Administrador | Todo: CRUD de operaciones y gestión de usuarios |
| `IMPORTER` | Importador | Solo `/dashboard` |
| `EXPORTER` | Exportador | Solo `/dashboard` |

## Tecnologías

| Tecnología | Uso |
|---|---|
| **Python 3.14** | Lenguaje base |
| **FastAPI** | Framework web (controladores/rutas) |
| **Jinja2** | Motor de plantillas (vistas HTML) |
| **SQLAlchemy** | ORM (modelos y acceso a datos) |
| **SQLite** | Base de datos local (archivo `data/app.db`) |
| **PostgreSQL** | Base de datos online en producción |
| **Starlette SessionMiddleware** | Sesiones con cookie firmada |
| **bcrypt** | Hash de contraseñas |
| **psycopg** | Conexión SQLAlchemy a PostgreSQL en producción |

## Arquitectura MVC

| Capa | Responsabilidad | Archivos |
|---|---|---|
| **Modelo** | Lógica de datos y reglas de negocio | `app/models.py`, `app/database.py`, `app/security.py`, `app/user_validation.py` |
| **Vista** | Interfaz con el usuario | `app/templates/`, `app/static/` |
| **Controlador** | Conecta modelo y vista, recibe las peticiones | `app/controllers/` |

Flujo típico de una petición:

```
Navegador → Controlador (ruta FastAPI) → Modelo (consulta SQLAlchemy)
          → Vista (plantilla Jinja2) → Respuesta HTML al navegador
```

## Estructura del proyecto

```
tarea3-crud-login/
├── app/
│   ├── main.py                     # Aplicación, sesiones y manejo de 401/403
│   ├── config.py                   # SECRET_KEY y configuración
│   ├── constants.py                # Roles, tipos de persona, estados
│   ├── database.py                 # SQLite local/PostgreSQL online y migración FK
│   ├── models.py                   # User y Operation (Operation.user_id → User.id)
│   ├── security.py                 # Hash de contraseñas y guards de acceso
│   ├── user_validation.py          # Validación backend de perfiles y contraseñas
│   ├── templating.py               # Configuración de Jinja2
│   ├── controllers/
│   │   ├── auth_controller.py      # /login, /logout, /register
│   │   ├── dashboard_controller.py # /dashboard
│   │   ├── operation_controller.py # CRUD /operations + GET /api/operations
│   │   └── admin_controller.py     # /admin/users + API admin
│   ├── templates/                  # Vistas HTML (Jinja2)
│   └── static/                     # CSS y JavaScript
├── seed.py                         # Crea las tablas y el admin inicial
├── render.yaml                     # Configuración de despliegue en Render
├── requirements.txt
└── README.md
```

## Instalación y ejecución

Requiere **Python 3.11 o superior** (probado con Python 3.14).

```bash
# 1. Clonar el repositorio
git clone https://github.com/Chiwi21/tareaCRUD-LOGIN.git
cd tareaCRUD-LOGIN

# 2. Crear y activar el entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Inicializar la base de datos y crear el administrador (seed)
python seed.py

# 5. Ejecutar la aplicación
uvicorn app.main:app --reload
```

La aplicación queda disponible en **http://127.0.0.1:8000** y la documentación automática de la API en **http://127.0.0.1:8000/docs**.

> El archivo `data/app.db` se crea automáticamente y está excluido del repositorio. Antes de restablecerlo, haga una copia si necesita conservar los datos. La aplicación agrega de forma compatible `user_id` a tablas de operaciones de la versión anterior, sin borrar las operaciones existentes.

## Despliegue en Render con Neon PostgreSQL

En local, si no se define `DATABASE_URL`, la aplicación usa SQLite (`data/app.db`). En producción puede conectarse a PostgreSQL mediante SQLAlchemy.

1. Cree un proyecto PostgreSQL en Neon y copie la connection string con SSL.
2. Importe este repositorio en Render como un Web Service usando la rama `main` y `render.yaml`.
3. En Render, configure `DATABASE_URL` con la connection string de Neon y `ADMIN_PASSWORD` con una contraseña única de producción. `SECRET_KEY` se genera desde la configuración de Render.
4. Render instala las dependencias, ejecuta `python seed.py` (idempotente) y levanta Uvicorn en el puerto asignado.
5. Guarde la URL pública asignada por Render aquí: _(pendiente de desplegar)_ y pruebe login, CRUD, validaciones y rutas protegidas.

**No incluya** la connection string, `SECRET_KEY` ni la contraseña de producción en Git, README, capturas o video. El disco local del servicio gratuito de Render es temporal; PostgreSQL en Neon mantiene los datos entre despliegues.

## Credenciales de prueba locales

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `admin123` |

Estas credenciales son solo para desarrollo local. En producción se define otra contraseña mediante `ADMIN_PASSWORD` en Render. Los usuarios **Importador** y **Exportador** se crean desde la pantalla de registro (`/register`) o desde el panel ADMIN.

## Rutas y protección

### Públicas

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Redirige a `/login` o `/dashboard` según la sesión |
| GET | `/login` | Formulario de inicio de sesión |
| POST | `/login` | Valida credenciales y crea la sesión |
| GET | `/register` | Formulario de registro público |
| POST | `/register` | Registra Importadores y Exportadores |

### Protegidas (requieren sesión)

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| POST | `/logout` | Cualquiera con sesión | Cierra la sesión |
| GET | `/dashboard` | Cualquiera con sesión | Panel principal |
| GET | `/operations` | ADMIN | Lista de operaciones |
| GET | `/operations/new` | ADMIN | Formulario de creación |
| POST | `/operations/new` | ADMIN | Crea una operación asociada a un Importador/Exportador seleccionado |
| GET | `/operations/{id}` | ADMIN | Detalle de una operación |
| GET | `/operations/{id}/edit` | ADMIN | Formulario de edición |
| POST | `/operations/{id}/edit` | ADMIN | Actualiza una operación |
| POST | `/operations/{id}/delete` | ADMIN | Elimina una operación |
| GET | `/admin/users` | ADMIN | Lista de usuarios registrados |
| GET | `/admin/users/new` | ADMIN | Formulario de creación de usuario |
| POST | `/admin/users/new` | ADMIN | Crea un Importador/Exportador con validación backend |
| GET | `/admin/users/{id}` | ADMIN | Detalle de un usuario |
| GET | `/admin/users/{id}/edit` | ADMIN | Formulario de edición (no modifica la cuenta ADMIN del seed) |
| POST | `/admin/users/{id}/edit` | ADMIN | Actualiza perfil y, opcionalmente, contraseña |
| POST | `/admin/users/{id}/delete` | ADMIN | Elimina usuarios no ADMIN que no tengan operaciones asociadas |
| GET | `/api/operations` | ADMIN | Lista de operaciones y usuario asociado en JSON |
| GET | `/api/admin/users` | ADMIN | Lista de usuarios en JSON |
| GET | `/api/admin/users/{id}` | ADMIN | Detalle de usuario en JSON |
| DELETE | `/api/admin/users/{id}` | ADMIN | Elimina usuario si no es el ADMIN activo y no tiene operaciones asociadas |

## Protección de rutas en detalle

La protección se implementa con dependencias de FastAPI (`require_login` y `require_admin` en `app/security.py`) y un manejador global de excepciones en `app/main.py`:

| Situación | Vistas HTML | Endpoints REST (`/api/...`) |
|---|---|---|
| Sin sesión | Redirección `303` a `/login` | `401 Unauthorized` (JSON) |
| Sesión sin rol ADMIN | `403 Forbidden` (página HTML) | `403 Forbidden` (JSON) |

### Cómo verificarlo (prueba de incógnito)

1. Inicie sesión con `admin` / `admin123`.
2. Copie la URL de una sección protegida, por ejemplo `http://127.0.0.1:8000/admin/users`.
3. Abra una ventana de **incógnito** y pegue la URL.
4. La aplicación redirige a `/login` porque la cookie de sesión no existe en esa ventana.
5. También puede probar la API sin sesión:
   ```bash
   curl -i http://127.0.0.1:8000/api/admin/users
   # HTTP/1.1 401 Unauthorized
   ```

## Capturas de pantalla

_(agregar capturas del login, del CRUD y del test de incógnito)_

## Autores

- Cristian López
- Alfredo Chiguano

Proyecto académico — **Ingeniería Web**, Tarea 3: CRUD / Login con MVC.

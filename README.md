# International Trade — Portal de comercio exterior (V3)

Plataforma web en Python para importar con mayor claridad: **calculadora de presupuesto**, operaciones, **diagnóstico regulatorio preliminar**, comparador de escenarios de transporte, recursos informativos y administración de usuarios. Está construida con FastAPI, SQLAlchemy, Jinja2 y PostgreSQL/SQLite.

## Funcionalidades

- Login y registro de importadores con cédula ecuatoriana validada en back-end, correo y contraseña.
- Dashboard y administración con roles.
- Calculadora de CIF, arancel, FODINFA, IVA y gastos adicionales, con presupuesto y costo unitario estimado.
- Diagnóstico orientativo de posibles entidades y requisitos según categoría de producto.
- Comparación y almacenamiento de escenarios aéreo, LCL y FCL con tarifas suministradas por el usuario.
- Guías desplegables, directorio institucional y centro de ayuda.

## Inicio local en Windows

Descarga y extrae el proyecto. Ejecuta `INICIAR_INTERNATIONAL_TRADE.bat` (requiere Python 3.12 e internet en el primer inicio). Inicia sesión en `http://127.0.0.1:8000/login` con usuario `admin` y contraseña `admin123` **solo para localhost**, o crea tu propia cuenta de prueba. Los registros locales se guardan en `data/app.db`, excluida del repositorio.

## Publicación en GitHub y Render

Lee **[GUIA_GITHUB_RENDER_INTERNATIONAL_TRADE.md](GUIA_GITHUB_RENDER_INTERNATIONAL_TRADE.md)** para el procedimiento completo. Incluye creación de una base Neon nueva, variables secretas y comprobaciones en producción.

- Archivo de infraestructura: `render.yaml`.
- Versión Python: `.python-version` (`3.12`).
- Inicializador seguro: `prepare_production.py` (no elimina tablas y no crea usuarios ficticios).
- Health check: `/health`.

**Enlace del servidor:** pendiente de publicar. Añade aquí la URL real de Render cuando finalice el despliegue.

## Pruebas

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## Advertencias

**Prototipo académico.** Los resultados de impuestos, fletes y requisitos son orientativos, deben verificarse con fuentes y cotizaciones oficiales y no reemplazan a asesores o autoridades competentes. No uses información real sensible de clientes antes de revisar medidas adicionales de seguridad, privacidad, respaldo y protección de formularios.

No ejecutes `migrate_legacy.py` contra una base de producción: la migración antigua puede reconstruir tablas y queda bloqueada con `APP_ENV=production`. Si quieres conservar datos del antiguo CRUD, prepara una migración independiente con respaldo y verificación manual.

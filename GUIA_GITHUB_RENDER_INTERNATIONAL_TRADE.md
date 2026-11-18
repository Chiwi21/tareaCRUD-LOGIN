# International Trade V3 — Cómo subirlo a GitHub y desplegarlo en Render

**Versión preparada para una nueva base PostgreSQL de Neon. No es una migración automática de la antigua aplicación de importaciones.**

## 0. Qué contiene esta versión

- Sistema FastAPI + SQLAlchemy + Jinja2, con calculadora de costos, operaciones, semáforo preliminar, comparador logístico, directorio y login.
- `render.yaml` preparado para un **nuevo** web service gratuito llamado `international-trade-v3`.
- `.python-version` fija Python 3.12 en Render.
- `prepare_production.py`: crea las tablas faltantes y los catálogos mínimos, además de un administrador con la contraseña suministrada en Render. **No crea usuarios u operaciones ficticias, no elimina tablas ni aplica migraciones destructivas.**
- `migrate_legacy.py` heredado queda bloqueado bajo `APP_ENV=production`.
- `app/main.py`: las cookies de sesión requieren HTTPS cuando `APP_ENV=production`.
- `tests/test_deployment_safety.py`: verifica que un esquema heredado se rechaza sin borrar registros.

No está publicado por el mero hecho de descargar el ZIP: debes hacer tú el push y crear el servicio en Render.

## 1. Preparar archivos en Windows

1. Extrae **todo** el ZIP en una carpeta independiente, por ejemplo `C:\Proyectos\International-Trade`.
2. Comprueba que al abrir esa carpeta veas `app`, `render.yaml`, `prepare_production.py`, `.python-version`, `requirements.txt` y `README.md`.
3. Abre **esa carpeta raíz** en VS Code: **File → Open Folder**.
4. **No subas** `.venv/`, `data/app.db`, `.env` ni contraseñas. Están ignoradas por `.gitignore`.
5. Si quieres probar localmente, ejecuta `INICIAR_INTERNATIONAL_TRADE.bat` con SQLite como antes. No mezcla bases con Neon.

## 2. Subir a un repositorio de GitHub NUEVO y vacío

Crea un repositorio en GitHub, preferiblemente `international-trade`, **sin inicializarlo** con README o licencia. En la terminal de VS Code, desde la carpeta raíz del proyecto:

```powershell
git init -b main
git status
git add .
git commit -m "feat: publicar International Trade V3 con calculadora y comparador"
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
```

Sustituye la URL con la del repositorio que vas a compartir. Si Git pide credenciales, inicia sesión con la cuenta que sea propietaria o colaboradora con permisos de escritura.

**Si el repositorio ya tiene historial o archivos:** no ejecutes `git init` ni `git push --force`. Clónalo primero con `git clone URL`, copia dentro de la copia clonada los archivos del proyecto (sin sobrescribir su `.git`) y ejecuta `git add -A`, `git commit -m "..."`, `git push origin main`. Esto conserva los commits antiguos. Si ese repositorio ya alimenta una app pública en Render, prueba primero en una rama nueva y no modifiques `main` hasta estar listo.

Si recibes `403`, verifica permisos de la cuenta autenticada en Git. El autor mostrado en Git no determina los permisos de push.

## 3. Crear una base NUEVA en Neon (recomendado)

1. Entra a https://console.neon.tech/ y crea un proyecto PostgreSQL nuevo, por ejemplo `international-trade-v3`.
2. En **Connect** selecciona la base `neondb`, usa **Direct connection** (Connection pooling desactivado) y copia la URL completa con `sslmode=require`.
3. No pegues esta URL en GitHub, README ni chats. Se introduce **solo en Render** como `DATABASE_URL`.
4. La nueva base está vacía: la aplicación creará sus tablas al arrancar. **No reutilices la base del antiguo CRUD sin respaldo y plan de migración.** `create_all()` no convierte automáticamente sus tablas antiguas.

## 4. Crear el servicio en Render

1. Abre https://dashboard.render.com/ e inicia sesión.
2. Elige **New → Blueprint**.
3. Conecta el repo de GitHub. Si no aparece, autoriza la instalación de Render en la cuenta **propietaria**. Como alternativa, para un repositorio público, Render permite usar su URL pública, pero puede no disponer de despliegue automático.
4. Selecciona la rama `main`. Deja `render.yaml` en la raíz.
5. El Blueprint incluye **un servicio nuevo** `international-trade-v3` en plan Free. No sustituye el antiguo `tradelab` por nombre.
6. Render pedirá los valores secretos marcados `sync: false`:

| Variable | Valor |
| --- | --- |
| `DATABASE_URL` | Cadena completa de Neon, con SSL, sin comillas |
| `ADMIN_PASSWORD` | Contraseña nueva, aleatoria, de **12 caracteres como mínimo**; mejor 16–24 |

Las siguientes se configuran sin intervención:

| Variable | Valor |
| --- | --- |
| `APP_ENV` | `production` |
| `ADMIN_USERNAME` | `admin` |
| `SECRET_KEY` | Generada por Render |

**No** establezcas `SEED_DEMO=1`, ni `DEMO_PASSWORD`. No uses `admin123` en producción. No añadas secrets al archivo `render.yaml`.

7. Revisa que el plan sea **Free** y pulsa **Deploy Blueprint**.
8. Abre **Logs**. Deberías ver `International Trade: base lista...` y luego el inicio de Uvicorn.
9. Al terminar, visita la URL que Render te asigne, del tipo `https://international-trade-v3.onrender.com` (solo un ejemplo, verifica la URL real).

### Si falla

- `Faltan columnas / esquema anterior`: la URL de Neon corresponde a una base incompatible. **No ejecutes `migrate_legacy.py`** en ella. Usa una base nueva o diseña una migración revisada con copia de seguridad.
- `No module named ...`: confirma que Build Command sea `pip install -r requirements.txt`.
- `SECRET_KEY` o `ADMIN_PASSWORD` incorrectas: revisa las variables desde **Environment**, sin revelar su valor en capturas.
- Login incorrecto tras cambiar `ADMIN_PASSWORD`: la contraseña del administrador creado previamente no se actualiza automáticamente. En una base nueva, usa la clave inicial que pusiste en Render.
- Primera carga lenta: los servicios gratuitos de Render pueden suspenderse tras un periodo de inactividad.

## 5. Pruebas de aceptación en la web

1. Abre `/health` y verifica `{"status":"ok","app":"International Trade"}`.
2. Abre `/login` e inicia sesión con `admin` y la contraseña configurada en Render.
3. Prueba el registro desde `/register` con datos de prueba válidos.
4. Entra a **Calculadora de importación**, modifica presupuesto, cantidad, flete, seguro y tasas, y comprueba el resultado y la advertencia de simulación.
5. Crea una operación con categoría de producto. Abre su detalle para ver el checklist preliminar de entidades.
6. Abre el comparador, guarda escenarios AIR/LCL y contrasta el costo unitario.
7. Comprueba en Neon → SQL Editor que hay filas, por ejemplo:

```sql
SELECT id, username, role FROM users ORDER BY id DESC;
SELECT id, code, type, status FROM operations ORDER BY id DESC;
SELECT operation_id, category, product_name FROM operation_trade_profiles;
SELECT operation_id, name, mode FROM freight_comparisons;
```

8. Comprueba que si cierras sesión y abres `/admin/users` se exige el login.

## 6. Observaciones antes de operar con clientes reales

Esta versión es una **demo académica pública**, no una plataforma lista para procesar datos comerciales sensibles de clientes. Antes de un lanzamiento real deberías revisar CSRF, protección anti-bots, límites de peticiones, verificación de correo, recuperación de contraseñas, política de privacidad, registros de auditoría y copias de seguridad. El diagnóstico regulatorio es orientativo; no sustituye una clasificación o autorización oficial. Los importes son estimaciones y necesitan tasas y cotizaciones verificadas.

Los servicios web gratuitos de Render usan un sistema de archivos efímero. Guarda los datos en Neon y no dependas de archivos SQLite ni de imágenes subidas manualmente al servidor en ejecución.

## 7. Después del primer deploy

Cuando tengas la URL pública, añádela al `README.md` del repositorio y crea un nuevo commit. Si Render está conectado a GitHub con permisos, los cambios en `main` suelen desencadenar un nuevo despliegue automático. Si se conectó solo por URL pública, revisa las opciones de despliegue manual.

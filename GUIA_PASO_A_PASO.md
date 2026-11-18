# Guía rápida — International Trade en Windows

## 1. Extraer el ZIP

Descarga `International_Trade_Vista_Previa_Local.zip`. Haz clic derecho y
**Extraer todo**. Abre la carpeta `International-Trade` que aparece dentro.
**No ejecutes el `.bat` desde dentro del visor del ZIP:** hay que extraerlo.

## 2. Comprobar Python

En Windows abre PowerShell y ejecuta `py -3 --version` o `python --version`.
Si no existe Python, instala Python 3.12 desde python.org y habilita pip.

## 3. Abrir el portal

Haz doble clic en **`INICIAR_INTERNATIONAL_TRADE.bat`**.
El primer inicio necesita Internet para descargar dependencias. No necesitas
abrir VS Code para iniciar la vista previa.

El lanzador te preguntará si quieres cargar **datos ficticios de demostración**:
- `S`: ver ejemplos de operaciones, embarques, facturas y alertas.
- `N`: base casi vacía con catálogos y administrador, para probar desde cero.

El programa creará `data/app.db` en esta misma carpeta y abrirá:

> Si ya cargaste datos de ejemplo anteriormente, elegir `N` no los borra.
> La base local es persistente hasta que tú decidas eliminarla.

**http://127.0.0.1:8000/login**

Si el navegador se adelanta al servidor, actualiza la página con `Ctrl+R`.
No cierres la ventana negra de la consola mientras utilices la página.

## 4. Iniciar sesión

Administrador **solo local**:
- Usuario: `admin`
- Contraseña: `admin123`

Para registrar una cuenta nueva, abre `http://127.0.0.1:8000/register`.
Completa nombres y apellidos, cédula ecuatoriana válida, correo electrónico y
contraseña. Después inicia sesión con el correo y tu contraseña.

Los usuarios antiguos también pueden entrar por nombre de usuario; al cargar
datos de demostración, una cuenta de ejemplo es `carlos.import` / `demo123`.

## 5. Qué probar

1. **Dashboard:** menú lateral, KPI reales y lista de operaciones.
2. **Registro:** enviar cédula incorrecta y verificar que el servidor la rechaza.
3. **Login:** entrar con el correo registrado.
4. **Calculadora:** introducir cantidades y tasas; comprobar cálculo de CIF,
   arancel, FODINFA, IVA y costo unitario.
5. **Información:** abrir vínculos a entidades oficiales.
6. **Centro de ayuda:** guardar una consulta y revisar su historial.
7. **Administrador:** entrar con `admin`; comprobar operaciones, catálogos,
   documentos y `/admin/soporte`.

**Nota:** los importadores registrados pueden consultar sus operaciones, pero
por ahora la creación y asignación de operaciones reales sigue reservada al
administrador, como en el código original. La futura función «Crear mi proyecto»
será otro desarrollo.

## 6. Detener y volver a abrir

Pulsa `Ctrl+C` en la consola o cierra la ventana del servidor.
Para volver, abre el `.bat` nuevamente. **No elimina tu base local.**

Si el puerto 8000 está ocupado por otro proyecto, cierra el servidor anterior.

## 7. Cambios a futuro

Esta carpeta no está vinculada a GitHub por defecto. No necesita Git, Render ni
Neon para verse localmente. Si decides publicar después, primero revisaremos
las nuevas tablas y los requisitos de seguridad de producción.

En caso de error, abre PowerShell dentro de `International-Trade` y ejecuta:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Copia el texto del error (sin compartir contraseñas ni URLs secretas).

# Guía de instalación y pruebas — International Trade V3

## 1. Abrir la versión local sin tocar Render

1. Extrae el archivo `International_Trade_V3_Presupuesto_Regulaciones_Logistica.zip` en una carpeta nueva.
2. Abre la carpeta `International-Trade`.
3. Ejecuta con doble clic **`INICIAR_INTERNATIONAL_TRADE.bat`**.
4. Windows puede avisar que es un archivo descargado: revisa el contenido en Bloc de notas y ejecútalo solo si confías en la procedencia.
5. Primera instalación: requiere Python y conexión a internet para `pip install`.
6. Responde **S** para generar datos ficticios. Espera a que aparezca Uvicorn. Si el navegador abre demasiado pronto, recarga la pestaña.
7. Visita `http://127.0.0.1:8000/login` (no uses el enlace de Render).
8. Entra con **usuario `admin` y contraseña `admin123`** (exclusivamente local).

La consola debe permanecer abierta. Para detener el proyecto, vuelve a la consola y pulsa **Ctrl+C**.

**Si ya tienes otro servidor en el puerto 8000**, detén primero su ventana. Si no se abre el proyecto, envía una captura del error de la consola.

## 2. Recorrido de prueba de la calculadora

1. Pulsa **Calculadora de importación** en el menú izquierdo.
2. Prueba `Presupuesto 20000`, `Cantidad 100`, `Precio unitario 150`, `Flete 1800`, `Seguro 1 %`, `Arancel 10 %`, `FODINFA 0,5 %`, `IVA 15 %` y gastos locales que conozcas.
3. Presiona **Calcular mi presupuesto**.
4. Comprueba el **desembolso total**, **costo por unidad**, **impuestos estimados** y el aviso de presupuesto suficiente o insuficiente.
5. Despliega las preguntas de la sección **Guía: cómo se calcula una importación** para comprender CIF, aranceles y gastos locales.

No confundas el precio FOB con un precio CIF. Si la cotización ya incluye flete o seguro, **no lo dupliques**. El arancel se ingresa manualmente; es una simulación, no un cobro real de SENAE.

## 3. Crear operación con diagnóstico regulatorio

1. Entra en **Mis operaciones → Nueva operación**.
2. Si ingresaste como administrador, completa también el tipo de operación. Puedes elegir empresa, responsable, origen y destino de los catálogos disponibles.
3. En la nueva sección **¿Qué producto planeas importar?**, elige la categoría: electrónica, cosméticos, textiles, alimentos, agropecuarios, etc.
4. Escribe nombre del producto, detalles técnicos, cantidad y presupuesto.
5. Introduce subpartida HS solo si tienes una. El código **no se valida en ECUAPASS automáticamente**.
6. Guarda la operación y abre su detalle.
7. En **Diagnóstico preliminar de requisitos** aparecen advertencias, instituciones, pasos y enlaces para consultar las fuentes.

**Ejemplo:** si eliges cosméticos, el sistema alerta de que puede aplicar la Notificación Sanitaria Obligatoria (NSO) en ARCSA. No asegura que todos los cosméticos o productos de salud tengan el mismo trámite; hay que verificar clasificación y características.

## 4. Comparar transporte aéreo y marítimo

1. Dentro del detalle de la operación, pulsa **Comparar escenarios**.
2. Crea **Escenario A — Aéreo**. Ingresa cantidad, valor unitario, presupuesto, bultos, dimensiones, peso real, tarifa cotizada en USD/kg y cargos del envío.
3. Guarda el escenario.
4. Crea **Escenario B — Marítimo LCL**, usando los mismos datos físicos pero tu tarifa cotizada USD/W/M y cargos portuarios.
5. Guarda y compara los resultados **uno al lado del otro**. También puedes probar FCL por contenedor.
6. Analiza **peso facturable, CBM, flete estimado, desembolso y costo unitario**. Si tienes plazos estimados del transportista, agrega los días manualmente.

No uses los ejemplos como cotizaciones reales. Si el proveedor o transportista cobra un mínimo diferente o prohíbe el envío de una mercancía, manda la condición real.

## 5. Cambiar las fotos de entidades

1. Consigue una fotografía o logotipo que puedas utilizar legalmente.
2. Copia el archivo (p. ej. `senae.webp`) dentro de `app/static/img/entities/`.
3. Abre `app/templates/portal/information.html` en VS Code.
4. Busca la lista de entidades al principio de la plantilla. Cada registro termina en un nombre de archivo, como `'senae.svg'`. Cambia solo ese valor a `'senae.webp'` si cargaste una imagen con ese nombre. La etiqueta de imagen utiliza `src="/static/img/entities/{{ img_name }}"` automáticamente.
5. Guarda, actualiza el navegador con **Ctrl+F5** y comprueba que se vea.

Las ocho imágenes iniciales son marcadores originales y genéricos. No representan logotipos oficiales.

## 6. Guías y glosario

Entra en **Guías y entidades**. Utiliza la búsqueda y despliega términos como `FOB`, `CIF`, `FODINFA`, `subpartida`, `LCL`, `FCL`, `W/M`, `packing list`, `ARCSA` y `ECUAPASS`.

## 7. Qué se guarda, qué no y cómo recuperar datos

- Los cambios se guardan en `data/app.db` **de esta carpeta**. La nueva V3 crea dos tablas complementarias sin borrar las existentes.
- Si ya tienes información en la V2 y quieres conservarla, cierra ambos servidores, haz una copia de seguridad del archivo antiguo `data/app.db` y copia esa base a la misma ruta de la V3 **antes de iniciarla**. Conserva una copia del original. Se crearán solo las tablas nuevas cuando arranque.
- No pegues contraseñas ni la `DATABASE_URL` de Neon en código, pantallazos o chats.
- No despliegues esta versión en producción hasta comprobarla y preparar las migraciones.

## 8. Ejecutar pruebas de Python

En PowerShell, dentro de la carpeta principal y después de ejecutar el iniciador al menos una vez:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas deben finalizar con `OK`. Si aparecen errores, compártelos antes de subir cambios a GitHub.

## 9. Problemas frecuentes

- **`py` no reconocido:** prueba `python --version`, instala Python 3.12 o ejecútalo desde la ruta conocida.
- **Puerto 8000 ocupado:** detén el servidor anterior pulsando Ctrl+C.
- **Falta dependencia:** ejecuta `pip install -r requirements.txt` con el Python de `.venv`.
- **La foto no cambia:** confirma que el `src` coincide exactamente con el nombre del archivo y recarga con Ctrl+F5.
- **No salen los escenarios:** crea primero una operación, entra en su detalle y selecciona **Comparar escenarios**.
- **No aparecen mis datos antiguos:** estás trabajando con otra copia de `data/app.db`; no es un problema de Neon.

## Estado

V3 local — permite revisar diseño y lógica. Las tarifas de transporte no están conectadas a proveedores, las tasas tributarias requieren verificación y el semáforo **no declara automáticamente permiso concedido ni mercancía de libre importación**.

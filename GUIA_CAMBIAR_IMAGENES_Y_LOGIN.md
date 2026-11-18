# International Trade — Cambiar fotografías y usar el nuevo login

## Qué cambia esta versión

- El login `/login` ahora utiliza dos columnas: carrusel grande a la izquierda y formulario de acceso a la derecha.
- El registro `/register` tiene un estilo coherente; mantiene los mismos campos y validación del back-end.
- Un nuevo archivo `app/static/js/auth-slider.js` controla las flechas y los puntos del carrusel, cambiando de imagen cada 6,5 segundos.
- No se modificaron las tablas, los endpoints de autenticación ni la conexión a la base de datos.
- Las imágenes de ejemplo son ilustraciones SVG originales, incluidas sin depender de URLs externas.

## Cómo colocar tus imágenes

1. Busca en tu proyecto `app/static/img/login/`.
2. Copia ahí tu fotografía, por ejemplo `puerto-china.jpg`.
3. En VS Code abre `app/templates/auth/login.html`.
4. Busca la primera línea que dice:

   `<img class="it-login-slide-image" src="/static/img/login/slide-1.svg" ...>`

   Cambia **solo la ruta `src`** a `/static/img/login/puerto-china.jpg`.
5. Guarda con Ctrl+S y recarga `http://127.0.0.1:8000/login` con Ctrl+F5.
6. Repite con slide-2 y slide-3 si quieres otras fotos.

Para cambiar la imagen de la pantalla de registro, abre `app/templates/auth/register.html` y cambia la ruta de `slide-2.svg`.

Formatos recomendados: JPG o WebP. Tamaño de origen de 1600×1100 o similar, entre 200 y 700 KB cuando sea posible. Para un logotipo con transparencia, utiliza PNG o SVG propio.

**No basta con copiar un archivo a la carpeta**: la plantilla debe apuntar a la ruta que usaste.

## Cómo agregar una imagen al dashboard

En la plantilla `app/templates/dashboard.html`, coloca en la ubicación deseada:

```html
<img src="/static/img/mi-banner.webp" alt="Carga internacional en puerto" class="mi-banner">
```

La foto `mi-banner.webp` debe estar en `app/static/img/`. Agrega a `app/static/css/international-trade.css`:

```css
.mi-banner { width: 100%; max-height: 350px; object-fit: cover; border-radius: 16px; }
```

## Iniciar el proyecto

1. Extrae el ZIP en una carpeta nueva. (Haz respaldo de la versión anterior.)
2. Doble clic en `INICIAR_INTERNATIONAL_TRADE.bat`.
3. Abre `http://127.0.0.1:8000/login`.
4. Prueba usuario `admin` / `admin123` **solo en local**.
5. Si ya tenías datos locales, puedes conservar tu `data/app.db` de la versión anterior copiándolo a esta carpeta antes de iniciar, siempre que sea del mismo proyecto y versión compatible. Haz una copia de seguridad antes.

Este archivo es una versión local de prueba; no está publicada en Render o Neon.

## Buenas prácticas

- Google Imágenes es un buscador, no una licencia. Utiliza fotografías tuyas o imágenes autorizadas para uso en tu proyecto. Revisa las condiciones de bancos como Unsplash, Pexels o los proveedores originales.
- No copies imágenes, logotipos ni textos del sistema Perseo. Solo se usó la composición general como inspiración.
- Si deseas que los usuarios suban sus propias imágenes desde un panel, eso requiere una funcionalidad adicional: formulario de carga, validación de extensiones/tamaño y almacenamiento persistente. Este ZIP permite añadir fotos manualmente a los archivos estáticos del proyecto.

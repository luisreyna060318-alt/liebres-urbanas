# Despliegue: Neon + Render + Vercel

Combinación gratuita y sin tarjeta que recomienda la materia. Cada pieza hace una sola cosa:

```
Navegador ──> Vercel (frontend React) ──> Render (backend FastAPI, en Docker) ──> Neon (PostgreSQL)
                                                   ├──> Nominatim (direcciones; solo lo llama el backend)
                                                   └──> Open-Meteo (pronóstico; solo lo llama el backend)
```

Las tres cuentas son personales de Luis (entró con su GitHub) y el repositorio de trabajo es público
(`luisreyna060318-alt/liebres-urbanas`), así que las tres plataformas pueden leerlo. **Ninguna clave se sube a Git**: se
escriben solo en el panel de cada servicio. Si alguien más hace la demo, se usa la misma URL pública; no hay que
desplegar otra vez.

## Orden recomendado

1. **Neon**: crear la base y copiar la cadena de conexión (no se pega en ningún chat).
2. **Render**: crear el backend con la cadena de Neon. Anotar su URL pública.
3. **Vercel**: crear el frontend con la URL de Render en `VITE_API_URL`. Anotar su URL pública.
4. **Render otra vez**: poner la URL de Vercel en `CORS_ORIGINS`.
5. **Comprobar** y **calentar** los servicios antes de la demo.

Se hace en ese orden porque cada paso necesita la dirección del anterior; CORS cierra el círculo al final.

## 1. Neon (base de datos)

1. Crea un proyecto llamado `liebre-urbana` en <https://neon.tech> y elige una región cercana a Render (en este
   proyecto, **AWS US East**; Render se pone en **Virginia**).
2. En **Connect**, usa la conexión **directa**: apaga el interruptor **Connection pooling**, de modo que el host
   **no** contenga `-pooler`. La conexión con pool está pensada para muchas conexiones cortas y puede dar problemas
   con las migraciones de Alembic.
3. Copia la cadena de conexión completa (con todo lo que va después del `?`). Se ve así:
   `postgresql://usuario:clave@ep-xxxx.neon.tech/neondb?sslmode=require`
4. Para Render, cambia solo el principio: `postgresql://` por **`postgresql+psycopg://`** (el backend usa el
   controlador psycopg 3). El resto queda igual. Ese es el valor de `DATABASE_URL` del paso 2.
5. **No pegues la cadena en chats, issues, pull requests ni commits** (el repositorio es público). Si por accidente
   la pegas en algún lugar, cambia la contraseña en *Roles & Databases > tu rol > Reset password* y usa la cadena
   nueva.

No hay que crear tablas a mano: al arrancar, el backend aplica las migraciones y carga los datos de demostración.

## 2. Render (backend)

> **Si en tu cuenta no aparece _Blueprint_** (la interfaz de Render cambia), no pasa nada: usa **New Web Service**
> (opción B). El resultado es el mismo.

**Opción A: Blueprint.** En <https://render.com>: **New + > Blueprint**, elige el repositorio. Render lee
`render.yaml` y crea el servicio `liebre-urbana-api`. Te pide los valores que no se pueden guardar en Git:

| Variable | Qué poner |
|---|---|
| `DATABASE_URL` | La cadena de Neon del paso 1, con el prefijo `postgresql+psycopg://` |
| `CORS_ORIGINS` | La URL del frontend en Vercel, sin diagonal final. Si aún no la tienes, escribe una provisional (por ejemplo `https://liebre-urbana.vercel.app`) y corrígela en el paso 4 |
| `SEED_CIUDADANO_PASSWORD`, `SEED_MODERADOR_PASSWORD`, `SEED_COORDINADOR_PASSWORD` | Contraseñas de **demostración** de las tres cuentas. Son ficticias y públicas (se escriben en el README para la demo): **nunca** pongas una contraseña real tuya |

`SECRET_KEY` la genera Render sola. `ENTORNO=produccion` y `SEED_ON_START=true` ya vienen en `render.yaml`. Con
`ENTORNO=produccion` el backend **se niega a arrancar** si la clave es corta o es la del ejemplo.

**Opción B: New Web Service.** Elige el repositorio y llena:

| Campo | Valor |
|---|---|
| Name | `liebre-urbana-api` |
| Branch | `main` |
| Language | **Docker** |
| Dockerfile Path | `backend/Dockerfile` |
| Docker Build Context Directory | `.` (la raíz del repositorio; la imagen necesita `backend/` y `db/`) |
| Region | La misma de Neon (**Virginia, US East**) |
| Instance Type | **Free** |
| Health Check Path (en *Advanced*) | `/api/health` |
| Docker Command y Pre-Deploy Command | **vacíos**: el arranque del contenedor ya aplica las migraciones |

Variables de entorno: `ENTORNO=produccion`, `SEED_ON_START=true`, `CORS_ORIGINS`, `DATABASE_URL`,
`SEED_CIUDADANO_PASSWORD`, `SEED_MODERADOR_PASSWORD`, `SEED_COORDINADOR_PASSWORD` (como en la tabla de arriba) y
`SECRET_KEY`, que se obtiene con el botón **Generate** de Render.

**Con la opción A o con la B**, espera a que el servicio diga **Live** (el primer despliegue tarda unos minutos).
Prueba en el navegador:

- `https://TU-SERVICIO.onrender.com/api/health` debe responder que está bien.
- `https://TU-SERVICIO.onrender.com/docs` debe mostrar la documentación de la API.

Anota la URL (`https://TU-SERVICIO.onrender.com`): se usa en el paso 3. Si el nombre `liebre-urbana-api` ya está
ocupado, Render agrega un sufijo; en ese caso usa la URL real y actualiza también el `connect-src` de
`frontend/vercel.json` (ver el paso 3).

### Que Render despliegue cada cambio

Un servicio creado desde **Public Git Repository** (o desde la herramienta de Render) no recibe avisos de GitHub, así
que **no se redespliega con cada fusión**: la aplicación publicada se queda con una versión vieja y los endpoints
nuevos responden 404. Hay dos formas de resolverlo (basta una):

1. **Conectar la cuenta de GitHub en Render** (Account Settings > GitHub) y dar acceso a `liebres-urbanas`. Después
   revisa en el servicio que *Auto-Deploy* esté activado.
2. **Deploy Hook:** en el servicio, *Settings > Deploy Hook*, copia la dirección. En GitHub, *Settings > Secrets and
   variables > Actions > New repository secret*, crea `RENDER_DEPLOY_HOOK_URL` con esa dirección. Es un secreto:
   no la pegues en chats, issues ni commits. El flujo `.github/workflows/despliegue.yml` la usa en cada fusión.

El flujo **Despliegue** comprueba en cada fusión a `main` que la API publicada responda; `/api/health` muestra en
`version` el commit publicado. Antes de una demo, revisa que coincida con el último commit de `main`. Si no, usa
**Manual Deploy > Deploy latest commit** en Render.

### Si Render no ve el repositorio

- En Render: **Account Settings > GitHub** (o *Configure account*) y revisa que la aplicación de Render esté instalada en
  la cuenta `luisreyna060318-alt` con acceso a `liebres-urbanas` (elige *All repositories* o selecciónalo
  a mano). Luego recarga la página de creación del servicio.
- El repositorio es público: en **New Web Service** también sirve la pestaña **Public Git Repository**, donde se pega la
  URL del repositorio (`https://github.com/luisreyna060318-alt/liebres-urbanas`). No necesita permisos de GitHub, pero
  tampoco redespliega solo con cada push (hay que usar **Manual Deploy**).
- Si el repositorio es de otra cuenta u organización que Render no puede ver, haz un fork a la cuenta conectada.

## 3. Vercel (frontend)

1. En <https://vercel.com>: **Add New > Project**, elige el repositorio.
2. **Root Directory:** `frontend` (el repositorio es un monorepo; sin esto Vercel no encuentra `package.json`).
   Framework Preset: Vite (lo detecta solo; build `npm run build`, salida `dist`).
3. **Environment Variables:** `VITE_API_URL` = la URL de Render del paso 2, sin diagonal final (por ejemplo
   `https://TU-SERVICIO.onrender.com`). Vite la escribe en el código al compilar: si la cambias después, haz
   **Redeploy** para que surta efecto.
4. **Deploy.** Las rutas de React Router (`/zona`, `/reportes/3`, `/login`...) funcionan al recargar la página gracias a
   `frontend/vercel.json`, que ya está en el repositorio y reescribe todas las rutas a `/index.html`.
5. Copia la URL que te da Vercel (`https://TU-PROYECTO.vercel.app`, sin diagonal final): la necesitas en el paso 4.

**La CSP de `frontend/vercel.json`.** Ese archivo trae cabeceras de seguridad, entre ellas una `Content-Security-Policy`
que solo deja al navegador hablar con el backend de ejemplo `https://liebre-urbana-api.onrender.com` (directiva
`connect-src`). **Si tu URL de Render es otra, cámbiala ahí** y haz commit; si no, el navegador bloqueará las peticiones
a la API aunque CORS esté bien. La política también permite imágenes de los mosaicos de OpenStreetMap
(`https://*.tile.openstreetmap.org`) para el mapa y estilos en línea (los usa Leaflet).

## 4. Cerrar el círculo (CORS)

Vuelve a Render > tu servicio > **Environment** y pon en `CORS_ORIGINS` la URL final de Vercel (la del paso 3, sin
diagonal final; si usas también un dominio propio, sepáralos con comas). Render reinicia el servicio.

CORS es lo que hace que **solo tu frontend** pueda llamar a la API desde un navegador. Es el primer lugar donde mirar
si algo falla en producción. Si al iniciar sesión el navegador marca un error de CORS, casi siempre es que esta URL
tiene una diagonal final o no coincide exactamente con la de Vercel (`https`, mayúsculas y subdominio incluidos).

## 5. Comprobar

- [ ] `/api/health` y `/docs` del backend responden.
- [ ] Desde el frontend (URL de Vercel): iniciar sesión con la cuenta de ciudadano de la demo.
- [ ] La lista pública de reportes carga con los datos de la semilla.
- [ ] Un registro nuevo y un inicio de sesión funcionan (esto prueba CORS y permisos).
- [ ] Con la cuenta de ciudadano, una acción de moderador o coordinador (por ejemplo `GET /api/usuarios`, que se prueba
      en `/docs`) responde **403**.
- [ ] Si el pronóstico o las direcciones fallan, la pantalla lo dice sin romperse (son servicios externos).

## El día de la demo

- **Render (plan gratuito) se duerme** tras 15 minutos sin tráfico y tarda 30 a 60 segundos en despertar; Neon también
  suspende la base tras unos minutos sin uso. **10 minutos antes**, abre `https://TU-SERVICIO.onrender.com/api/health`
  hasta que responda, y luego abre el frontend, inicia sesión y abre la lista de reportes. Así los dos servicios
  están despiertos cuando empiece la demostración.
- **Plan B obligatorio:** si la nube falla, todo se levanta en la laptop con `docker compose up` (ver el README;
  requiere Docker Compose 2.24 o más nuevo). Levanta base de datos, backend y frontend en <http://localhost:8080>.
  Antes de la demo corre una vez `docker compose build` para tener las imágenes construidas (así levanta en menos de
  3 minutos) y deja Docker Desktop abierto. Sin internet, el pronóstico muestra "Pronóstico no disponible" y las
  direcciones se capturan a mano.
- Los límites de los planes gratuitos cambian: verifícalos en el sitio de cada proveedor antes de desplegar.

## Seguridad (para el reporte)

- Ningún secreto en el repositorio ni en la imagen de Docker (`.env` está en `.gitignore` y en `.dockerignore`); las
  contraseñas de demostración son ficticias y públicas a propósito.
- `SECRET_KEY` aleatoria generada por Render; en producción no se acepta la de ejemplo (OWASP A02).
- CORS limitado al dominio del frontend (OWASP A02) y autorización por rol verificada en el servidor (OWASP A01).
- Cabeceras de seguridad y CSP en Vercel (`frontend/vercel.json`).
- El contenedor del backend corre como un usuario sin privilegios, no como `root`; el del frontend, también.

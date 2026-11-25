# Revisión de seguridad del backend (A01 y A02)

Revisión hecha en la rama L11 sobre todos los endpoints que existen hasta L10 (cuenta, catálogos, ubicación y reportes
del ciudadano). La comprobación automática está en `backend/tests/test_seguridad.py`.

En OWASP Top 10, A02 es "Fallas criptográficas" en la edición 2021 y "Configuración de seguridad incorrecta" en la 2025;
se revisaron los dos temas.

## A01 — Control de acceso roto

| Qué se revisó | Resultado |
|---|---|
| Cada endpoint protegido usa `require_role(...)` o `usuario_actual` en el servidor | Correcto. La matriz rol × endpoint prueba los 17 endpoints con 4 casos (sin sesión, ciudadano, moderador, coordinador). Una prueba falla si se agrega una ruta y no se suma a la matriz |
| El 403 de rol llega antes de validar el cuerpo | Correcto: un moderador recibe 403 aunque mande datos inválidos (no aprende nada de los campos) |
| Rol y suspensión se leen de la base en cada petición | Correcto: con un token todavía vigente, la suspensión da 403 `CUENTA_SUSPENDIDA` y el cambio de rol surte efecto en la siguiente petición |
| Autoría al editar y borrar (`PUT`/`DELETE /api/reportes/{id}`) | Correcto: otra persona recibe 403 `SIN_PERMISO`; tras `recibido`, 409 y el reporte nunca se borra (RN-07) |
| `GET /api/mis-reportes` solo devuelve lo propio | Correcto (filtro por `autor_id` del token, nunca por un parámetro) |
| Confirmar el reporte propio, o dos veces | 403 `ES_TU_REPORTE` y 409 `YA_CONFIRMADO`; la restricción única de la base frena dos clics simultáneos |
| Privacidad (RN-04): ninguna respuesta pública trae al autor | Correcto: los serializadores copian campo por campo; las pruebas recorren el JSON de todas las respuestas y los esquemas de `/docs` buscando `autor_id`, `correo`, `actor_id`, etc. El 409 de duplicado tampoco revela al autor del reporte cercano |

## A02 — Criptografía y configuración

| Qué se revisó | Resultado |
|---|---|
| Contraseñas con bcrypt; el hash nunca sale | Correcto: ninguna respuesta (ni registro ni login) contiene el hash ni la contraseña |
| JWT firmado con `SECRET_KEY` de entorno; algoritmo fijo (sin `alg: none`); token vencido o alterado → 401 | Correcto |
| En producción no arranca con la clave de ejemplo | Correcto (`core/config.py`) |
| CORS limitado a `CORS_ORIGINS` (nunca `*`) | Correcto |
| Cabeceras de seguridad | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` y `Cache-Control: no-store` ya estaban. **Faltaba HSTS**: se agregó solo en producción |
| Errores 500 sin detalles técnicos | Correcto (`core/errores.py`) |
| Nominatim: User-Agent genérico, sin datos personales en la URL | Correcto: solo viaja el texto de la dirección o las coordenadas |

## Qué se corrigió

1. `fix(seguridad)`: cabecera `Strict-Transport-Security` en producción.
2. `fix(geo)`: la fila de espera hacia Nominatim tenía turno ilimitado; con muchas búsquedas a la vez cada petición ocupaba un
   hilo del servidor esperando y podía dejar sin hilos al resto de la API. Ahora espera como máximo 3 s (`GEO_ESPERA_MAX_S`)
   y responde 503; lo que ya está en caché no hace fila.

## Pendientes (fuera de A01/A02 o decisión del equipo)

- No hay límite de intentos en `POST /api/auth/login` (fuerza bruta, OWASP A07). Sugerencia: contar intentos fallidos por
  correo en la base, igual que el límite de reportes por hora.
- `/docs` y `/openapi.json` quedan públicos también en producción. Se dejan para la revisión del proyecto; se pueden apagar con
  `FastAPI(docs_url=None, openapi_url=None)` si el equipo lo decide.
- Los endpoints de moderación, administración y tablero (Carlos) deben sumarse a la matriz de `test_seguridad.py` al llegar.

# Liebre Urbana — Checklist de entrega

> Lista de verificación escrita al planear. Sus casillas no se mantuvieron: el estado final está en [`../AUTOEVALUACION.md`](../AUTOEVALUACION.md) y en el reporte.

Cada criterio de la rúbrica (100 puntos, 11 criterios) con el nivel al que apuntamos, la evidencia que lo respalda y quién la
produce. **Un nivel sin evidencia enlazada se toma como Insuficiente**, así que la evidencia se va guardando mientras se construye.

## 1. Requisitos de entrada (si falta uno, no se evalúa)

- [ ] Repositorio de la organización (`tecnm-itcj/aeb-1055-programacion-web-u5-final-group-3`, donde el docente `dr-roberto-contreras-itcj` ya es colaborador) con `main` completo y la etiqueta **`v1.0.0`**.
- [ ] `docker compose up` levanta frontend, backend y base de datos sin pasos manuales (salvo copiar `.env.example` a `.env`).
- [ ] `AI_USAGE.md` presente y completo.
- [ ] Autoevaluación con la rúbrica al final del reporte y en `docs/AUTOEVALUACION.md`.

## 2. Rúbrica

| # | Criterio (peso) | Meta | Evidencia | Responsable | Listo |
|---|---|---|---|---|---|
| 1 | Planeación y arquitectura (6) | Excelente | `docs/arquitectura.png` fiel al sistema real; 34 historias con CA en issues; tablero de GitHub Projects actualizado durante el miércoles; justificación del stack con fuentes (`DISENO_TECNICO.md`) | Luis (diagrama, backlog), Carlos (tablero) | ☐ |
| 2 | HTML semántico, CSS y responsividad (8) | Excelente | Capturas en 360 px y escritorio; `header/nav/main/section/footer` en cada vista; Lighthouse accesibilidad ≥ 90 guardado en `docs/lighthouse/` | Carlos | ☐ |
| 3 | Frontend en React (14) | Excelente | Componentes reutilizables con props, más de 4 rutas, `useState`/`useEffect`, estados de carga, error y vacío en todas las vistas, validación en cliente, formulario dinámico de HU-02.2 | Ambos | ☐ |
| 4 | Backend en FastAPI (14) | Excelente | 36 endpoints con métodos y códigos HTTP correctos, Pydantic en entrada y salida, capas separadas, `/docs` descriptivo (captura) | Ambos | ☐ |
| 5 | Base de datos (12) | Excelente | Diagrama ER (`db/er.png`), relaciones 1:N y N:M, migraciones Alembic reproducibles, semilla, restricciones, CRUD completo en colonias, usuarios y reportes | Luis | ☐ |
| 6 | Seguridad e interoperabilidad (10) | Excelente | bcrypt, JWT, autorización por rol demostrada con un 403 en la demo, CORS restringido, **cero secretos en el historial** (revisión con búsqueda antes de etiquetar), API externa con manejo de fallas | Luis | ☐ |
| 7 | Contenedores y despliegue (10) | Excelente | `docker compose up` al primer intento; URL pública estable en Vercel + Render + Neon; variables de entorno separadas | Luis (Docker, CI y nube) | ☐ |
| 8 | Calidad y flujo DevOps (8) | Excelente | ≥ 25 pruebas `pytest` en verde, CI en verde, **PRs revisados por la otra persona**, Conventional Commits, commits de ambos repartidos desde el miércoles a mediodía | Ambos | ☐ |
| 9 | Declaración de uso de IA (5) | Excelente | `AI_USAGE.md` con los 7 puntos, archivos de contexto en el repo (`CLAUDE.md`), commits marcados, reflexión con un caso concreto | Ambos (Luis arma el archivo final) | ☐ |
| 10 | Reporte técnico (5) | Excelente | `docs/REPORTE.pdf` (≤ 20 páginas) con las cuatro fases, figuras, referencias APA 7 y autoevaluación con evidencia enlazada en cada fila | Ambos | ☐ |
| 11 | Demo y defensa individual (8) | Excelente | Demo de 8 min fluida; cada persona explica cualquier parte y el flujo completo de una petición | Ambos | ☐ |
| Extra | Puntos extra (hasta +5) | Mapa, XML y Vitest | HU-04.5, HU-07.3 con XSD, pruebas de Vitest en CI | Carlos | ☐ |

## 3. Contenido que debe tener el repositorio

| Archivo | Responsable | Listo |
|---|---|---|
| `README.md`: problema, integrantes y roles, URL pública, `docker compose up`, usuarios de prueba (uno por rol), insignia de CI | Luis | ☐ |
| `AI_USAGE.md` y `docs/ai/bitacora-*.md` | Ambos | ☐ |
| `.env.example` (nunca `.env`) | Luis | ☐ |
| `.github/workflows/ci.yml` | Luis | ☐ |
| `docs/arquitectura.png`, `db/er.png` | Luis | ☐ |
| `docs/REPORTE.pdf` y `docs/AUTOEVALUACION.md` | Ambos | ☐ |
| `docs/lighthouse/` y capturas en móvil y escritorio | Carlos | ☐ |
| `db/datos/FUENTE.md` con la fuente del catálogo de colonias | Luis | ☐ |

## 4. Reporte técnico: quién escribe qué

| Sección | Escribe | Fuente en el repo |
|---|---|---|
| Portada (con número de control y rol de cada integrante) | Luis | — |
| Fundamentación: problema, usuarios, similares, alcance | Carlos | `BACKLOG.md`, carta del cliente |
| Planeación: historias, tablero, **cronograma real**, arquitectura, stack, modelo ER | Luis | `docs/plan/` |
| Ejecución: frontend y contenedores | Carlos | `frontend/`, `infra/` |
| Ejecución: backend, base de datos, seguridad y despliegue | Luis | `backend/`, `db/` |
| Evaluación: pruebas, Lighthouse, problemas, lecciones, trabajo futuro | Carlos | CI, `docs/lighthouse/` |
| Uso de IA: resumen y reflexión | Luis | `AI_USAGE.md` |
| Contribución individual (commits y PRs por persona, porcentaje acordado) | Ambos | `git shortlog`, PRs |
| Coevaluación entre pares (puede ser privada) | Cada quien la suya | — |
| Referencias APA 7 | Ambos | Requerimientos, OWASP, Twelve-Factor, Conventional Commits, documentación oficial |
| Autoevaluación con rúbrica y un párrafo por integrante | Ambos | Este archivo |

El **cronograma real** del reporte sale del historial de PRs y del tablero; por eso no se maquilla: se toma tal como pasó.

## 5. Revisión final antes de etiquetar (jueves)

- [ ] `main` con CI en verde.
- [ ] Búsqueda de secretos en todo el historial (`git log -p` con patrones de claves y cadenas de conexión) y revisión de `.env` ignorado.
- [ ] Ningún dato personal real en la semilla; ningún documento del docente en el repo.
- [ ] `docker compose up` desde una carpeta limpia (clon nuevo) con cronómetro: < 3 minutos con imágenes construidas.
- [ ] URL pública abierta desde un dispositivo distinto; registro, login y reporte funcionan.
- [ ] Una respuesta pública, la exportación y el resumen revisados a mano: sin nombre ni correo.
- [ ] Un 403 mostrado en `/docs` con una cuenta de ciudadano.
- [ ] Lighthouse ≥ 90 en las vistas principales.
- [ ] Etiqueta `v1.0.0` creada **antes** de la hora de entrega y el docente puede verla.

## 6. Demo

- [ ] Cuentas de demo verificadas (ciudadano, moderador, coordinador).
- [ ] Encharcamiento nuevo creado en vivo; bache a 30 m para mostrar el duplicado.
- [ ] 10 minutos antes: abrir el frontend y llamar `/api/health` para despertar Render y Neon.
- [ ] Plan B probado: `docker compose up` en la laptop.
- [ ] Ensayo cruzado hecho: cada quien explicó una historia de la otra persona, del clic en React a la consulta en PostgreSQL.

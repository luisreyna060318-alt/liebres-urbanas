# Bitácora de IA — Carlos Limones Ayala

Una fila por prompt significativo. Se consolida en `AI_USAGE.md` antes de la etiqueta `v1.0.0`.

Herramienta: Claude Code (aplicación de escritorio de Claude, pestaña Code), modelo Claude Sonnet 5.5 (`claude-sonnet-5-5`).
Los commits con código generado por la herramienta terminan con `Co-Authored-By: Claude Sonnet 5.5`.

| Fecha | Herramienta / modelo | Prompt (resumen fiel) | Archivos afectados | Ajustes humanos |
|---|---|---|---|---|
| 2026-11-25 | Claude Code / Claude Sonnet 5.5 | Clonar el repositorio `liebres-urbanas`, analizar las tareas que le tocan a Carlos Limones Ayala y armar un proyecto local con las herramientas de la computadora, sin hacer commits ni PRs todavía | Ninguno en el repositorio (copia local de L1+L2+L3 fuera del repo, con base de datos en Docker, `.env` propio y dependencias instaladas) | Carlos eligió "copia aparte, sin commits" para no tocar `main` mientras los PRs de Luis siguen abiertos |
| 2026-11-25 | Claude Code / Claude Sonnet 5.5 | Revisar y aprobar los 14 PRs de Luis; después trabajar las tareas de Carlos en PRs modulares, que revisa Luis y fusiona Carlos | Reviews en los PRs #1 a #14 (sin cambios de código); esta bitácora | Carlos fijó el flujo de trabajo. Las aprobaciones se publicaron después de leer el código, correr las pruebas de la punta de cada pila y probar el flujo de ciudadano en el navegador contra PostgreSQL real |

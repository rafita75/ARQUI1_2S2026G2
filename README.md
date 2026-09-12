# Proyecto 1 — Arquitectura de Computadores y Ensambladores 1

Grupo 2 — Arquitectura de Computadores y Ensambladores 1.

Edificio Inteligente IoT con Raspberry Pi ARM64.

## Estructura del repositorio

- `backend/` — núcleo Python (`main.py`), controladores de hardware,
  modelos de MongoDB, API REST (`api.py`) y módulo en ensamblador ARM64
  (`arm64/`).
- `frontend/` — dashboard web (HTML/JS/CSS) con MQTT y consumo de la API.
- `docs/` — documentación técnica y diagramas (arquitectura, topics MQTT,
  esquema de MongoDB, flujo Python↔ARM64, conexiones físicas).

## Documentación técnica

- [Manual técnico (informe completo)](docs/manual_tecnico.md)
- [Arquitectura del sistema](docs/arquitectura.md)
- [Topics MQTT](docs/mqtt_topics.md)
- [Esquema de MongoDB Atlas](docs/mongodb_schema.md)
- [Flujo Python → ARM64 → MongoDB → Dashboard](docs/flujo_arm64.md)
- [Diagrama de conexiones físicas (GPIO)](docs/conexiones_fisicas.md)

## Módulo ARM64

El código en ensamblador vive en `backend/arm64/logica.s`. Para compilar,
probar de forma independiente y depurar con GDB sin afectar los archivos
`datos.txt`/`resultado.txt` reales que usa `main.py`, ver
[`backend/arm64/test/README.md`](backend/arm64/test/README.md).

## Repositorio del curso

El nombre del repositorio debe ser `ARQUI1_2S2026G#` (donde `#` es el número
de grupo), y el usuario auxiliar `PoncheDeFrutas` debe ser colaborador con
acceso de lectura.

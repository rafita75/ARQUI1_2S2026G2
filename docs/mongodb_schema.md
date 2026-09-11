# Esquema de MongoDB Atlas

Base de datos: `proyecto1`.

## Colecciones actualmente implementadas

| Colección real | Modelo | Contenido | Equivalente pedido en el enunciado |
|---|---|---|---|
| `sensores` | `modelo_lecturas.py` → `LecturaSchema` | `sensor`, `tipo`, `valor`, `unidad`, `timestamp` | `sensor_readings` |
| `eventos` | `modelo_eventos.py` → `EventoSchema` | `tipo_evento`, `descripcion`, `severidad`, `timestamp` | `events` |
| `estados` | `modelo_estado.py` → `EstadoSchema` | `estado_global`, `motivo`, `puerta_abierta`, `ventilador_encendido`, `luces_encendidas`, `alarma_activa`, `timestamp` | `system_status` |
| (colección de `modelo_arm64.py`) | `Arm64Schema` | `maximo`, `minimo`, `promedio`, `total_datos`, `tiempo_ms` | `arm64_results` |
| `comandos` (modelo definido, **no usado aún** en `main.py`) | `modelo_comandos.py` → `ComandoSchema` | `actuador`, `accion`, `origen`, `timestamp` | `commands` |

## Nota sobre nombres

El enunciado especifica los nombres literales `sensor_readings`, `events`,
`commands`, `arm64_results`, `system_status`. El proyecto usa nombres en
español (`sensores`, `eventos`, `estados`, etc.) que cumplen funcionalmente
el mismo propósito. Se documenta aquí la equivalencia para la defensa
técnica; si se prefiere alinear los nombres literales, ese cambio debe
hacerse en los archivos `modelo_*.py` y probarse contra la base real antes
de la entrega.

## Comandos desde botón físico

Actualmente `main.py` ejecuta las acciones de los botones físicos
(`accion_btn_puerta`, `accion_btn_luces`, `accion_btn_silenciar`,
`accion_btn_reset`) pero no llama a `ComandosModel.guardar(...)` para
dejarlas registradas en la colección de comandos — solo quedan registradas
como eventos cuando el propio controlador (`ctrl_acceso`, `ctrl_luces`,
`ctrl_clima`) genera un `EventoSchema`. El enunciado pide que la colección de
comandos incluya explícitamente los originados desde el panel físico, no
solo desde el dashboard. Es un cambio pendiente en `main.py`.

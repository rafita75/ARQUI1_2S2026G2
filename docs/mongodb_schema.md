# Esquema de MongoDB Atlas

Base de datos: `proyecto1`.

## Colecciones actualmente implementadas

| Colección real | Modelo | Contenido | Equivalente pedido en el enunciado |
|---|---|---|---|
| `sensores` | `modelo_lecturas.py` → `LecturaSchema` | `sensor`, `tipo`, `valor`, `unidad`, `timestamp` | `sensor_readings` |
| `eventos` | `modelo_eventos.py` → `EventoSchema` | `tipo_evento`, `descripcion`, `severidad`, `timestamp` | `events` |
| `estados` | `modelo_estado.py` → `EstadoSchema` | `estado_global`, `motivo`, `puerta_abierta`, `ventilador_encendido`, `luces_encendidas`, `alarma_activa`, `timestamp` | `system_status` |
| `arm64` | `modelo_arm64.py` → `Arm64Schema` | `maximo`, `minimo`, `promedio`, `total_datos`, `tiempo_ms` | `arm64_results` |
| `comandos` | `modelo_comandos.py` → `ComandoSchema` | `actuador`, `accion`, `origen` (`"Botón Físico"` \| `"Dashboard Web"`), `timestamp` | `commands` |

## Nota sobre nombres

El enunciado especifica los nombres literales `sensor_readings`, `events`,
`commands`, `arm64_results`, `system_status`. El proyecto usa nombres en
español (`sensores`, `eventos`, `estados`, etc.) que cumplen funcionalmente
el mismo propósito. Se documenta aquí la equivalencia para la defensa
técnica; si se prefiere alinear los nombres literales, ese cambio debe
hacerse en los archivos `modelo_*.py` y probarse contra la base real antes
de la entrega.

## Comandos desde botón físico y desde el dashboard

`main.py` registra cada comando (botón físico o MQTT del dashboard) en la
colección `comandos` mediante `registrar_comando(actuador, accion, origen)`,
un helper que envuelve `ComandosModel.guardar(...)`:

- **Botón físico** (`accion_btn_puerta`, `accion_btn_luces`,
  `accion_btn_silenciar`, `accion_btn_reset`): se registra con
  `origen="Botón Físico"`.
- **Dashboard** (`al_recibir_mensaje`, para los topics `comandos/puerta`,
  `comandos/luces`, `comandos/ventilador`): se registra con
  `origen="Dashboard Web"`.
- **Seguridad** (`accion_btn_silenciar`/`accion_btn_reset`) se reutiliza
  tanto para el botón físico como para el topic `comandos/seguridad` del
  dashboard; el `origen` se pasa como parámetro para que quede correctamente
  etiquetado según quién disparó la acción.

Esto además sigue guardando eventos vía `EventoSchema` en cada controlador
(comportamiento previo sin cambios) — la colección `comandos` es un registro
adicional, no un reemplazo.

Confirmado funcionando en la Raspberry Pi real.

# Comunicación MQTT

Broker utilizado: `broker.emqx.io` (EMQX público), puerto 1883 desde la
Raspberry Pi y `wss://broker.emqx.io:8084/mqtt` desde el navegador
(WebSockets).

## Topics actualmente implementados

| Topic | Dirección | Payload | Publicado/consumido en |
|---|---|---|---|
| `grupo2/edificio/sensores` | Pi → Dashboard | JSON con temperatura, humedad, gas, distancia, luz, estado global y estado de actuadores | `backend/main.py` (publica) / `frontend/script.js` (consume) |
| `grupo2/edificio/comandos/puerta` | Dashboard → Pi | `ABRIR` \| `CERRAR` | `frontend/script.js` (publica) / `backend/main.py` (consume) |
| `grupo2/edificio/comandos/luces` | Dashboard → Pi | `ENCENDER` \| `APAGAR` \| `AUTO` | `frontend/script.js` (publica) / `backend/main.py` (consume) |
| `grupo2/edificio/comandos/ventilador` | Dashboard → Pi | `ENCENDER` \| `APAGAR` \| `AUTO` | `frontend/script.js` (publica) / `backend/main.py` (consume) |
| `grupo2/edificio/comandos/seguridad` | Dashboard → Pi | `SILENCIAR` \| `RESET` | `frontend/script.js` (publica) / `backend/main.py` (consume) |

## Topics pedidos por el enunciado y su estado actual

El enunciado (sección 7, "Comunicación MQTT obligatoria") pide como mínimo
topics separados por sensor/actuador y un topic para resultados de ARM64.
Estado actual frente a esa lista:

| Topic del enunciado | Estado |
|---|---|
| `edificio/sensores/temperatura` | Cubierto de forma agregada dentro de `grupo2/edificio/sensores` |
| `edificio/sensores/humedad` | Cubierto de forma agregada dentro de `grupo2/edificio/sensores` |
| `edificio/sensores/gas` | Cubierto de forma agregada dentro de `grupo2/edificio/sensores` |
| `edificio/sensores/distancia` | Cubierto de forma agregada dentro de `grupo2/edificio/sensores` |
| `edificio/sensores/luz` | Cubierto de forma agregada dentro de `grupo2/edificio/sensores` |
| `edificio/actuadores/puerta` | No implementado como topic de estado (solo como topic de comando) |
| `edificio/actuadores/luces` | No implementado como topic de estado (solo como topic de comando) |
| `edificio/actuadores/ventilador` | Comando implementado (`grupo2/edificio/comandos/ventilador`); falta topic de estado dedicado |
| `edificio/actuadores/alarma` | Comando de silenciar/reset implementado (`grupo2/edificio/comandos/seguridad`); falta topic de estado dedicado |
| `edificio/estado/global` | Incluido dentro del payload de `grupo2/edificio/sensores`, no como topic propio |
| `edificio/control/remoto` | Implementado como sub-topics `grupo2/edificio/comandos/<dispositivo>` |
| `edificio/arm64/resultados` | **Pendiente** — el resultado ARM64 solo se guarda en MongoDB y se sirve por REST (`/api/historial/arm64/...`), no se publica por MQTT |

> Nota: el sistema actual sí usa MQTT como medio de comunicación real (no lo
> sustituye por llamadas directas), pero para cumplir literalmente la lista
> mínima de topics del enunciado todavía falta: separar los topics de
> sensores y publicar el estado de los actuadores, del estado global y del
> resultado ARM64 en sus propios topics dedicados. Los comandos de
> `ventilador` y `seguridad` (silenciar/reset) ya se agregaron a `main.py`
> — pendiente confirmar en la Raspberry Pi real.

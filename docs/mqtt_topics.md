# Comunicación MQTT

Broker utilizado: `broker.emqx.io` (EMQX público), puerto 1883 desde la
Raspberry Pi y `wss://broker.emqx.io:8084/mqtt` desde el navegador
(WebSockets).

## Topics actualmente implementados

Todos bajo el prefijo `grupo2/edificio/...` (mismo prefijo que ya usaba el
proyecto para identificar al grupo, equivalente al `edificio/...` genérico
del enunciado).

| Topic | Dirección | Payload | Publicado/consumido en |
|---|---|---|---|
| `grupo2/edificio/sensores` | Pi → Dashboard | JSON combinado (todas las lecturas + estado global + estado de actuadores) | `backend/main.py` (publica) / `frontend/script.js` (consume) |
| `grupo2/edificio/sensores/temperatura` | Pi → Dashboard | Valor numérico como texto | `backend/main.py` (publica) |
| `grupo2/edificio/sensores/humedad` | Pi → Dashboard | Valor numérico como texto | `backend/main.py` (publica) |
| `grupo2/edificio/sensores/gas` | Pi → Dashboard | Valor numérico (ADC 0-255) como texto | `backend/main.py` (publica) |
| `grupo2/edificio/sensores/distancia` | Pi → Dashboard | Valor numérico (cm) como texto | `backend/main.py` (publica) |
| `grupo2/edificio/sensores/luz` | Pi → Dashboard | Valor numérico (ADC 0-255) como texto | `backend/main.py` (publica) |
| `grupo2/edificio/actuadores/puerta` | Pi → Dashboard | `Abierta` \| `Cerrada` | `backend/main.py` (publica) |
| `grupo2/edificio/actuadores/luces` | Pi → Dashboard | `Encendidas` \| `Apagadas` | `backend/main.py` (publica) |
| `grupo2/edificio/actuadores/ventilador` | Pi → Dashboard | `Encendido` \| `Apagado` | `backend/main.py` (publica) |
| `grupo2/edificio/actuadores/alarma` | Pi → Dashboard | `Silenciada` \| `Activada` \| `Inactiva` | `backend/main.py` (publica) |
| `grupo2/edificio/estado/global` | Pi → Dashboard | `NORMAL` \| `ADVERTENCIA` \| `EMERGENCIA` | `backend/main.py` (publica) |
| `grupo2/edificio/arm64/resultados` | Pi → Dashboard | JSON: `maximo`, `minimo`, `promedio`, `total_datos`, `tiempo_ms` | `backend/main.py` (publica, justo después de guardarlo en MongoDB) |
| `grupo2/edificio/comandos/puerta` | Dashboard → Pi | `ABRIR` \| `CERRAR` | `frontend/script.js` (publica) / `backend/main.py` (consume) |
| `grupo2/edificio/comandos/luces` | Dashboard → Pi | `ENCENDER` \| `APAGAR` \| `AUTO` | `frontend/script.js` (publica) / `backend/main.py` (consume) |
| `grupo2/edificio/comandos/ventilador` | Dashboard → Pi | `ENCENDER` \| `APAGAR` \| `AUTO` | `frontend/script.js` (publica) / `backend/main.py` (consume) |
| `grupo2/edificio/comandos/seguridad` | Dashboard → Pi | `SILENCIAR` \| `RESET` | `frontend/script.js` (publica) / `backend/main.py` (consume) |

Los topics granulares de sensores/actuadores/estado se publican **además**
del payload combinado (mismo intervalo de 2 segundos, mismo bloque de
código en `main.py`), no lo reemplazan — así el dashboard actual, que ya
consume el payload combinado, sigue funcionando sin cambios mientras se
actualiza para aprovechar los topics individuales si se quiere.

## Comparación contra la lista mínima del enunciado

| Topic del enunciado | Estado |
|---|---|
| `edificio/sensores/temperatura` | ✅ `grupo2/edificio/sensores/temperatura` |
| `edificio/sensores/humedad` | ✅ `grupo2/edificio/sensores/humedad` |
| `edificio/sensores/gas` | ✅ `grupo2/edificio/sensores/gas` |
| `edificio/sensores/distancia` | ✅ `grupo2/edificio/sensores/distancia` |
| `edificio/sensores/luz` | ✅ `grupo2/edificio/sensores/luz` |
| `edificio/actuadores/puerta` | ✅ `grupo2/edificio/actuadores/puerta` |
| `edificio/actuadores/luces` | ✅ `grupo2/edificio/actuadores/luces` |
| `edificio/actuadores/ventilador` | ✅ `grupo2/edificio/actuadores/ventilador` |
| `edificio/actuadores/alarma` | ✅ `grupo2/edificio/actuadores/alarma` |
| `edificio/estado/global` | ✅ `grupo2/edificio/estado/global` |
| `edificio/control/remoto` | ✅ Implementado como sub-topics `grupo2/edificio/comandos/<dispositivo>` |
| `edificio/arm64/resultados` | ✅ `grupo2/edificio/arm64/resultados` (además de seguir guardándose en MongoDB y sirviéndose por REST, sin cambios ahí) |

> Los 12 topics mínimos del enunciado ya están cubiertos. Probado con el
> simulador de hardware (incluyendo un `subprocess.run` simulado para el
> binario ARM64, ya que ese binario solo corre en Linux ARM64) — pendiente
> confirmar en la Raspberry Pi real con el binario y el hardware reales.

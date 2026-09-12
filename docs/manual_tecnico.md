# Manual Técnico — Edificio Inteligente IoT con Raspberry Pi ARM64

Arquitectura de Computadores y Ensambladores 1 — Proyecto 1

## Índice

1. [Introducción](#1-introducción)
2. [Arquitectura general del sistema](#2-arquitectura-general-del-sistema)
3. [Modelo de datos (MongoDB Atlas)](#3-modelo-de-datos-mongodb-atlas)
4. [Comunicación MQTT](#4-comunicación-mqtt)
5. [Subsistemas del edificio](#5-subsistemas-del-edificio)
6. [Panel de control físico](#6-panel-de-control-físico)
7. [Dashboard web](#7-dashboard-web)
8. [Módulo de procesamiento en ensamblador ARM64](#8-módulo-de-procesamiento-en-ensamblador-arm64)
9. [Flujo completo del sistema](#9-flujo-completo-del-sistema)
10. [Decisiones de diseño](#10-decisiones-de-diseño)
11. [Estado del proyecto](#11-estado-del-proyecto)

---

## 1. Introducción

Este documento describe la implementación técnica del sistema IoT de control
y monitoreo para una maqueta de edificio inteligente, construido sobre una
Raspberry Pi con sistema Linux ARM64. El sistema integra sensores,
actuadores, comunicación MQTT, persistencia en MongoDB Atlas, un dashboard
web y un módulo de procesamiento numérico escrito en ensamblador AArch64.

El código fuente se organiza en:

```
backend/
  main.py                  Núcleo del sistema (bucle principal)
  api.py                   API REST para el dashboard
  controllers/              Un controlador por subsistema físico
  models/                   Esquemas y acceso a MongoDB Atlas
  view/lcd_view.py          Manejo de la pantalla LCD
  arm64/logica.s            Módulo en ensamblador AArch64
  arm64/Makefile            Compilación del módulo ARM64
  arm64/test/               Pruebas independientes del módulo ARM64
frontend/
  index.html, script.js, styles.css   Dashboard web
docs/
  Documentación técnica y diagramas (este manual y sus anexos)
```

## 2. Arquitectura general del sistema

El sistema sigue una arquitectura de tres capas: **hardware/GPIO** (sensores
y actuadores controlados directamente por la Raspberry Pi), **núcleo de
control** (`main.py` y sus controladores en Python) y **servicios en la
nube** (broker MQTT EMQX y MongoDB Atlas), consumidos por un **dashboard
web** independiente.

Diagrama completo de componentes y su interacción:
[`docs/arquitectura.md`](arquitectura.md).

Diagrama de conexiones físicas (pines GPIO/I2C):
[`docs/conexiones_fisicas.md`](conexiones_fisicas.md).

## 3. Modelo de datos (MongoDB Atlas)

Base de datos: `proyecto1`. Cada subsistema guarda sus lecturas y eventos a
través de un modelo dedicado (`backend/models/*.py`), usando `dataclasses`
serializadas con `asdict()`.

| Colección | Esquema | Campos |
|---|---|---|
| `sensores` | `LecturaSchema` | `sensor`, `tipo`, `valor`, `unidad`, `timestamp` |
| `eventos` | `EventoSchema` | `tipo_evento`, `descripcion`, `severidad`, `timestamp` |
| `estados` | `EstadoSchema` | `estado_global`, `motivo`, `puerta_abierta`, `ventilador_encendido`, `luces_encendidas`, `alarma_activa`, `timestamp` |
| `arm64` | `Arm64Schema` | `maximo`, `minimo`, `promedio`, `total_datos`, `tiempo_ms` |
| `comandos` | `ComandoSchema` | `actuador`, `accion`, `origen` (`"Botón Físico"` \| `"Dashboard Web"`), `timestamp` |

Detalle completo, incluyendo la equivalencia con los nombres de colección
que pide el enunciado (`sensor_readings`, `events`, `commands`,
`arm64_results`, `system_status`): [`docs/mongodb_schema.md`](mongodb_schema.md).

## 4. Comunicación MQTT

Broker: EMQX público (`broker.emqx.io`), puerto `1883` desde la Raspberry Pi
y WebSockets (`wss://broker.emqx.io:8084/mqtt`) desde el navegador.

- La Raspberry Pi publica un payload JSON combinado con todas las lecturas y
  el estado de los actuadores en `grupo2/edificio/sensores`, además de un
  topic individual por sensor, actuador, estado global y resultado ARM64.
- El dashboard publica comandos en `grupo2/edificio/comandos/<dispositivo>`
  para puerta, luces, ventilador y seguridad (silenciar/reset), todos
  conectados en el backend.
- El estado global se transmite tanto embebido en el payload de sensores
  como en su propio topic (`grupo2/edificio/estado/global`).

Listado completo de topics y su correspondencia con los mínimos del
enunciado: [`docs/mqtt_topics.md`](mqtt_topics.md).

## 5. Subsistemas del edificio

### 5.1 Monitoreo ambiental (`ctrl_clima.py`)
- Sensor DHT11 (pin GPIO4), ventilador (GPIO5) y LED indicador (GPIO6).
- Lectura cada 2 segundos; sube a MongoDB cada 10 segundos.
- Umbral de encendido: temperatura ≥ 28.0 °C. Umbral de apagado: ≤ 26.5 °C
  (histéresis para evitar parpadeo del ventilador).
- Maneja errores de lectura del DHT11 reutilizando el último valor válido y
  reiniciando el sensor tras 8 fallos consecutivos.

### 5.2 Detección de gas o humo (`ctrl_seguridad.py`)
- Sensor MQ-2 leído vía ADC PCF8591 (I2C, dirección `0x48`, canal `AIN1`).
- Buzzer (GPIO16) y LED rojo (GPIO26).
- Umbral de peligro: valor ADC > 180/255 → activa alarma y reporta
  `EMERGENCIA`. Umbral seguro: < 100/255 → desactiva alarma.
- El estado `EMERGENCIA` se mantiene mientras la lectura no baje del umbral
  seguro (no vuelve a `NORMAL` mientras persista el peligro), según lo exige
  el enunciado.

### 5.3 Acceso automatizado (`ctrl_acceso.py`)
- HC-SR04 (TRIG en GPIO23, ECHO en GPIO24), servomotor (GPIO12, PWM 50 Hz).
- Filtro de mediana sobre 5 muestras para reducir ruido en la medición de
  distancia.
- Si la distancia es menor a 10 cm, abre la puerta automáticamente
  (barrido suave de 0° a 90°); se cierra sola a los 5 segundos.
- También se puede abrir/cerrar desde el botón físico (GPIO17) y desde el
  dashboard (topic `grupo2/edificio/comandos/puerta`).

### 5.4 Iluminación inteligente (`ctrl_luces.py`)
- Sensor LDR leído vía ADC PCF8591 (I2C, canal `AIN0`).
- 3 LEDs distribuidos en pines GPIO21, GPIO18 y GPIO14.
- Umbral de encendido: luz < 180/255. Umbral de apagado: > 130/255.
- Modo automático/manual controlado por el botón físico (GPIO27) o desde el
  dashboard (`AUTO`, `ENCENDER`, `APAGAR`).

### 5.5 Estado global y alarmas (`main.py`)
- LED verde (GPIO13) = `NORMAL`, LED amarillo (GPIO19) = `ADVERTENCIA`, LED
  rojo (GPIO26, compartido con la alarma de gas) = `EMERGENCIA`.
- Reglas de transición evaluadas en el bucle principal:
  - `EMERGENCIA` si el subsistema de gas reporta ese estado (gas > umbral).
    Al entrar en emergencia se abre la puerta automáticamente y se fuerzan
    las luces encendidas, simulando evacuación.
  - `ADVERTENCIA` si el ventilador está encendido (temperatura alta) o la
    humedad está fuera de rango (≥ 70% o ≤ 30%).
  - `NORMAL` en cualquier otro caso.
- El estado se persiste en MongoDB (colección `estados`) cuando cambia o
  cada 60 segundos como máximo.

### 5.6 Panel de control físico
Ver sección 6.

## 6. Panel de control físico

- **Pantalla LCD 16x2** (I2C, dirección `0x27`), gestionada por
  `backend/view/lcd_view.py`. Rota cada 2 segundos entre: temperatura y
  humedad, nivel de gas, distancia, nivel de luz, estado de la puerta y
  estado global — cumpliendo el requisito de mostrar toda esa información
  de forma rotativa.
- **4 botones físicos** (polling por software en `main.py`, detectando
  flanco de subida):
  - GPIO17 — abrir/cerrar puerta.
  - GPIO27 — alternar modo de iluminación AUTOMÁTICO/MANUAL (y alternar
    encendido si está en manual).
  - GPIO22 — silenciar el buzzer (sin apagar la causa de la alarma).
  - GPIO25 — restablecer alertas, solo si las condiciones de peligro
    (gas < 180, temperatura < 28 °C) ya no están presentes.

## 7. Dashboard web

`frontend/index.html` + `frontend/script.js`, sin backend propio (archivos
estáticos servidos desde cualquier servidor HTTP simple o directamente
abiertos en el navegador).

- **Tiempo real**: se conecta al broker EMQX por WebSockets y actualiza en
  vivo temperatura, humedad, gas, distancia, luz, estado de actuadores y
  estado global a partir del payload MQTT combinado.
- **Gráficas** (Chart.js): temperatura, humedad, gas, distancia, luz y
  promedios históricos del módulo ARM64, alimentadas por la API REST
  (`backend/api.py`) que consulta MongoDB.
- **Controles remotos**: puerta, luces (on/off/auto), ventilador
  (on/off/auto) y seguridad (silenciar/reset), todos conectados de punta a
  punta con el backend vía MQTT.
- **Historial**: últimos eventos, últimos comandos remotos y últimos
  resultados del módulo ARM64, todo vía REST (`/api/historial/...`).

## 8. Módulo de procesamiento en ensamblador ARM64

Implementado íntegramente en `backend/arm64/logica.s` (AArch64, syscalls de
Linux directas: `openat`, `read`, `write`, `close`, `exit`).

**Algoritmo:**
1. Abre `datos.txt` en el directorio de trabajo actual.
2. Lee su contenido completo a un buffer de 1024 bytes.
3. Recorre byte a byte: acumula dígitos de un número en curso; al encontrar
   `\n` o `\r` cierra el número y actualiza máximo (`x19`), mínimo (`x20`),
   suma (`x21`) y contador (`x22`); al encontrar `$` cierra el último número
   pendiente (si existe) y termina el análisis.
4. Calcula el promedio truncado con división entera (`udiv`).
5. Escribe `resultado.txt` con el formato exacto `MÁX=`, `MIN=`, `AVG=`,
   `COUNT=`, usando una subrutina propia (`write_int_to_file`) que convierte
   enteros a texto ASCII sin depender de la librería C.

**Restricción cumplida:** todo el cálculo ocurre en ensamblador; Python
(`main.py`) solo genera `datos.txt`, ejecuta el binario vía `subprocess.run`,
lee `resultado.txt` y guarda el resultado en MongoDB.

**Compilación:** `backend/arm64/Makefile` (`make` compila con `as`/`ld`;
`make test` corre el binario contra datos de prueba conocidos en un
directorio aislado; `make debug` recompila con símbolos y abre GDB).

**Pruebas independientes y evidencia de depuración:**
[`backend/arm64/test/README.md`](../backend/arm64/test/README.md), con dos
casos de prueba (`datos.txt` de 4 valores tomado del propio enunciado, y
`datos_extra.txt` de 10 valores) y sus resultados esperados.

Diagrama de secuencia del flujo completo:
[`docs/flujo_arm64.md`](flujo_arm64.md).

## 9. Flujo completo del sistema

```
Sensor DHT11 (temperatura real)
  → main.py acumula 20 lecturas (una cada 2s)
  → escribe datos.txt (enteros + "$")
  → ejecuta backend/arm64/calculos_arm
  → logica.s calcula MÁX/MIN/AVG/COUNT
  → escribe resultado.txt
  → main.py parsea resultado.txt
  → guarda en MongoDB Atlas (colección de resultados ARM64)
  → dashboard consulta vía API REST (backend/api.py)
  → se muestra en el panel principal, gráfica y tabla de historial
```

## 10. Decisiones de diseño

- **Filtro de mediana en el sensor ultrasónico**: se prefirió mediana sobre
  promedio para descartar outliers producidos por reflexiones erráticas del
  HC-SR04, sin suavizar en exceso la respuesta del sistema.
- **Histéresis en umbrales de temperatura y luz**: evita que el ventilador o
  las luces oscilen rápidamente cuando la lectura está justo en el límite.
- **Payload MQTT combinado además de topics individuales**: el combinado
  simplifica la sincronización en el dashboard (una sola suscripción, un
  solo `render`); los topics individuales por sensor/actuador/estado se
  agregaron para cumplir la granularidad mínima del enunciado sin quitar el
  combinado, evitando romper el dashboard existente.
- **Cálculo 100% en ensamblador**: se usan syscalls directas de Linux
  (`openat`/`read`/`write`) en vez de la libc, para evidenciar manejo de
  bajo nivel real sin depender de un runtime de C.

## 11. Estado del proyecto

Checklist frente a los requisitos obligatorios del enunciado. Todos los
puntos de código están implementados y confirmados funcionando en la
Raspberry Pi real:

- [x] Subsistemas de clima, gas, acceso y luces funcionando end-to-end.
- [x] Panel físico (LCD + 4 botones).
- [x] Módulo ARM64 completo, con Makefile y pruebas independientes.
- [x] Dashboard con panel principal, gráficas, controles e historial.
- [x] Flujo Python → ARM64 → MongoDB → Dashboard demostrable.
- [x] Comandos de `ventilador` y `seguridad` desde el dashboard, con modo
      manual/automático para el ventilador (igual que las luces).
- [x] Umbral de humedad como segunda causa de `ADVERTENCIA`.
- [x] Topics MQTT granulares por sensor, actuador, estado global y
      resultado ARM64 — ver [`mqtt_topics.md`](mqtt_topics.md). Los 12
      topics mínimos del enunciado están cubiertos.
- [x] Colección `comandos` registra tanto los comandos del botón físico
      como los del dashboard, con su `origen` correcto — ver
      [`mongodb_schema.md`](mongodb_schema.md).
- [x] LED rojo ligado explícitamente al estado global `EMERGENCIA`.

Único punto que se decidió no cambiar, por diseño:

- Los nombres de las colecciones de MongoDB (`sensores`, `eventos`,
  `estados`, `arm64`, `comandos`) no se renombraron a los literales del
  enunciado (`sensor_readings`, `events`, etc.) para no arriesgar el
  historial ya guardado en Atlas justo antes de la entrega. La equivalencia
  queda documentada en [`mongodb_schema.md`](mongodb_schema.md) para la
  defensa técnica.

Pendientes fuera del código (maqueta física, evidencias en video/capturas,
documentación de participación del equipo) se coordinan directamente con el
equipo, no requieren cambios de software.

# Flujo Python → ARM64 → MongoDB → Dashboard

```mermaid
sequenceDiagram
    participant DHT as Sensor DHT11
    participant Py as main.py (Python)
    participant Asm as calculos_arm (ARM64)
    participant Mongo as MongoDB Atlas
    participant Dash as Dashboard Web

    loop cada 2s hasta juntar 20 lecturas
        DHT->>Py: temperatura real
        Py->>Py: acumula en temperaturas_para_arm[]
    end
    Py->>Py: escribe datos.txt (enteros + "$")
    Py->>Asm: subprocess.run(["./arm64/calculos_arm"])
    Asm->>Asm: lee datos.txt, detecta "$"
    Asm->>Asm: calcula MÁX, MIN, AVG (truncado), COUNT
    Asm-->>Py: escribe resultado.txt
    Py->>Py: parsea resultado.txt
    Py->>Mongo: guarda Arm64Schema (maximo, minimo, promedio, total_datos, tiempo_ms)
    Dash->>Mongo: GET /api/historial/arm64/promedios (vía api.py)
    Dash->>Mongo: GET /api/historial/arm64/stats (vía api.py)
    Mongo-->>Dash: últimos resultados
```

## Restricción cumplida

Todo el cálculo de máximo, mínimo, promedio y conteo se realiza en
`backend/arm64/logica.s` (AArch64), no en Python. `main.py` únicamente:

1. Genera `datos.txt` con lecturas reales de temperatura.
2. Ejecuta el binario `calculos_arm`.
3. Lee `resultado.txt`.
4. Guarda el resultado en MongoDB Atlas.

## Formato de archivos

**`datos.txt`** — un entero por línea, terminado en `$`:

```
23
25
21
27
$
```

**`resultado.txt`** — formato fijo:

```
MÁX=27
MIN=21
AVG=24
COUNT=4
```

## Pendiente

- Publicar el resultado también por MQTT en el topic `edificio/arm64/resultados`
  (ver [`mqtt_topics.md`](mqtt_topics.md)) — hoy solo llega al dashboard vía
  REST, no vía MQTT.

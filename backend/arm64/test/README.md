# Prueba independiente del módulo ARM64

Esta carpeta permite demostrar el funcionamiento del módulo ARM64 **de forma
aislada**, sin tocar los archivos `datos.txt` / `resultado.txt` reales que usa
`main.py` en producción (el binario lee siempre `datos.txt` en su directorio
de trabajo actual, por eso la prueba corre en su propia carpeta con su propia
copia del binario).

## Archivos

- `datos.txt` — caso de prueba mínimo, tomado directamente del ejemplo del
  enunciado del proyecto.
- `resultado_esperado.txt` — salida que el binario debe producir para
  `datos.txt`.
- `datos_extra.txt` — segundo caso de prueba con 10 valores, para verificar
  el cálculo con un conjunto más grande.
- `resultado_extra_esperado.txt` — salida esperada para `datos_extra.txt`.

## Cómo ejecutar la prueba (en la Raspberry Pi / entorno ARM64)

Desde `backend/arm64/`:

```bash
make test
```

Esto compila `logica.s` (si hace falta), copia el binario a `test/`, lo
ejecuta contra `test/datos.txt` y muestra el `resultado.txt` generado. Debe
coincidir con `resultado_esperado.txt`.

Para probar el segundo caso:

```bash
cd test
cp datos_extra.txt datos.txt
./calculos_arm
cat resultado.txt   # comparar contra resultado_extra_esperado.txt
```

## Evidencia a capturar (para el entregable)

1. Captura de terminal mostrando `make test` (compilación + ejecución).
2. Captura de `cat test/datos.txt` (entrada).
3. Captura de `cat test/resultado.txt` (salida) junto al esperado.
4. Sesión de GDB (ver abajo) — captura de al menos un breakpoint y la
   inspección de un registro clave (p. ej. `x19` = máximo acumulado).

## Depuración con GDB

Compilar con símbolos de depuración y arrancar gdb:

```bash
make debug
```

Dentro de gdb, ejemplo de sesión mínima que sirve como evidencia:

```
(gdb) break check_and_save_num
(gdb) run
(gdb) info registers x19 x20 x21 x22
(gdb) continue
(gdb) info registers x19 x20 x21 x22
(gdb) continue
...
(gdb) print $x22
(gdb) quit
```

Esto permite mostrar cómo `x19` (máximo), `x20` (mínimo), `x21` (suma) y
`x22` (contador) se van actualizando lectura por lectura — es la evidencia de
depuración que pide la rúbrica del proyecto.

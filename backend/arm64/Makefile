# Makefile - Módulo ARM64 (AArch64)
# No modifica logica.s ni el binario calculos_arm ya generado.
# Solo automatiza los comandos as/ld que ya se usan manualmente.

AS      = as
LD      = ld
SRC     = logica.s
OBJ     = logica.o
BIN     = calculos_arm

.PHONY: all clean test debug

all: $(BIN)

$(OBJ): $(SRC)
	$(AS) -g -o $(OBJ) $(SRC)

$(BIN): $(OBJ)
	$(LD) -o $(BIN) $(OBJ)

# Ejecuta el binario contra el datos.txt de prueba independiente,
# SIN tocar el datos.txt/resultado.txt reales usados por main.py.
test: $(BIN)
	cp $(BIN) test/$(BIN)
	cd test && ./$(BIN)
	@echo "----- resultado.txt de PRUEBA -----"
	cat test/resultado.txt

# Recompila con símbolos de depuración y abre gdb
debug: clean
	$(AS) -g -o $(OBJ) $(SRC)
	$(LD) -o $(BIN) $(OBJ)
	gdb ./$(BIN)

clean:
	rm -f $(OBJ) $(BIN) test/$(BIN) test/resultado.txt

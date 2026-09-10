import time
from rpi_lcd import LCD

class LCDView:
    def __init__(self, address=0x27):
        try:
            # Inicialización exacta como la pidió tu auxiliar
            self.lcd = LCD(address, 1, 16, 2, True)
            
            # Variables para guardar el estado de los sensores
            self.temp = 0.0
            self.hum = 0.0
            self.gas = 0.0
            self.distancia = 0.0
            self.luz = 0.0
            self.puerta = "Cerrada"
            self.estado_global = "Seguro"
            
            # Control de la rotación sin usar sleep()
            self.index_pantalla = 0
            self.ultimo_cambio = time.time()
            self.tiempo_espera = 2.0  # Cambia cada 2 segundos
            
            self.lcd.clear()
            self.lcd.text("Sistema Listo", 1)
            self.lcd.text("Iniciando...", 2)
            
        except Exception as e:
            print(f"⚠️ Error LCD: {e}")
            self.lcd = None

    def actualizar_datos(self, temp, hum, gas, dist, luz, puerta, estado):
        self.temp = temp
        self.hum = hum
        self.gas = gas
        self.distancia = dist
        self.luz = luz
        self.puerta = puerta
        self.estado_global = estado

    def rotar_pantalla(self):
        if self.lcd is None:
            return

        ahora = time.time()
        # Si ya pasaron 2 segundos desde el último cambio...
        if ahora - self.ultimo_cambio >= self.tiempo_espera:
            self.ultimo_cambio = ahora # Reiniciar el cronómetro
            
            pantallas = [
                (f"Temp:{self.temp}C", f"Hum:{self.hum}%"),
                ("Nivel Gas:", f"{self.gas} PPM"),
                ("Distancia:", f"{self.distancia} cm"),
                ("Nivel Luz:", f"{self.luz} %"),
                ("Puerta:", f"{self.puerta}"),
                ("Estado Global:", f"{self.estado_global}")
            ]
            
            # Obtener las 2 líneas de texto de la pantalla actual
            line1, line2 = pantallas[self.index_pantalla]
            
            # Mostrar en la LCD 
            self.lcd.clear()
            self.lcd.text(line1, 1)
            self.lcd.text(line2, 2)
            
            # Avanzar al siguiente índice circularmente
            self.index_pantalla = (self.index_pantalla + 1) % len(pantallas)

    def limpiar(self):
        if self.lcd:
            self.lcd.clear()

import time
import RPi.GPIO as GPIO
import subprocess
from datetime import datetime

from view.lcd_view import LCDView

from controllers.ctrl_acceso import ControladorAcceso
from controllers.ctrl_clima import ControladorClima
from controllers.ctrl_seguridad import ControladorSeguridad
from controllers.ctrl_luces import ControladorLuces

from models.modelo_estado import EstadoModel, EstadoSchema
from models.modelo_arm64 import Arm64Model, Arm64Schema

# Pines para los LEDs de estado global
PIN_LED_VERDE = 13
PIN_LED_AMARILLO = 19

def main():
    print("Iniciando Sistema...")
    pantalla = LCDView()

    # Inicialización de los controladores
    acceso = ControladorAcceso()
    clima = ControladorClima()
    seguridad = ControladorSeguridad()
    luces = ControladorLuces()
    
    db_estado = EstadoModel()
    db_arm64 = Arm64Model()
    ultima_subida_estado = 0.0
    ultimo_estado_global = ""
    
    GPIO.setup(PIN_LED_VERDE, GPIO.OUT)
    GPIO.setup(PIN_LED_AMARILLO, GPIO.OUT)
    
    # Variables para el archivo datos.txt de ARM64
    temperaturas_para_arm = []
    ultima_recoleccion_temp = 0.0
    
    print("\nTodos los módulos inicializados. Entrando en bucle principal...\n")
    
    try:
        while True:
            tiempo_actual = time.time()
        
            acceso.procesar()
            clima.procesar()
            luces.procesar()
            estado_seguridad = seguridad.procesar()
            
            # LEDs DE ESTADO GLOBAL
            if estado_seguridad == "EMERGENCIA":
                nivel_estado = "EMERGENCIA"
                razon = "Fuga de gas detectada"
                
                # Apagamos Verde y Amarillo (El Rojo ya fue encendido por ctrl_seguridad)
                GPIO.output(PIN_LED_VERDE, GPIO.LOW)
                GPIO.output(PIN_LED_AMARILLO, GPIO.LOW)
                
                # Forzamos apertura de puerta y encendido de luces
                if not acceso.puerta_abierta:
                    print(" [SISTEMA CENTRAL] ¡Emergencia! Abriendo puertas de evacuación...")
                    acceso.abrir_puerta()
                if not luces.luces_encendidas:
                    luces.encender_luces()
                    
            elif clima.ventilador_encendido:
                nivel_estado = "ADVERTENCIA"
                razon = "Temperatura alta"
                
                # Encendemos Amarillo, Apagamos Verde (El Rojo sigue apagado)
                GPIO.output(PIN_LED_VERDE, GPIO.LOW)
                GPIO.output(PIN_LED_AMARILLO, GPIO.HIGH)
                
            else:
                nivel_estado = "NORMAL"
                razon = "Todo en orden"
                
                # Encendemos Verde, Apagamos Amarillo (El Rojo sigue apagado)
                GPIO.output(PIN_LED_VERDE, GPIO.HIGH)
                GPIO.output(PIN_LED_AMARILLO, GPIO.LOW)

            # GENERACIÓN DEL ARCHIVO datos.txt PARA ARM64
            # Obtenemos la última temperatura válida del controlador de clima cada 2 segundos
            if clima.last_temperature is not None and (tiempo_actual - ultima_recoleccion_temp) >= 2.0:
                # Convertimos a entero para evitar problemas de decimales en AArch64
                temperaturas_para_arm.append(int(clima.last_temperature))
                ultima_recoleccion_temp = tiempo_actual
                
                # Cuando tengamos 20 lecturas, creamos el archivo
                if len(temperaturas_para_arm) >= 20:
                    try:
                        with open("datos.txt", "w") as archivo:
                            for temp in temperaturas_para_arm:
                                archivo.write(f"{temp}\n")
                            archivo.write("$\n")
                        print("Archivo datos.txt generado. Ejecutando módulo ARM64...")
                        
                        # Ejecutamos el binario compilado 
                        # check=True hace que Python lance un error si el binario falla
                        inicio_tiempo = time.time()
                        subprocess.run(["./arm64/calculos_arm"], check=True)
                        print("Módulo ARM64 ejecutado exitosamente.")
                        fin_tiempo = time.time()

                        # Calculamos los milisegundos que tardó el ensamblador
                        tiempo_ejecucion_ms = (fin_tiempo - inicio_tiempo) * 1000
                        print(f"Módulo ARM64 ejecutado en {tiempo_ejecucion_ms:.4f} ms.")
                        
                        # Leemos el archivo resultado.txt y extraemos los datos
                        resultados_parseados = {}
                        with open("resultado.txt", "r") as res:
                            lineas = res.readlines()
                            for linea in lineas:
                                if "=" in linea:
                                    # Separamos "MÁX=27" en clave y valor
                                    clave, valor = linea.strip().split("=")
                                    resultados_parseados[clave] = float(valor)
                        
                        if all(k in resultados_parseados for k in ("MÁX", "MIN", "AVG", "COUNT")):
                            datos_esquema = Arm64Schema(
                                maximo=resultados_parseados["MÁX"],
                                minimo=resultados_parseados["MIN"],
                                promedio=resultados_parseados["AVG"],
                                total_datos=int(resultados_parseados["COUNT"]),
                                tiempo_ms=tiempo_ejecucion_ms
                            )
                            
                            # Subida a Atlas
                            db_arm64.guardar(datos_esquema)
                        else:
                            print("Advertencia: El archivo resultado.txt no tenía el formato completo.")
                            
                    except FileNotFoundError:
                        print("Error: No se encontró el ejecutable './calculos_arm'.")
                    except subprocess.CalledProcessError as e:
                        print(f"El programa en ensamblador falló al ejecutarse: {e}")
                    except Exception as e:
                        print(f"Error en el flujo de archivos: {e}")
                    
                    # Limpiamos la lista 
                    temperaturas_para_arm.clear()

            # GUARDAR EL ESTADO GLOBAL (Híbrido: Por cambio o cada 60s)
            ha_pasado_mucho_tiempo = (tiempo_actual - ultima_subida_estado) >= 60.0
            hay_un_cambio_importante = (nivel_estado != ultimo_estado_global)

            if hay_un_cambio_importante or ha_pasado_mucho_tiempo:
                estado_actual = EstadoSchema(
                    estado_global=nivel_estado,
                    motivo=razon,
                    puerta_abierta=acceso.puerta_abierta,
                    ventilador_encendido=clima.ventilador_encendido,
                    luces_encendidas=luces.luces_encendidas,
                    alarma_activa=seguridad.alarma_activada
                )
                
                db_estado.guardar(estado_actual)
                
                ultima_subida_estado = tiempo_actual
                ultimo_estado_global = nivel_estado
                
                if hay_un_cambio_importante:
                    print(f"Cambio de estado detectado: {nivel_estado}. Guardado inmediato.")

            temp_actual = clima.last_temperature if clima.last_temperature is not None else 0.0
            hum_actual = clima.last_humidity if clima.last_humidity is not None else 0.0

            nivel_gas = seguridad.nivel_gas if hasattr(seguridad, 'nivel_gas') and seguridad.nivel_gas is not None else 0.0 
            distancia = acceso.distancia_actual if hasattr(acceso, 'distancia_actual') and acceso.distancia_actual is not None else 0.0
            nivel_luz = luces.nivel_luz if hasattr(luces, 'nivel_luz') and luces.nivel_luz is not None else 0.0
            
            estado_puerta = "Abierta" if acceso.puerta_abierta else "Cerrada"

            pantalla.actualizar_datos(
                temp=round(temp_actual, 1),
                hum=round(hum_actual, 1),
                gas=nivel_gas,
                dist=round(distancia, 1) if distancia else 0.0,
                luz=nivel_luz,
                puerta=estado_puerta,
                estado=nivel_estado
            )
            
            # 3. Forzamos la rotación (ella sola sabrá si ya pasaron 2 segundos)
            pantalla.rotar_pantalla()
                    
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nSeñal de apagado recibida. Deteniendo el sistema central...")
        
    finally:
        # APAGADO SEGURO
        print("Limpiando puertos GPIO y apagando actuadores...")
        acceso.cerrar_puerta(forzar=True)
        clima.apagar_ventilador(forzar=True)
        luces.apagar_luces()
        seguridad.desactivar_alarma(forzar=True)
        
        GPIO.output(PIN_LED_VERDE, GPIO.LOW)
        GPIO.output(PIN_LED_AMARILLO, GPIO.LOW)
        
        clima.sensor.exit() 
        time.sleep(0.5)
        GPIO.cleanup()
        print("Sistema apagado correctamente. ¡Buen trabajo!")

if __name__ == "__main__":
    main()


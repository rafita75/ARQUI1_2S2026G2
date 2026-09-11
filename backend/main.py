import time
import RPi.GPIO as GPIO
import subprocess
from datetime import datetime
import json
import paho.mqtt.client as mqtt

from view.lcd_view import LCDView

from controllers.ctrl_acceso import ControladorAcceso
from controllers.ctrl_clima import ControladorClima
from controllers.ctrl_seguridad import ControladorSeguridad
from controllers.ctrl_luces import ControladorLuces

from models.modelo_estado import EstadoModel, EstadoSchema
from models.modelo_arm64 import Arm64Model, Arm64Schema
from models.modelo_comandos import ComandosModel, ComandoSchema

# Pines para los LEDs de estado global
PIN_LED_VERDE = 13
PIN_LED_AMARILLO = 19

PIN_BTN_PUERTA = 17
PIN_BTN_LUCES = 27
PIN_BTN_SILENCIAR = 22
PIN_BTN_RESET = 25

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
    db_comandos = ComandosModel()
    ultima_subida_estado = 0.0
    ultimo_estado_global = ""

    def registrar_comando(actuador, accion, origen):
        db_comandos.guardar(ComandoSchema(actuador=actuador, accion=accion, origen=origen))

    # Banderas para los botones
    modo_luces_auto = True
    buzzer_silenciado = False

    GPIO.setup(PIN_LED_VERDE, GPIO.OUT)
    GPIO.setup(PIN_LED_AMARILLO, GPIO.OUT)

    # CONFIGURACIÓN DE PINES PARA BOTONES
    GPIO.setup(PIN_BTN_PUERTA, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(PIN_BTN_LUCES, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(PIN_BTN_SILENCIAR, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(PIN_BTN_RESET, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    # ==========================================
    # FUNCIONES DE ACCIÓN PARA BOTONES
    # ==========================================
    # 1. Botón Puerta
    def accion_btn_puerta():
        print("\n🔘 [BOTÓN] Alternando puerta...")
        if acceso.puerta_abierta:
            acceso.cerrar_puerta(forzar=True)
            registrar_comando("Puerta", "CERRAR", "Botón Físico")
        else:
            acceso.abrir_puerta()
            registrar_comando("Puerta", "ABRIR", "Botón Físico")

    # 2. Botón Luces (Auto / Manual)
    def accion_btn_luces():
        nonlocal modo_luces_auto
        if modo_luces_auto:
            modo_luces_auto = False
            print("\n🔘 [BOTÓN] Modo Luces: MANUAL (Alternando estado...)")
            if luces.luces_encendidas:
                luces.apagar_luces()
                registrar_comando("Luces", "APAGAR (manual)", "Botón Físico")
            else:
                luces.encender_luces()
                registrar_comando("Luces", "ENCENDER (manual)", "Botón Físico")
        else:
            modo_luces_auto = True
            print("\n🔘 [BOTÓN] Modo Luces: AUTOMÁTICO (Control por LDR)")
            registrar_comando("Luces", "AUTO", "Botón Físico")

    # 3. Botón Silenciar Buzzer (tambien reutilizado por el comando MQTT de seguridad)
    def accion_btn_silenciar(origen="Botón Físico"):
        nonlocal buzzer_silenciado
        if seguridad.alarma_activada:
            buzzer_silenciado = True
            GPIO.output(seguridad.pin_buzzer, GPIO.LOW)
            print("\n🔘 [BOTÓN] 🔇 Buzzer silenciado. (Peligro aún activo)")
            registrar_comando("Alarma", "SILENCIAR", origen)

    # 4. Botón Restablecer Alerta (tambien reutilizado por el comando MQTT de seguridad)
    def accion_btn_reset(origen="Botón Físico"):
        nonlocal buzzer_silenciado
        print("\n🔘 [BOTÓN] Intentando restablecer alertas...")

        # Validar si el peligro de gas ya pasó
        if seguridad.nivel_gas is not None and seguridad.nivel_gas < 180:
            seguridad.desactivar_alarma(forzar=True)
            buzzer_silenciado = False
            print("✅ Alarma de gas restablecida. Sistema seguro.")
            registrar_comando("Alarma", "RESET", origen)
        elif seguridad.alarma_activada:
            print("⚠️ DENEGADO: Aún hay altos niveles de gas detectados.")

        # Validar si el peligro de temperatura ya pasó
        if clima.last_temperature is not None and clima.last_temperature < 28.0:
            clima.apagar_ventilador(forzar=True)
            print("✅ Advertencia térmica restablecida.")
            registrar_comando("Ventilador", "RESET", origen)

    temperaturas_para_arm = []
    ultima_recoleccion_temp = 0.0

    # ==========================================
    # CONFIGURACIÓN MQTT (EMQX)
    # ==========================================
    broker = "broker.emqx.io"
    puerto = 1883
    cliente_mqtt = mqtt.Client()

    # Función para recibir comandos desde la web
    def al_recibir_mensaje(client, userdata, msg):
        comando = msg.payload.decode()
        print(f"\n🌐 [MQTT] Comando web recibido en {msg.topic}: {comando}")
        
        if msg.topic == "grupo2/edificio/comandos/puerta":
            if comando == "ABRIR": acceso.abrir_puerta()
            elif comando == "CERRAR": acceso.cerrar_puerta(forzar=True)
            else: return
            registrar_comando("Puerta", comando, "Dashboard Web")

        elif msg.topic == "grupo2/edificio/comandos/luces":
            nonlocal modo_luces_auto
            if comando == "ENCENDER":
                modo_luces_auto = False
                luces.encender_luces()
            elif comando == "APAGAR":
                modo_luces_auto = False
                luces.apagar_luces()
            elif comando == "AUTO":
                modo_luces_auto = True
            else:
                return
            registrar_comando("Luces", comando, "Dashboard Web")

        elif msg.topic == "grupo2/edificio/comandos/ventilador":
            if comando == "ENCENDER":
                clima.modo_manual = True
                clima.encender_ventilador()
            elif comando == "APAGAR":
                clima.modo_manual = True
                clima.apagar_ventilador(forzar=True)
            elif comando == "AUTO":
                clima.modo_manual = False
            else:
                return
            registrar_comando("Ventilador", comando, "Dashboard Web")

        elif msg.topic == "grupo2/edificio/comandos/seguridad":
            if comando == "SILENCIAR":
                accion_btn_silenciar(origen="Dashboard Web")
            elif comando == "RESET":
                accion_btn_reset(origen="Dashboard Web")

    cliente_mqtt.on_message = al_recibir_mensaje
    cliente_mqtt.connect(broker, puerto, 60)

    # Nos suscribimos a los tópicos de control para escuchar al Dashboard
    cliente_mqtt.subscribe("grupo2/edificio/comandos/puerta")
    cliente_mqtt.subscribe("grupo2/edificio/comandos/luces")
    cliente_mqtt.subscribe("grupo2/edificio/comandos/ventilador")
    cliente_mqtt.subscribe("grupo2/edificio/comandos/seguridad")
    
    # Arrancamos el hilo de MQTT en segundo plano
    cliente_mqtt.loop_start()

    print("\nTodos los módulos inicializados. Entrando en bucle principal...\n")

    # ==========================================
    # BANDERAS PARA POLLING DE BOTONES
    # ==========================================
    btn_ant_puerta = GPIO.LOW
    btn_ant_luces = GPIO.LOW
    btn_ant_silenciar = GPIO.LOW
    btn_ant_reset = GPIO.LOW

    try:
        while True:
            tiempo_actual = time.time()

            # ==========================================
            # LECTURA DE BOTONES MANUAL (POLLING)
            # ==========================================
            actual_puerta = GPIO.input(PIN_BTN_PUERTA)
            if actual_puerta == GPIO.HIGH and btn_ant_puerta == GPIO.LOW:
                accion_btn_puerta()
            btn_ant_puerta = actual_puerta

            actual_luces = GPIO.input(PIN_BTN_LUCES)
            if actual_luces == GPIO.HIGH and btn_ant_luces == GPIO.LOW:
                accion_btn_luces()
            btn_ant_luces = actual_luces

            actual_silenciar = GPIO.input(PIN_BTN_SILENCIAR)
            if actual_silenciar == GPIO.HIGH and btn_ant_silenciar == GPIO.LOW:
                accion_btn_silenciar()
            btn_ant_silenciar = actual_silenciar

            actual_reset = GPIO.input(PIN_BTN_RESET)
            if actual_reset == GPIO.HIGH and btn_ant_reset == GPIO.LOW:
                accion_btn_reset()
            btn_ant_reset = actual_reset
            # ==========================================

            acceso.procesar()
            clima.procesar()
            
            # Solo procesa automáticamente las luces si está en AUTO
            if modo_luces_auto:
                luces.procesar()
                
            estado_seguridad = seguridad.procesar()

            # Mantiene el buzzer apagado si fue silenciado manualmente
            if buzzer_silenciado:
                GPIO.output(seguridad.pin_buzzer, GPIO.LOW)

            # LEDs DE ESTADO GLOBAL
            if estado_seguridad == "EMERGENCIA":
                nivel_estado = "EMERGENCIA"
                razon = "Fuga de gas detectada"

                GPIO.output(PIN_LED_VERDE, GPIO.LOW)
                GPIO.output(PIN_LED_AMARILLO, GPIO.LOW)
                GPIO.output(seguridad.pin_led_rojo, GPIO.HIGH)  # LED rojo = estado global EMERGENCIA

                if not acceso.puerta_abierta:
                    print(" [SISTEMA CENTRAL] ¡Emergencia! Abriendo puertas de evacuación...")
                    acceso.abrir_puerta()
                
                # En emergencia, forzamos las luces a encender ignorando el modo
                if not luces.luces_encendidas:
                    luces.encender_luces()

            elif clima.ventilador_encendido or clima.humedad_fuera_rango:
                nivel_estado = "ADVERTENCIA"
                razon = "Temperatura alta" if clima.ventilador_encendido else "Humedad fuera de rango"

                GPIO.output(PIN_LED_VERDE, GPIO.LOW)
                GPIO.output(PIN_LED_AMARILLO, GPIO.HIGH)

            else:
                nivel_estado = "NORMAL"
                razon = "Todo en orden"

                GPIO.output(PIN_LED_VERDE, GPIO.HIGH)
                GPIO.output(PIN_LED_AMARILLO, GPIO.LOW)

            # GENERACIÓN DEL ARCHIVO ARM64
            if clima.last_temperature is not None and (tiempo_actual - ultima_recoleccion_temp) >= 2.0:
                temperaturas_para_arm.append(int(clima.last_temperature))
                ultima_recoleccion_temp = tiempo_actual

                if len(temperaturas_para_arm) >= 20:
                    try:
                        with open("datos.txt", "w") as archivo:
                            for temp in temperaturas_para_arm:
                                archivo.write(f"{temp}\n")
                            archivo.write("$\n")
                        print("Archivo datos.txt generado. Ejecutando módulo ARM64...")

                        inicio_tiempo = time.time()
                        subprocess.run(["./arm64/calculos_arm"], check=True)
                        print("Módulo ARM64 ejecutado exitosamente.")
                        fin_tiempo = time.time()

                        tiempo_ejecucion_ms = (fin_tiempo - inicio_tiempo) * 1000

                        resultados_parseados = {}
                        with open("resultado.txt", "r") as res:
                            lineas = res.readlines()
                            for linea in lineas:
                                if "=" in linea:
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
                            db_arm64.guardar(datos_esquema)

                            # Topic MQTT obligatorio para el resultado del modulo ARM64
                            cliente_mqtt.publish(
                                "grupo2/edificio/arm64/resultados",
                                json.dumps({
                                    "maximo": resultados_parseados["MÁX"],
                                    "minimo": resultados_parseados["MIN"],
                                    "promedio": resultados_parseados["AVG"],
                                    "total_datos": int(resultados_parseados["COUNT"]),
                                    "tiempo_ms": tiempo_ejecucion_ms
                                })
                            )
                    except Exception as e:
                        print(f"Error en flujo ARM64: {e}")

                    temperaturas_para_arm.clear()

            # GUARDAR EL ESTADO GLOBAL
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

            # ACTUALIZACIÓN DE LA PANTALLA LCD
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
            pantalla.rotar_pantalla()

            # PUBLICACIÓN MQTT (Hacia el Dashboard)
            if not hasattr(main, "ultima_publicacion_mqtt"):
                main.ultima_publicacion_mqtt = 0

            if (tiempo_actual - main.ultima_publicacion_mqtt) >= 2.0:
                payload_sensores = {
                    "temperatura": temp_actual,
                    "humedad": hum_actual,
                    "gas": nivel_gas,
                    "distancia": round(distancia, 1) if distancia else 0.0,
                    "luz": nivel_luz,
                    "estado": nivel_estado,
                    "actuadores": {
                        "puerta": "Abierta" if acceso.puerta_abierta else "Cerrada",
                        "luces": "Encendidas" if luces.luces_encendidas else "Apagadas",
                        "ventilador": "Encendido" if clima.ventilador_encendido else "Apagado",
                        "alarma": "Silenciada" if buzzer_silenciado else ("Activada" if seguridad.alarma_activada else "Inactiva")
                    }
                }
                # Convertimos el diccionario a JSON y lo enviamos
                cliente_mqtt.publish("grupo2/edificio/sensores", json.dumps(payload_sensores))

                # Topics granulares por sensor/actuador/estado (ademas del payload
                # combinado de arriba), para cumplir la lista minima de topics del
                # enunciado sin romper al dashboard actual que consume el combinado.
                cliente_mqtt.publish("grupo2/edificio/sensores/temperatura", str(temp_actual))
                cliente_mqtt.publish("grupo2/edificio/sensores/humedad", str(hum_actual))
                cliente_mqtt.publish("grupo2/edificio/sensores/gas", str(nivel_gas))
                cliente_mqtt.publish("grupo2/edificio/sensores/distancia", str(payload_sensores["distancia"]))
                cliente_mqtt.publish("grupo2/edificio/sensores/luz", str(nivel_luz))
                cliente_mqtt.publish("grupo2/edificio/actuadores/puerta", payload_sensores["actuadores"]["puerta"])
                cliente_mqtt.publish("grupo2/edificio/actuadores/luces", payload_sensores["actuadores"]["luces"])
                cliente_mqtt.publish("grupo2/edificio/actuadores/ventilador", payload_sensores["actuadores"]["ventilador"])
                cliente_mqtt.publish("grupo2/edificio/actuadores/alarma", payload_sensores["actuadores"]["alarma"])
                cliente_mqtt.publish("grupo2/edificio/estado/global", nivel_estado)

                main.ultima_publicacion_mqtt = tiempo_actual

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
        
        # Detenemos y cerramos el cliente MQTT limpiamente
        cliente_mqtt.loop_stop()
        cliente_mqtt.disconnect()
        
        time.sleep(0.5)
        GPIO.cleanup()
        print("Sistema apagado correctamente. ¡Buen trabajo!")

if __name__ == "__main__":
    main()

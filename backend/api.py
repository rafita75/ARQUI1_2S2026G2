from flask import Flask, jsonify, request
from flask_cors import CORS
from models.modelo_lecturas import LecturasModel
from models.modelo_arm64 import Arm64Model
from models.modelo_eventos import EventosModel

app = Flask(__name__)
CORS(app)

# Instanciamos nuestras conexiones a MongoDB
db_lecturas = LecturasModel()
db_arm64 = Arm64Model()
db_eventos = EventosModel()

# ==========================================
# 1. ENDPOINT PARA LAS 5 GRÁFICAS DE SENSORES
# ==========================================
@app.route('/api/historial/<sensor>', methods=['GET'])
def obtener_historial_sensor(sensor):
    # sensor puede ser: temperatura, humedad, gas, distancia, luz
    try:
        # Buscamos los últimos 15 registros del sensor especificado
        cursor = db_lecturas.coleccion.find({"tipo": sensor}).sort("_id", -1).limit(15)
        datos = []
        for doc in cursor:
            datos.append({
                "valor": doc.get("valor", 0),
                "hora": doc["_id"].generation_time.strftime("%H:%M:%S")
            })
        datos.reverse() # Invertimos para que la gráfica vaya de izquierda (viejo) a derecha (nuevo)
        return jsonify(datos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 2. ENDPOINTS PARA LA GRÁFICA Y DATOS DE ARM64
# ==========================================
@app.route('/api/historial/arm64/promedios', methods=['GET'])
def obtener_historial_arm_promedios():
    try:
        cursor = db_arm64.coleccion.find().sort("_id", -1).limit(15)
        datos = []
        for doc in cursor:
            datos.append({
                "valor": doc.get("promedio", 0),
                "hora": doc["_id"].generation_time.strftime("%H:%M:%S")
            })
        datos.reverse()
        return jsonify(datos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/historial/arm64/stats', methods=['GET'])
def obtener_arm_stats():
    try:
        cursor = db_arm64.coleccion.find().sort("_id", -1).limit(10)
        datos = []
        for doc in cursor:
            datos.append({
                "promedio": doc.get("promedio", 0),
                "maximo": doc.get("maximo", 0),
                "minimo": doc.get("minimo", 0),
                "tiempo_ms": doc.get("tiempo_ms", 0),
                "hora": doc["_id"].generation_time.strftime("%H:%M:%S")
            })
        return jsonify(datos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 3. ENDPOINTS PARA LOS HISTORIALES DE EVENTOS Y COMANDOS
# ==========================================
@app.route('/api/historial/eventos', methods=['GET'])
def obtener_eventos():
    try:
        # Traemos los últimos 10 eventos (ignorando los comandos web)
        cursor = db_eventos.coleccion.find({"tipo_evento": {"$ne": "Comando Web"}}).sort("_id", -1).limit(10)
        datos = []
        for doc in cursor:
            datos.append({
                "descripcion": f"[{doc.get('severidad', 'INFO')}] {doc.get('descripcion', '')}",
                "hora": doc["_id"].generation_time.strftime("%H:%M:%S")
            })
        return jsonify(datos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/historial/comandos', methods=['GET'])
def obtener_comandos():
    try:
        # Traemos solo los eventos que son "Comando Web"
        cursor = db_eventos.coleccion.find({"tipo_evento": "Comando Web"}).sort("_id", -1).limit(10)
        datos = []
        for doc in cursor:
            datos.append({
                "dispositivo": doc.get("descripcion", "").split("|")[0],
                "accion": doc.get("descripcion", "").split("|")[1] if "|" in doc.get("descripcion", "") else "Desconocida",
                "hora": doc["_id"].generation_time.strftime("%H:%M:%S")
            })
        return jsonify(datos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/comandos', methods=['POST'])
def guardar_comando():
    # Esta ruta es usada por el Dashboard cada vez que presionas un botón web
    try:
        data = request.json
        # Insertamos el comando remoto en la base de datos de MongoDB
        db_eventos.coleccion.insert_one({
            "tipo_evento": "Comando Web",
            "descripcion": f"{data.get('dispositivo')}|{data.get('accion')}",
            "severidad": "REMOTO"
        })
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 API Full-Stack corriendo en http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)

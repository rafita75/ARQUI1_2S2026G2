// ==========================================
// CONFIGURACIÓN GLOBAL
// ==========================================
const API_URL = "http://10.58.38.42:5000/api"; // Cambiar "localhost" por la IP de la Raspberry Pi
const MQTT_BROKER = "wss://broker.emqx.io:8084/mqtt";
const TOPIC_SENSORES = "grupo2/edificio/sensores";
const TOPIC_COMANDOS = "grupo2/edificio/comandos/";

let chartInstances = {};

// ==========================================
// 1. MQTT: TIEMPO REAL Y COMANDOS
// ==========================================
const clienteMQTT = mqtt.connect(MQTT_BROKER);

clienteMQTT.on('connect', () => {
    console.log('✅ Conectado a EMQX');
    clienteMQTT.subscribe(TOPIC_SENSORES);
});

clienteMQTT.on('message', (topic, message) => {
    if (topic === TOPIC_SENSORES) {
        const datos = JSON.parse(message.toString());
        
        // Actualizar Sensores
        document.getElementById('live-temp').innerText = `${datos.temperatura} °C`;
        document.getElementById('live-hum').innerText = `${datos.humedad} %`;
        document.getElementById('live-gas').innerText = `${datos.gas} /255`;
        document.getElementById('live-dist').innerText = `${datos.distancia} cm`;
        document.getElementById('live-luz').innerText = `${datos.luz} /255`;
        
        // Actualizar Actuadores (Asumiendo que envías esto en el JSON MQTT)
        document.getElementById('estado-puerta').innerText = datos.actuadores.puerta;
        document.getElementById('estado-luces').innerText = datos.actuadores.luces;
        document.getElementById('estado-ventilador').innerText = datos.actuadores.ventilador;
        document.getElementById('estado-alarma').innerText = datos.actuadores.alarma;

        // Actualizar Estado Global
        const domEstado = document.getElementById('estado-global');
        domEstado.innerText = datos.estado;
        domEstado.style.color = datos.estado === "NORMAL" ? "#10b981" : (datos.estado === "ADVERTENCIA" ? "#fbbf24" : "#ef4444");
    }
});

function enviarComando(dispositivo, accion) {
    const topico = TOPIC_COMANDOS + dispositivo;
    clienteMQTT.publish(topico, accion);
    
    // Guardar el comando en la base de datos a través de la API para el historial
    fetch(`${API_URL}/comandos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dispositivo: dispositivo, accion: accion })
    }).catch(e => console.error("Error guardando comando:", e));
}

// ==========================================
// 2. API: GRÁFICAS (Chart.js)
// ==========================================
function crearGrafica(idCanvas, label, datos, color) {
    const ctx = document.getElementById(idCanvas).getContext('2d');
    
    if (chartInstances[idCanvas]) chartInstances[idCanvas].destroy();

    const etiquetas = datos.map(d => d.hora);
    const valores = datos.map(d => d.valor);

    chartInstances[idCanvas] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: etiquetas,
            datasets: [{
                label: label,
                data: valores,
                borderColor: color,
                backgroundColor: color + '33', // Transparencia
                borderWidth: 2, fill: true, tension: 0.3
            }]
        },
        options: { scales: { y: { beginAtZero: false } }, plugins: { legend: { labels: { color: '#e2e8f0' } } } }
    });
}

async function cargarTodasLasGraficas() {
    try {
        // Pedimos los datos a la API (Deberás crear estos endpoints en Flask)
        const endpoints = [
            { url: 'temperatura', canvas: 'graficaTemp', label: 'Temp (°C)', color: '#f97316' },
            { url: 'humedad', canvas: 'graficaHum', label: 'Humedad (%)', color: '#38bdf8' },
            { url: 'gas', canvas: 'graficaGas', label: 'Gas (Nivel)', color: '#fbbf24' },
            { url: 'distancia', canvas: 'graficaDist', label: 'Distancia (cm)', color: '#a855f7' },
            { url: 'luz', canvas: 'graficaLuz', label: 'Luz (ADC)', color: '#eab308' },
            { url: 'arm64/promedios', canvas: 'graficaArm', label: 'ARM64 Promedios (°C)', color: '#10b981' }
        ];

        for (let ep of endpoints) {
            let res = await fetch(`${API_URL}/historial/${ep.url}`);
            let datos = await res.json();
            crearGrafica(ep.canvas, ep.label, datos, ep.color);
        }
    } catch (e) { console.error("Error cargando gráficas:", e); }
}

// ==========================================
// 3. API: HISTORIAL Y LISTAS
// ==========================================
async function cargarHistoriales() {
    try {
        // 1. Eventos
        let resEv = await fetch(`${API_URL}/historial/eventos`);
        let eventos = await resEv.json();
        document.getElementById('lista-eventos').innerHTML = eventos.map(e => `<li>[${e.hora}] ${e.descripcion}</li>`).join('');

        // 2. Comandos
        let resCmd = await fetch(`${API_URL}/historial/comandos`);
        let comandos = await resCmd.json();
        document.getElementById('lista-comandos').innerHTML = comandos.map(c => `<li>[${c.hora}] ${c.dispositivo}: ${c.accion}</li>`).join('');

        // 3. ARM64 Resultados textuales
        let resArm = await fetch(`${API_URL}/historial/arm64/stats`);
        let arm64 = await resArm.json();
        
        // Llenar tarjeta principal
        if(arm64.length > 0) {
            document.getElementById('arm-avg').innerText = arm64[0].promedio;
            document.getElementById('arm-max').innerText = arm64[0].maximo;
            document.getElementById('arm-min').innerText = arm64[0].minimo;
            document.getElementById('arm-time').innerText = arm64[0].tiempo_ms.toFixed(2);
        }
        
        // Llenar lista del historial
        document.getElementById('lista-arm64').innerHTML = arm64.map(a => `<li>[${a.hora}] Prom: ${a.promedio}°C | ${a.tiempo_ms}ms</li>`).join('');

    } catch (e) { console.error("Error cargando historiales:", e); }
}

// Inicializar al cargar la página
window.onload = () => {
    cargarTodasLasGraficas();
    cargarHistoriales();
};

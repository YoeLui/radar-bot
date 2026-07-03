import pandas as pd
import requests
import time
import os
import re
from huggingface_hub import HfApi

print("🤖 Iniciando el Scraper Híbrido Autónomo...")

# 1. EMULACIÓN DE NAVEGADOR MÓVIL REAL
# Configuramos los encabezados para que la web del banco crea que somos un celular real en Lima
URL_TARGET = "https://interbank.pe/promociones-catalogo/todo/tarjeta-de-credito"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-PE,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/"
}

# 2. LISTA MAESTRA DE RESPALDO Y GEOLOCALIZACIÓN
COORDEANADAS_LIMA = {
    "Barrio": (-12.0942, -77.0224), "Popular": (-12.1224, -77.0298), 
    "Embarcadero 41": (-12.1542, -76.9424), "La Cuadra de Salvador": (-12.1012, -77.0291),
    "El Hornero": (-12.1444, -76.9402), "KO Asian Kitchen": (-12.0865, -76.9751),
    "Bembos": (-12.1582, -76.9395), "Cineplanet": (-12.1662, -76.9470),
    "Tottus": (-12.1654, -76.9335), "Movil Bus": (-12.0532, -77.0321),
    "Despegar": (-12.1214, -77.0295), "Tiendas EFE": (-12.0562, -77.0368)
}

PROMOS_VERIFICADAS = [
    {"Cadena": "Barrio", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en toda la carta."},
    {"Cadena": "Popular", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en toda la carta."},
    {"Cadena": "Embarcadero 41", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en platos a la carta."},
    {"Cadena": "La Cuadra de Salvador", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en toda la carta."},
    {"Cadena": "El Hornero", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en toda la carta."},
    {"Cadena": "KO Asian Kitchen", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en toda la carta."},
    {"Cadena": "Bembos", "Tarjeta": "Interbank", "Tipo": "Tarjeta de crédito", "Rango": "Visa Platinium", "Descuento": "🍔 35% de descuento en Combos Medianos Extremos."},
    {"Cadena": "Bembos", "Tarjeta": "Interbank", "Tipo": "Plin", "Rango": "Todas", "Descuento": "📱 S/ 5 de descuento adicional escaneando QR Plin."},
    {"Cadena": "Cineplanet", "Tarjeta": "Interbank", "Tipo": "Tarjeta de crédito", "Rango": "Visa Platinium", "Descuento": "🎬 2x1 en entradas todos los días."},
    {"Cadena": "Cineplanet", "Tarjeta": "Interbank", "Tipo": "Plin", "Rango": "Todas", "Descuento": "📱 Combo Popcorn mediano a precio exclusivo con Plin."},
    {"Cadena": "Tottus", "Tarjeta": "CMR", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🛒 10% de descuento en Alimentos y Bebidas (Todos los días)."},
    {"Cadena": "Tottus", "Tarjeta": "CMR", "Tipo": "Tarjeta de crédito", "Rango": "Todas", "Descuento": "🛒 30% de descuento los fines de semana."},
    {"Cadena": "Movil Bus", "Tarjeta": "Interbank", "Tipo": "Tarjeta de crédito", "Rango": "Todas", "Descuento": "🚌 10% de desc. en pasajes en counter y 15% en envíos."},
    {"Cadena": "Despegar", "Tarjeta": "Interbank", "Tipo": "Tarjeta de crédito", "Rango": "Todas", "Descuento": "✈️ Hasta 12 cuotas sin intereses en reservas globales."},
    {"Cadena": "Tiendas EFE", "Tarjeta": "Efectibank", "Tipo": "Tarjeta de crédito", "Rango": "Todas", "Descuento": "🔌 Hasta 30% de descuento en combos de electrodomésticos."}
]

# 3. INTENTO DE CONEXIÓN EN VIVO A INTERBANK
promos_finales = []
usando_respaldo = True

try:
    print(f"🌐 Conectando de forma encubierta a: {URL_TARGET}")
    response = requests.get(URL_TARGET, headers=HEADERS, timeout=15)
    
    if response.status_code == 200:
        html_content = response.text
        print("✅ Conexión exitosa. Analizando estructura de la página...")
        
        # El motor busca de forma masiva si las marcas de Lima aparecen activas en el HTML vivo del banco
        for marca in COORDEANADAS_LIMA.keys():
            if re.search(marca, html_content, re.IGNORECASE):
                print(f"🎯 ¡Detectada marca activa en la web del banco!: {marca}")
                # Si la encuentra en vivo, filtramos sus promos reales para el mapa
                for p in PROMOS_VERIFICADAS:
                    if p["Cadena"] == marca:
                        promos_finales.append(p)
        
        if len(promos_finales) > 0:
            usando_respaldo = False
            print(f"✨ Éxito: Se construyó el mapa dinámico con {len(promos_finales)} marcas detectadas en vivo.")
    else:
        print(f"⚠️ El servidor del banco respondió con código {response.status_code}. Activando escudo protector...")
except Exception as e:
    print(f"⚠️ Error de red o bloqueo de seguridad: {e}. Activando escudo protector...")

# 4. SISTEMA DE FUSIÓN (Si el banco bloqueó al robot, usa la base de datos segura completa)
if usando_respaldo:
    print("🛡️ Escudo protector activado: Usando la base de datos maestra completa para asegurar continuidad.")
    promos_finales = PROMOS_VERIFICADAS

# 5. GENERACIÓN DEL ARCHIVO CON GEOLOCALIZACIÓN
registros = []
for item in promos_finales:
    lat, lon = COORDEANADAS_LIMA.get(item["Cadena"], (-12.16542, -76.93351))
    row = item.copy()
    row["lat"] = lat
    row["lon"] = lon
    registros.append(row)

df = pd.DataFrame(registros)
df.to_csv("promos.csv", index=False)
print("✅ Archivo promos.csv estructurado correctamente.")

# 6. INYECCIÓN AUTOMÁTICA EN HUGGING FACE
token = os.getenv("HF_TOKEN")
if not token:
    print("❌ ERROR: No se encontró el HF_TOKEN en la caja fuerte de GitHub.")
    exit(1)

try:
    api = HfApi()
    api.upload_file(
        path_or_fileobj="promos.csv",
        path_in_repo="promos.csv",
        repo_id="YoeLui/radar-vmt",  
        repo_type="space",
        token=token
    )
    print("🚀 ¡SINCRO COMPLETADA CON ÉXITO EN TU MAPA!")
except Exception as error_detalle:
    print(f"❌ Falló la subida final a Hugging Face: {error_detalle}")
    exit(1)
    

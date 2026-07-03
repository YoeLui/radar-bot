import pandas as pd
import requests
import time
import os
from huggingface_hub import HfApi

# Base maestra oficial actualizada con tus capturas del 50%, Plin y Viajes
DIARIO_CATALOGO = [
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

def obtener_coordenadas(marca):
    # Diccionario de coordenadas fijas de alta precisión para Lima para evitar bloqueos
    coordenadas = {
        "Barrio": (-12.0942, -77.0224), "Popular": (-12.1224, -77.0298), 
        "Embarcadero 41": (-12.1542, -76.9424), "La Cuadra de Salvador": (-12.1012, -77.0291),
        "El Hornero": (-12.1444, -76.9402), "KO Asian Kitchen": (-12.0865, -76.9751),
        "Bembos": (-12.1582, -76.9395), "Cineplanet": (-12.1662, -76.9470),
        "Tottus": (-12.1654, -76.9335), "Movil Bus": (-12.0532, -77.0321),
        "Despegar": (-12.1214, -77.0295), "Tiendas EFE": (-12.0562, -77.0368)
    }
    return coordenadas.get(marca, (-12.16542, -76.93351))

# Generar filas procesadas con geolocalización activa
registros = []
for item in DIARIO_CATALOGO:
    lat, lon = obtener_coordenadas(item["Cadena"])
    row = item.copy()
    row["lat"] = lat
    row["lon"] = lon
    registros.append(row)

df = pd.DataFrame(registros)
df.to_csv("promos.csv", index=False)
print("✅ Archivo promos.csv generado exitosamente.")

# Subida automatizada a Hugging Face usando tu Token de seguridad
token = os.getenv("HF_TOKEN")
if token:
    api = HfApi()
    api.upload_file(
        path_or_fileobj="promos.csv",
        path_in_repo="promos.csv",
        repo_id="YoelLui/radar-vmt",
        repo_type="space",
        token=token
    )
    print("🚀 Archivo sincronizado en producción de Hugging Face.")
    

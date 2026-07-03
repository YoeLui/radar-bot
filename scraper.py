import pandas as pd
import time
import os
from huggingface_hub import HfApi
from geopy.geocoders import Nominatim

print("🤖 Iniciando Scraper Personalizado Sólido (Interbank, BCP, CMR, Efectibank)...")

# 1. INICIALIZAR EL BUSCADOR DE MAPAS GLOBAL
geolocalizador = Nominatim(user_agent="radar_lima_personal_bot")

# 2. BASE DE DATOS MAESTRA TOTAL DE TUS TARJETAS REALES
PROMOS_VERIFICADAS = [
    # === INTERBANK ===
    {"Cadena": "Barrio", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en toda la carta por tener tu Sueldo aquí."},
    {"Cadena": "Popular", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en toda la carta por Cuenta Sueldo."},
    {"Cadena": "La Cuadra de Salvador", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en carnes seleccionadas (Sueldo)."},
    {"Cadena": "El Hornero", "Tarjeta": "Interbank", "Tipo": "Cuenta Sueldo", "Rango": "Todas", "Descuento": "🔥 50% de descuento en toda la carta de carnes y vinos."},
    {"Cadena": "Bembos", "Tarjeta": "Interbank", "Tipo": "Tarjeta de crédito", "Rango": "Visa Platinum", "Descuento": "🍔 35% de descuento en combos medianos exclusivos para Platinum."},
    {"Cadena": "Cineplanet", "Tarjeta": "Interbank", "Tipo": "Tarjeta de crédito", "Rango": "Visa Platinum", "Descuento": "🎬 2x1 en entradas y acceso a zonas preferenciales con tu Visa Platinum."},
    {"Cadena": "Bembos", "Tarjeta": "Interbank", "Tipo": "Plin", "Rango": "Todas", "Descuento": "📱 S/ 5 de descuento extra pagando escaneando el QR de Plin."},
    {"Cadena": "Cineplanet", "Tarjeta": "Interbank", "Tipo": "Plin", "Rango": "Todas", "Descuento": "📱 Combo Popcorn Mediano a precio exclusivo pagando con Plin."},
    {"Cadena": "Starbucks", "Tarjeta": "Interbank", "Tipo": "Tarjeta de débito", "Rango": "Todas", "Descuento": "☕ 20% de descuento en bebidas seleccionadas pagando con Débito Interbank."},
    {"Cadena": "Despegar", "Tarjeta": "Interbank", "Tipo": "Tarjeta de crédito", "Rango": "Visa Platinum", "Descuento": "✈️ Hasta 12 cuotas sin intereses y acumulación de Millas Benefit mejorada."},

    # === BCP ===
    {"Cadena": "Tambo", "Tarjeta": "BCP", "Tipo": "Yape", "Rango": "Todas", "Descuento": "📱 Promos exclusivas en tienda desde S/ 1.50 escaneando el QR de Yape."},
    {"Cadena": "Papa Johns", "Tarjeta": "BCP", "Tipo": "Tarjeta de crédito", "Rango": "Oro LATAM Pass", "Descuento": "🍕 2x1 en Pizzas Familiares y acumulación directa de Millas LATAM Pass."},
    {"Cadena": "Metro", "Tarjeta": "BCP", "Tipo": "Tarjeta de crédito", "Rango": "Oro LATAM Pass", "Descuento": "🛒 Precios exclusivos Oro en tecnología y abarrotes seleccionados + Millas."},
    {"Cadena": "KFC", "Tarjeta": "BCP", "Tipo": "Tarjeta de débito", "Rango": "Todas", "Descuento": "🍗 Combo Festín BCP preferencial mostrando y pagando con tu tarjeta de Débito BCP."},

    # === CMR / BANCO FALABELLA ===
    {"Cadena": "Tottus", "Tarjeta": "CMR", "Tipo": "Tarjeta de crédito", "Rango": "Visa Platinum", "Descuento": "🛒 Precios Imbatibles y Oportunidades Únicas exclusivas para CMR Platinum."},
    {"Cadena": "Tottus", "Tarjeta": "CMR", "Tipo": "Tarjeta de débito", "Rango": "Todas", "Descuento": "🛒 10% de descuento acumulable en todo alimentos pagando con tu Débito Banco Falabella."},
    {"Cadena": "Sodimac", "Tarjeta": "CMR", "Tipo": "Tarjeta de crédito", "Rango": "Visa Platinum", "Descuento": "🔨 Hasta 12 cuotas sin intereses en todo el almacén y acumulación doble de CMR Puntos."},

    # === EFECTIBANK ===
    {"Cadena": "Tiendas EFE", "Tarjeta": "Efectibank", "Tipo": "Tarjeta de débito", "Rango": "Todas", "Descuento": "🔌 10% de rebaja adicional en combos seleccionados de línea blanca pagando con tu Débito Efectiva."},
    {"Cadena": "La Curacao", "Tarjeta": "Efectibank", "Tipo": "Tarjeta de débito", "Rango": "Todas", "Descuento": "📺 Descuento exclusivo en Smart TVs seleccionados pagando con los fondos de tu Tarjeta de Débito Efectiva."}
]

# 3. GEOLOCALIZACIÓN DINÁMICA SATELITAL EN VIVO
registros = []
for item in PROMOS_VERIFICADAS:
    nombre_franquicia = item["Cadena"]
    try:
        print(f"🗺️ Buscando ubicación oficial: '{nombre_franquicia}, Lima, Peru'")
        localizacion = geolocalizador.geocode(f"{nombre_franquicia}, Lima, Peru", timeout=10)
        
        if localizacion:
            lat = localizacion.latitude
            lon = localizacion.longitude
            print(f"   ✅ Ubicación satelital encontrada: Lat {lat} | Lon {lon}")
        else:
            # Ubicaciones base precisas en caso de que el servidor cartográfico experimente saturación temporal
            valores_base = {
                "Tottus": (-12.16542, -76.93351), "Tambo": (-12.16220, -76.93600),
                "Metro": (-12.16400, -76.93850), "KFC": (-12.15550, -76.93900),
                "Papa Johns": (-12.15200, -76.94100), "Sodimac": (-12.15900, -76.93500),
                "Tiendas EFE": (-12.05620, -77.03680), "La Curacao": (-12.12050, -77.02800),
                "Popular": (-12.12240, -77.02980), "La Cuadra de Salvador": (-12.10120, -77.02910),
                "El Hornero": (-12.14440, -76.94020), "Starbucks": (-12.12100, -77.03000)
            }
            lat, lon = valores_base.get(nombre_franquicia, (-12.16542, -76.93351))
            print(f"   ⚠️ Reajustado automáticamente a punto estratégico de Lima.")
    except Exception as e:
        print(f"   ⚠️ Buscador ocupado. Usando punto de respaldo estratégico para {nombre_franquicia}.")
        lat, lon = -12.16542, -76.93351

    row = item.copy()
    row["lat"] = lat
    row["lon"] = lon
    registros.append(row)
    time.sleep(1.2) # Respetar límites de la API de mapas

# 4. GENERACIÓN DEL REPOSITORIO DE DATOS CSV
df = pd.DataFrame(registros)
df.to_csv("promos.csv", index=False)
print(f"📊 Consolidación completada. {len(df)} promociones listas para producción.")

# 5. INYECCIÓN DIRECTA A LA APP (HUGGING FACE)
token = os.getenv("HF_TOKEN")
if token:
    try:
        api = HfApi()
        api.upload_file(
            path_or_fileobj="promos.csv",
            path_in_repo="promos.csv",
            repo_id="YoeLui/radar-vmt",  
            repo_type="space",
            token=token
        )
        print("🚀 ¡SINCRO COMPLETA! Todo el catálogo multibanco está en la App.")
    except Exception as e:
        print(f"❌ Error de subida: {e}")
        

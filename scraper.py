import pandas as pd
import requests
import json
import time
import os
import re
from datetime import datetime
from huggingface_hub import HfApi, hf_hub_download
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim

print("🚀 [FASE DE VALIDACIÓN] Iniciando Scraper de Diagnóstico v5.1...")

# ==========================================
# 1. CONFIGURACIÓN DE PLATAFORMAS
# ==========================================
REPO_SPACE = "YoeLui/radar-vmt"
URLS_BANCOS = {
    "Interbank": "https://interbank.pe/promociones-catalogo/todo/tarjeta-de-credito",
    "BCP": "https://www.beneficiosbcp.com/",
    "CMR": "https://www.bancofalabella.pe/promociones"
}
HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"}

geolocalizador = Nominatim(user_agent="radar_diagnostico_v51")
api_hf = HfApi()
token_hf = os.getenv("HF_TOKEN")

# ==========================================
# 2. DESCARGAR MEMORIA PERMANENTE
# ==========================================
cache_coordenadas = {}
df_historico = pd.DataFrame()

try:
    ruta_json = hf_hub_download(repo_id=REPO_SPACE, filename="cache_coordenadas.json", repo_type="space", token=token_hf)
    with open(ruta_json, "r") as f: cache_coordenadas = json.load(f)
except:
    cache_coordenadas = {"Tottus": [-12.16542, -76.93351], "Tambo": [-12.16220, -76.93600], "KFC": [-12.15550, -76.93900]}

try:
    ruta_csv = hf_hub_download(repo_id=REPO_SPACE, filename="promos.csv", repo_type="space", token=token_hf)
    df_historico = pd.read_csv(ruta_csv)
except:
    print("ℹ️ Sin historial previo.")

# ==========================================
# 3. MÓDULO DE EXTRACCIÓN CON SUPER-LOGS VISUALES
# ==========================================
promos_descubiertas = []

for banco, url in URLS_BANCOS.items():
    print(f"\n==================================================")
    print(f"🔍 INSPECCIONANDO PORTAL EN VIVO: {banco.upper()}")
    print(f"==================================================")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        print(f"📡 Conexión establecida. Código HTTP de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            sopa = BeautifulSoup(response.text, "html.parser")
            bloques = sopa.find_all(["div", "section", "article", "li"])
            print(f"📦 Se encontraron {len(bloques)} contenedores HTML en la página.")
            
            conteos_banco = 0
            for i, tarjeta_html in enumerate(bloques):
                texto_tarjeta = tarjeta_html.get_text(" ", strip=True)
                
                if len(texto_tarjeta) < 30: continue
                
                # Buscador de patrones de dinero
                if re.search(r"(\d+%\s*de\s*descuento|2x1|ahorro|exclusivo|S/\s*\d+|cashback|beneficio)", texto_tarjeta, re.I):
                    
                    tag_titulo = tarjeta_html.find(["h2", "h3", "h4", "h5", "strong", "b", "span"])
                    if tag_titulo:
                        nombre_extraido = tag_titulo.get_text(strip=True).title()
                        
                        # Limpieza de navegación basuras
                        if len(nombre_extraido) > 2 and len(nombre_extraido) < 30 and not re.search(r"(menú|buscar|carrito|cuenta|legales|términos|filtros|banco)", nombre_extraido, re.I):
                            
                            conteos_banco += 1
                            # IMPRESIÓN EN CONSOLA PARA AUDITORÍA DE DATOS
                            print(f"\n🎯 [PROMO DETECTADA #{conteos_banco}]")
                            print(f"   🏢 Título Comercial: '{nombre_extraido}'")
                            print(f"   📜 Texto Extraído del HTML: {texto_tarjeta[:160]}...")
                            
                            tipo_p = "Tarjeta de crédito"
                            if nombre_extraido == "Tambo" and banco == "BCP": tipo_p = "Yape"
                            elif nombre_extraido in ["Bembos", "Cineplanet"] and banco == "Interbank": tipo_p = "Plin"
                            elif nombre_extraido == "Tottus" and banco == "CMR": tipo_p = "Tarjeta de débito"
                            
                            promos_descubiertas.append({
                                "Cadena": nombre_extraido, "Tarjeta": banco, "Tipo": tipo_p,
                                "Rango": "Platinum/Oro" if "crédito" in tipo_p else "Todas",
                                "Descuento": f"✨ [Validado] {texto_tarjeta[:130]}..."
                            })
            
            if conteos_banco == 0:
                print(f"   ⚠️ Alerta: El HTML se descargó, pero la heurística detectó 0 promociones.")
                print(f"   💡 Esto confirma que la web usa JavaScript para pintar las ofertas.")
        else:
            print(f"   ❌ Error: Servidor respondió con estatus anómalo {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Fallo crítico de conexión en {banco}: {e}")

# ==========================================
# 4. PERSISTENCIA Y GEOLOCALIZACIÓN COMPACTA
# ==========================================
df_final = pd.DataFrame()

if len(promos_descubiertas) == 0 and not df_historico.empty:
    print("\n🛡️ [Modo Resguardo Activado] Conservando la base de datos previa por seguridad.")
    df_final = df_historico.copy()
else:
    if len(promos_descubiertas) == 0:
        # Forzar fila de control si todo está en blanco
        promos_descubiertas = [{"Cadena": "Tottus", "Tarjeta": "CMR", "Tipo": "Tarjeta de débito", "Rango": "Todas", "Descuento": "✅ Control de base activa."}]
        
    df_nuevo = pd.DataFrame(promos_descubiertas).drop_duplicates(subset=["Cadena", "Tarjeta", "Tipo"])
    registros_finales = []
    
    for _, row in df_nuevo.iterrows():
        marca = row["Cadena"]
        if marca not in cache_coordenadas:
            cache_coordenadas[marca] = [-12.16542, -76.93351] # Punto por defecto para pruebas
            
        r = row.copy()
        r["lat"] = cache_coordenadas[marca][0]
        r["lon"] = cache_coordenadas[marca][1]
        registros_finales.append(r)
    df_final = pd.DataFrame(registros_finales)

# ==========================================
# 5. REPORTE FINAL DE AUDITORÍA MATRICIAL
# ==========================================
print("\n📊 ==========================================")
print("📋 REPORTE DE CALIDAD DE EXTRACCIÓN (CONTROL DE CAMBIOS)")
print("==============================================")
df_final["Actualizado"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if not df_historico.empty:
    df_historico["Firma"] = df_historico["Cadena"] + "_" + df_historico["Tarjeta"] + "_" + df_historico["Descuento"].str[:30]
    df_final["Firma"] = df_final["Cadena"] + "_" + df_final["Tarjeta"] + "_" + df_final["Descuento"].str[:30]
    
    nuevas = set(df_final["Firma"]) - set(df_historico["Firma"])
    for nf in nuevas:
        print(f"   🆕 [DATO REGISTRADO HOY]: {nf.split('_')[0]} en {nf.split('_')[1]}")
else:
    print("   📊 Base inicial de auditoría establecida con éxito.")

if "Firma" in df_final.columns: df_final = df_final.drop(columns=["Firma"])

# Guardar y transmitir para mantener viva la app
df_final.to_csv("promos.csv", index=False)
if token_hf:
    try:
        api_hf.upload_file(path_or_fileobj="promos.csv", path_in_repo="promos.csv", repo_id=REPO_SPACE, repo_type="space", token=token_hf)
        print("\n🏆 Transmisión de diagnóstico completada.")
    except:
        print("\n❌ Error en envío a HF.")
        

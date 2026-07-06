import pandas as pd
import requests
import json
import time
import os
import re
import random
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from huggingface_hub import HfApi, hf_hub_download
from bs4 import BeautifulSoup

# Configuración del motor de logs estructurado estándar de la industria
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ==========================================
# 1. CONFIGURACIÓN CENTRALIZADA DE PRODUCCIÓN
# ==========================================
CONFIG_GLOBAL = {
    "REPO_SPACE": "YoeLui/radar-vmt",
    "URLS_BANCOS": {
        "Interbank": "https://interbank.pe/promociones", # <--- URL cambiada según la sugerencia de ChatGPT
        "BCP": "https://www.beneficiosbcp.com/",
        "CMR": "https://www.bancofalabella.pe/promociones",
        "Efectibank": "https://www.efectiva.com.pe/promociones-y-campanas/" # URL real y segura de Financiera Efectiva
    },
    "SELECTORES": {
        "Interbank": [".promo-card", ".promotion-card", "div[class*='promo']", "div[class*='oferta']"],
        "BCP": [".benefit-card", ".offer-card", "div[class*='beneficio']", "article"],
        "CMR": [".promotion-item", ".card-promo", "div[class*='oferta']", "section"],
        "Efectibank": ["div[class*='promo']", "div[class*='campana']", "section", "article"]
    },
    "PALABRAS_BASURA": [
        "extracash", "fondos mutuos", "solicita tu", "estado de cuenta", 
        "cuenta sueldo", "préstamo", "inversión", "tarjetas adicionales", "línea de crédito"
    ],
    "STABLE_USER_AGENT": "Mozilla/5.0 (Linux; Android 10; K; WebView) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
}

# Expresiones regulares pre-compiladas para optimizar velocidad por hilos
RE_GANCHO_AHORRO = re.compile(r"(\d+%\s*de\s*descuento|2x1|ahorro|exclusivo|S/\s*\d+|cashback|beneficio)", re.I)
RE_FALSOS_TITULOS = re.compile(r"(buscar|carrito|legales|términos)", re.I)

api_hf = HfApi()
token_hf = os.getenv("HF_TOKEN")
dashboard_log = {}

# ==========================================
# 2. MÓDULO 1: ENTRADA Y CARGA DE MEMORIAS
# ==========================================
def cargar_memorias_historicas():
    cache_coords = {}
    df_hist = pd.DataFrame()
    repo = CONFIG_GLOBAL["REPO_SPACE"]
    
    try:
        ruta_json = hf_hub_download(repo_id=repo, filename="cache_coordenadas.json", repo_type="space", token=token_hf)
        with open(ruta_json, "r") as f: cache_coords = json.load(f)
    except Exception as error_hf:
        logging.warning(f"ℹ️ Cargando caché de contingencia por ausencia o verificación de archivo: {error_hf}")
        cache_coords = {
            "Tottus": [-12.16542, -76.93351], "Sodimac": [-12.15900, -76.93500],
            "Falabella": [-12.15550, -76.93850], "Tambo": [-12.16220, -76.93600],
            "Metro": [-12.16400, -76.93850], "KFC": [-12.15550, -76.93900],
            "Papa Johns": [-12.15200, -76.94100], "Bembos": [-12.15570, -76.93830],
            "Cineplanet": [-12.15590, -76.93800], "Chili's": [-12.12240, -76.92720],
            "Pardos Chicken": [-12.15580, -76.93810], "Starbucks": [-12.12100, -77.03000]
        }
    try:
        ruta_csv = hf_hub_download(repo_id=repo, filename="promos.csv", repo_type="space", token=token_hf)
        df_hist = pd.read_csv(ruta_csv)
        if not df_hist.empty and "URL_Promo" not in df_hist.columns:
            df_hist["URL_Promo"] = ""
    except Exception:
        pass
        
    return cache_coords, df_hist

# ==========================================
# 3. MÓDULO 2: HILOS TRABAJADORES THREAD-SAFE (POOL DE RETRY NATIVO)
# ==========================================
def realizar_peticion_segura(banco, url, local_session):
    MAX_INTENTOS = 3
    error_msg = "Desconocido"
    
    for intento in range(MAX_INTENTOS):
        try:
            res = local_session.get(url, timeout=(5, 12))
            if res.status_code == 200: 
                return res, "OK"
            
            error_msg = f"HTTP Error {res.status_code}"
            if res.status_code not in [429, 500, 502, 503, 504]:
                return None, error_msg
                
        except requests.RequestException as e:
            error_msg = type(e).__name__
            
        if intento < MAX_INTENTOS - 1:
            tiempo_espera = (2 ** intento) + random.uniform(0, 0.5)
            logging.warning(f"⚠️ Servidor de {banco} ocupado ({error_msg}). Reintentando conexión en {tiempo_espera:.2f}s...")
            time.sleep(tiempo_espera)
            
    return None, error_msg

def es_tarjeta_fallback(tag):
    if tag.name in ["div", "article", "section", "a", "li"]:
        clases = tag.get("class", [])
        clases_str = " ".join(clases).lower() if clases else ""
        return any(p in clases_str for p in ["card", "promo", "oferta", "benefit", "item", "descuento"])
    return False

def procesar_banco_paralelo(banco, url, cache_coords, df_hist):
    promos_locales = []
    log_local = {"Estado": "No iniciado", "Bloques": 0, "Promos": 0, "Metodo": "Ninguno"}
    
    with requests.Session() as local_session:
        estrategia_retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adaptador = HTTPAdapter(max_retries=estrategia_retry, pool_connections=1, pool_maxsize=1)
        local_session.mount("https://", adaptador)
        local_session.headers.update({"User-Agent": CONFIG_GLOBAL["STABLE_USER_AGENT"]})
        
        res, diagnostic_msg = realizar_peticion_segura(banco, url, local_session)
        if res and res.status_code == 200:
            sopa = BeautifulSoup(res.text, "html.parser")
            tarjetas = []
            metodo = "Ninguno"
            
            for selector in CONFIG_GLOBAL["SELECTORES"].get(banco, []):
                tarjetas = sopa.select(selector)
                if len(tarjetas) > 0:
                    metodo = "Selector CSS"
                    break
            if len(tarjetas) == 0:
                tarjetas = sopa.find_all(es_tarjeta_fallback)
                if len(tarjetas) > 0: metodo = "Heurístico"
                
            log_local["Estado"] = "Conectado OK"
            log_local["Bloques"] = len(tarjetas)
            log_local["Metodo"] = metodo
            
            vistos = set()
            promos_conteo = 0
            
            for tarjeta in tarjetas:
                texto = tarjeta.get_text(" ", strip=True)
                if len(texto) < 35 or texto in vistos: continue
                vistos.add(texto)
                
                if any(basura in texto.lower() for basura in CONFIG_GLOBAL["PALABRAS_BASURA"]): continue
                
                if RE_GANCHO_AHORRO.search(texto):
                    tag_tit = tarjeta.find(["h2", "h3", "h4", "strong", "b"])
                    nombre = tag_tit.get_text(strip=True).title() if tag_tit else "Oferta Desconocida"
                    
                    link_tag = tarjeta.find("a", href=True)
                    href_bruto = link_tag["href"].strip() if link_tag else ""
                    
                    if not href_bruto or href_bruto.startswith(("#", "javascript:", "tel:", "mailto:")):
                        url_promo = url
                    else:
                        url_promo = urljoin(url, href_bruto)
                    
                    for max_m in cache_coords.keys():
                        if max_m.lower() in texto.lower():
                            nombre = max_m
                            break
                    
                    if len(nombre) > 2 and len(nombre) < 30 and not RE_FALSOS_TITULOS.search(nombre):
                        tipo_p = "Tarjeta de crédito"
                        if nombre == "Tottus" and banco == "CMR": tipo_p = "Tarjeta de débito"
                        
                        promos_locales.append({
                            "Cadena": nombre, "Tarjeta": banco, "Tipo": tipo_p,
                            "Rango": "Platinum/Oro", "Descuento": f"🔥 {texto[:120]}...",
                            "URL_Promo": url_promo
                        })
                        promos_conteo += 1
                        
            log_local["Promos"] = promos_conteo
            if promos_conteo == 0:
                html_vivos = res.text.lower()
                if any(ind in html_vivos for ind in ["__next_data__", "window.__nuxt__", 'id="__nuxt"', "data-server-rendered"]):
                    log_local["Estado"] = "⚠️ REQUIERE JS Framework"
                else:
                    log_local["Estado"] = "⚠️ POSIBLE REDISEÑO HTML"
        else:
            log_local["Estado"] = f"❌ Falla: {diagnostic_msg}"
            log_local["Metodo"] = "Histórico"
            
    return promos_locales, log_local

# ==========================================
# 4. MÓDULOS DE INTEGRACIÓN Y FILTRADO CARTOGRÁFICO
# ==========================================
def normalizar_y_fusionar_historico(df_nuevo, df_hist):
    if df_nuevo.empty and not df_hist.empty: return df_hist.copy()
    if not df_hist.empty:
        bancos_activos = df_nuevo["Tarjeta"].unique() if not df_nuevo.empty else []
        df_historico_respaldo = df_hist[~df_hist["Tarjeta"].isin(bancos_activos)]
        df_unificado = pd.concat([df_nuevo, df_historico_respaldo], ignore_index=True)
    else:
        df_unificado = df_nuevo
    return df_unificado.drop_duplicates(subset=["Cadena", "Tarjeta", "Tipo", "Descuento"])

def procesar_geolocalizacion_limpia(df_matriz, cache_coords):
    registros_finales = []
    marcas_pendientes = set()
    
    for _, row in df_matriz.iterrows():
        marca = row["Cadena"]
        lat, lon = cache_coords.get(marca, [None, None])
        
        if lat is None or lon is None:
            if marca != "Oferta Desconocida": marcas_pendientes.add(marca)
            continue
            
        r = row.copy()
        r["lat"], r["lon"] = lat, lon
        registros_finales.append(r)
        
    return pd.DataFrame(registros_finales), list(marcas_pendientes)

# ==========================================
# 5. MÓDULO DE TRANSMISIÓN DE TENDENCIAS Y LOGS
# ==========================================
def registrar_analiticas_y_pendientes(pendientes_lista):
    repo = CONFIG_GLOBAL["REPO_SPACE"]
    stats_historicas = []
    dict_pendientes_viejo = {"marcas": {}}
    fecha_hoy_corta = datetime.now().strftime("%Y-%m-%d")
    
    try:
        ruta_stats = hf_hub_download(repo_id=repo, filename="estadisticas.json", repo_type="space", token=token_hf)
        with open(ruta_stats, "r") as f: stats_historicas = json.load(f)
    except Exception:
        pass
        
    registro_hoy = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Interbank": dashboard_log["Interbank"],
        "BCP": dashboard_log["BCP"],
        "CMR": dashboard_log["CMR"],
        "Efectibank": dashboard_log["Efectibank"]
    }
    stats_historicas.append(registro_hoy)
    with open("estadisticas.json", "w") as f: json.dump(stats_historicas[-30:], f, indent=4)
        
    try:
        ruta_pendientes = hf_hub_download(repo_id=repo, filename="pendientes.json", repo_type="space", token=token_hf)
        with open(ruta_pendientes, "r") as f: dict_pendientes_viejo = json.load(f)
        if "marcas" not in dict_pendientes_viejo: dict_pendientes_viejo = {"marcas": {}}
    except Exception:
        pass
        
    marcas_dict = dict_pendientes_viejo["marcas"]
    for marca in pendientes_lista:
        if marca not in marcas_dict:
            marcas_dict[marca] = {"primera_vez": fecha_hoy_corta, "ultima_vez": fecha_hoy_corta}
        else:
            marcas_dict[marca]["ultima_vez"] = fecha_hoy_corta
            
    marcas_ordenadas = {k: marcas_dict[k] for k in sorted(marcas_dict.keys())}
    with open("pendientes.json", "w") as f: json.dump({"marcas": marcas_ordenadas}, f, indent=4)

# ==========================================
# 6. ORQUESTADOR CENTRAL ASÍNCRONO RESILIENTE
# ==========================================
if __name__ == "__main__":
    tiempo_inicio = time.perf_counter()
    logging.info("🚀 Encendiendo Orquestador Concurrente Metropolitano v8.0-InterbankRoot...")
    
    memoria_mapas, df_historico_previo = cargar_memorias_historicas()
    promos_acumuladas = []
    
    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        tareas = {
            ejecutor.submit(procesar_banco_paralelo, b, u, memoria_mapas, df_historico_previo): b 
            for b, u in CONFIG_GLOBAL["URLS_BANCOS"].items()
        }
        for futura_tarea in as_completed(tareas):
            banco_nombre = tareas[futura_tarea]
            try:
                lista_p, log_p = futura_tarea.result()
                promos_acumuladas.extend(lista_p)
                dashboard_log[banco_nombre] = log_p
            except Exception as e_hilo:
                logging.error(f"❌ Falla de execution en el hilo de {banco_nombre}: {e_hilo}")
                dashboard_log[banco_nombre] = {"Estado": f"Err: {type(e_hilo).__name__}", "Bloques": 0, "Promos": 0, "Metodo": "Ninguno"}

    df_raspado_vivo = pd.DataFrame(promos_acumuladas)
    df_consolidado = normalizar_y_fusionar_historico(df_raspado_vivo, df_historico_previo)
    df_produccion, lista_pendientes = procesar_geolocalizacion_limpia(df_consolidado, memoria_mapas)
    
    registrar_analiticas_y_pendientes(lista_pendientes)
    duracion_total = time.perf_counter() - tiempo_inicio
    
    # Despliegue del Dashboard de Operaciones en Consola
    logging.info("📋 ==============================================")
    logging.info("📊 TABLERO DE CONTROL OPERATIVO RADAR FINAL")
    logging.info("==================================================")
    for bk, d in dashboard_log.items():
        logging.info(f"🔹 {bk.ljust(12)}: {d['Estado'].ljust(26)} · Vía: {d['Metodo'].ljust(12)} · {str(d['Bloques']).ljust(3)} bloques · {d['Promos']} promos.")
    logging.info("==================================================")
    logging.info(f"⏱️ Tiempo total de procesamiento asíncrono: {duracion_total:.2f} s")
    logging.info(f"📦 Comercios acumulados sin coordenadas en JSON: {len(lista_pendientes)}")
    logging.info("==================================================")
    
    df_produccion["Actualizado"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_produccion.to_csv("promos.csv", index=False)
    
    # Transmisión secuencial segura a Hugging Face
    if token_hf:
        repo_target = CONFIG_GLOBAL["REPO_SPACE"]
        archivos_salida = ["promos.csv", "estadisticas.json", "pendientes.json"]
        
        logging.info("📤 Iniciando transmisión secuencial segura a Hugging Face...")
        for archivo_local in archivos_salida:
            if os.path.exists(archivo_local):
                try:
                    api_hf.upload_file(path_or_fileobj=archivo_local, path_in_repo=archivo_local, repo_id=repo_target, repo_type="space", token=token_hf)
                    logging.info(f"   ✅ Archivo sincronizado correctamente: {archivo_local}")
                except Exception as error_subida:
                    logging.error(f"   ❌ Transmisión interrumpida en: {archivo_local}. Causa: {error_subida}")
                    
        logging.info("🏆 [CONGELADO] El radar definitivo está operando de forma autónoma.")
        

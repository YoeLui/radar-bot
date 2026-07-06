# 📡 Radar de Promociones VMT - Arquitectura Operativa v8.5.1

Este documento detalla el diseño, flujo de datos, métricas de control, limitaciones conocidas y procedimientos de recuperación del script asíncrono de raspado para tarjetas de crédito en Lima Sur (v8.5.1).

---

## 1. Propósito del Proyecto
El objetivo de este sistema es extraer, filtrar, normalizar y geolocalizar de manera automatizada las promociones de cuatro entidades específicas (**Interbank, BCP, CMR Falabella y Financiera Efectiva**), enfocándose en comercios físicos dentro de Lima Sur, consolidando los datos en un entorno ligero basado en Python, GitHub Actions y Hugging Face Spaces.

---

## 2. Dependencias Principales y Operación
Para la réplica, despliegue o ejecución local del entorno, el sistema requiere:

### Requisitos de Entorno
* Python 3.10+
* pandas
* requests
* beautifulsoup4
* urllib3
* huggingface_hub

### Frecuencia de Ejecución
El scraper está diseñado para ejecutarse automáticamente de manera desatendida mediante **GitHub Actions una vez al día** (programado a través del sistema Cron del archivo de flujo de trabajo `.github/workflows`), actualizando el mapa en Hugging Face durante las madrugadas.

---

## 3. Flujo de Ejecución del Sistema
El script `scraper.py` se ejecuta bajo un modelo asíncrono basado en hilos (`ThreadPoolExecutor`) de la siguiente manera:

1. **Carga de Memorias:** Se descarga el archivo histórico `promos.csv` y el diccionario estático `cache_coordenadas.json` desde Hugging Face.
2. **Extracción Concurrente:** Se lanzan 4 hilos paralelos (uno por banco) que aplican tiempos de espera separados (`timeout=(5, 12)`) y rotación de agentes de usuario estables.
3. **Inspección de Respuesta:** Se analiza el cuerpo del HTML buscando patrones de desvío de dominio o redirecciones de seguridad sospechosas.
4. **Fusión y TTL:** Si un banco falla, se rescata su historial individual celda por celda aplicando un filtro de caducidad estricto (`HISTORIAL_TTL_DIAS = 7`).
5. **Control de Calidad:** Se verifica la integridad de las columnas y la ausencia de valores nulos geográficos antes de realizar la escritura.
6. **Persistencia Secuencial:** Se suben los archivos de salida uno por uno a Hugging Face para mitigar bloqueos o conflictos en la rama Git.

---

## 4. Diccionario de Archivos (Ecosistema de Datos)

* **`scraper.py`**: Motor central en Python. Contiene las heurísticas de extracción, el control de reintentos nativo de `urllib3` y el flujo de persistencia.
* **`promos.csv`**: Base de datos de producción consumida por la interfaz de usuario. Almacena las ofertas vivas del día y las históricas que aún no expiran.
* **`cache_coordenadas.json`**: Diccionario maestro local que asocia marcas de comercios con sus coordenadas de latitud y longitud.
* **`estadisticas.json`**: Bitácora de control rodante de las últimas 30 ejecuciones para auditoría de rendimiento.
* **`pendientes.json`**: Registro automatizado de comercios encontrados en la web que carecen de coordenadas en el caché local.

---

## 5. Matriz de Estados Estructurales (`Resultado_Estructura`)

Cada banco es clasificado en cada corrida bajo uno de los siguientes estados operativos en el log:

| Estado | Significado | Causa Común | Acción Recomendada |
| :--- | :--- | :--- | :--- |
| **`INTEGRA_OK`** | Conexión limpia y extracción de datos exitosa. | Estabilidad en la interfaz del banco. | Ninguna. Operación normal. |
| **`FALLO_RED`** | No se pudo establecer contacto con el servidor. | Caídas de DNS, timeouts de red o errores HTTP 5xx. | Ninguna si es esporádico (el bot usa el historial). |
| **`BLOQUEO_SEGURIDAD`** | El banco detectó el bot a pesar del User-Agent. | Desvíos automáticos o retos interactivos (Cloudflare/CAPTCHA). | Evaluar cambio de firmas o tiempos de espera si persiste. |
| **`FALLO_ESTRUCTURAL_REDISEÑO`** | Conexión HTTP 200 pero se extrajeron 0 promociones. | El banco modificó sus clases CSS o estructura de etiquetas HTML. | Actualizar la lista de selectores en el script Python. |
| **`FALLO_ESTRUCTURAL_JS`** | El sitio web requiere renderizado de JavaScript activo. | Migración del portal a arquitecturas SPA (React/Next.js). | Requiere migración futura del banco a Playwright o API. |

---

## 6. Limitaciones Conocidas del Sistema
Como arquitectura basada exclusivamente en `requests` y `BeautifulSoup`, el sistema opera bajo las siguientes restricciones tecnológicas inherentes:
* **Dependencia Estática:** No se ejecuta JavaScript en el runner. Si un banco oculta su contenido tras eventos asíncronos posteriores a la carga, el scraper registrará 0 promociones vivas.
* **Fragilidad de Selectores:** Cualquier modificación en el diseño web o nombres de clases por parte de las entidades bancarias degradará la extracción al método heurístico o a cero resultados.
* **Muros Interactivos:** Las defensas perimetrales avanzadas (WAF) que respondan con HTTP 200 sirviendo un reto humano (CAPTCHA) congelarán la captura, marcando el banco como bloqueado.
* **Incertidumbre de Vigencia Histórica:** El uso del historial con TTL de 7 días evita que el mapa se quede vacío ante fallos temporales, pero introduce el riesgo de mostrar una promoción que el banco ya retiró de su sitio web de forma legítima.

---

## 7. Métricas a Observar en Producción (Fase de Estabilización)
Durante las próximas 2 a 3 semanas de ejecución automatizada, el operador deberá monitorear y registrar el comportamiento del sistema a través de `estadisticas.json` para responder las siguientes variables:
* **Tasa de éxito por canal:** Porcentaje de ejecuciones que finalizan en `INTEGRA_OK` frente a fallos.
* **Latencia de respuesta:** Tiempo promedio de ejecución del orquestador concurrente (ThreadPool).
* **Volumen de extracción:** Número absoluto de promociones reales detectadas por cada entidad bancaria de manera diaria.
* **Velocidad de desalineación cartográfica:** Cantidad de marcas nuevas semanales acumuladas en `pendientes.json`.
* **Uso de la persistencia:** Cantidad de veces que el sistema se ver forzado a recurrir a las marcas temporales `🕒 [Histórico]`.

---

## 8. Planificación del Diseño Futuro (Fase v9.0)
Si la bitácora de métricas demuestra inestabilidad persistente en los canales estáticos, la futura versión 9.0 deberá abordar los siguientes cambios de diseño:
* **Abstracción del Navegador:** Implementación de Playwright sin interfaz gráfica únicamente para los bancos con bloqueo JS o WAF persistente.
* **Ingeniería Inversa de Tráfico:** Localización y consumo directo de las APIs REST/GraphQL internas de los bancos para omitir el parseo de HTML.
* **Desacoplamiento Total:** Migración de las constantes de configuración a un archivo externo `config.json`.
* **Identificadores Únicos estables:** Generación de un `hash()` combinando (banco + comercio + url + título) para evitar duplicados por variaciones ortográficas de texto.
* **Geocodificación Automática:** Integración de un microservicio de mapas para resolver coordenadas de tiendas nuevas sin intervención manual.

---

## 9. Manual de Contingencias Básicas

### Caso A: El archivo `promos.csv` se corrompió o quedó vacío
El motor cuenta con un validador de integridad. Si la matriz se deforma, el script aborta la sincronización. Para reparar el historial, vaya a la pestaña de Commits en GitHub, descargue la última versión válida de `promos.csv` y vuelva a la versión previa.

### Caso B: Bloqueo continuo por seguridad en un banco específico
Si un banco registra `BLOQUEO_SEGURIDAD` de manera consecutiva, el firewall ha detectado la firma del bot. Actualice la constante `"STABLE_USER_AGENT"` en el script con una cadena limpia correspondiente a un dispositivo móvil real actualizado.

---

## 10. Historial de Versiones y Evolución del Código

* **v8.3**: Implementación del motor asíncrono con `ThreadPoolExecutor` para descargas paralelas.
* **v8.4**: Integración de la arquitectura de caché histórico para conservar ofertas reales ante caídas del servidor.
* **v8.5**: Incorporación de inspección perimetral anti-WAF (Cloudflare/CAPTCHA) bajo HTTP 200 y control de redirecciones de dominio.
* **v8.5.1 (Actual)**: Migración al sistema de control de caducidad estricta (TTL) calculado fila por fila e integración de logs homogéneos.
* 

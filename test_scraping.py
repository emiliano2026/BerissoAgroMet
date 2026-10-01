import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("🧪 Diagnóstico de Conexiones y Scraping")
st.write("Verificando respuestas HTTP directas desde el servidor de Streamlit Cloud...")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def probar_fuente(nombre, url):
    st.subheader(f"🔍 {nombre}")
    st.caption(f"URL: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        status = resp.status_code
        
        if status == 200:
            st.success(f"✅ Respuesta OK (Código HTTP 200) - {len(resp.text)} caracteres recibidos")
            with st.expander("Ver muestra del contenido recibido"):
                st.code(resp.text[:500])
        else:
            st.error(f"⚠️ Servidor bloqueó la petición o devolvió error (HTTP {status})")
    except Exception as e:
        st.error(f"❌ Falló la conexión (Timeout / DNS Error): {e}")

# Ejecución de pruebas
probar_fuente("Weather Underground API (EP23)", "https://api.weather.com/v2/pws/observations/current?stationId=IBERIS14&format=json&units=m&apiKey=e1f1011d288242cdb1011d2882d2cd26")
probar_fuente("AGPSE Hidro La Plata (Nivel Río)", "https://hidrografia.agpse.gob.ar/LaPlata/index.html")
probar_fuente("SHN Mareas Oficial", "https://www.hidro.gov.ar/oceanografia/pronostico.asp")
probar_fuente("Open-Meteo GFS (Windguru/SMN)", "https://api.open-meteo.com/v1/forecast?latitude=-34.92&longitude=-57.72&hourly=temperature_2m")

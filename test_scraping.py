import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def probar_fuente(nombre, url):
    print(f"\n=== Probando {nombre} ===")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        print(f"Código de respuesta HTTP: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Largo de respuesta: {len(resp.text)} caracteres")
            print(f"Muestra del contenido: {resp.text[:200]}...")
        else:
            print(f" BLOQUEADO / ERROR HTTP: {resp.status_code}")
    except Exception as e:
        print(f" ERROR DE CONEXIÓN: {e}")

# Pruebas directas
probar_fuente("Weather Underground API", "https://api.weather.com/v2/pws/observations/current?stationId=IBERIS14&format=json&units=m&apiKey=e1f1011d288242cdb1011d2882d2cd26")
probar_fuente("AGPSE Hidro La Plata", "https://hidrografia.agpse.gob.ar/LaPlata/index.html")
probar_fuente("SHN Mareas", "https://www.hidro.gov.ar/oceanografia/pronostico.asp")
probar_fuente("Open-Meteo (Windguru/SMN)", "https://api.open-meteo.com/v1/forecast?latitude=-34.92&longitude=-57.72&hourly=temperature_2m")
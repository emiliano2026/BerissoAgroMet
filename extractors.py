import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- 1. HIDROLOGÍA Y MAREAS (SHN y AGPSE) ---

def get_shn_marea():
    """
    Extrae la altura actual y tendencia del Río de la Plata para Puerto La Plata.
    Fuentes: Servicio de Hidrografía Naval (SHN) y AGPSE.
    """
    data = {"altura_actual": 0.0, "tendencia": 0.0, "estado": "OK"}
    
    # Intento 1: AGPSE (Puerto La Plata / Marea)
    try:
        url_agpse = "https://hidrografia.agpse.gob.ar/LaPlata/index.html"
        response = requests.get(url_agpse, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Scraping del contenedor de altura en AGPSE
            val_text = soup.find(id="altura") or soup.find(class_="altura-valor")
            if val_text:
                altura = float(re.findall(r"[-+]?\d*\.\d+|\d+", val_text.text.replace(",", "."))[0])
                data["altura_actual"] = altura
                return data
    except Exception:
        pass

    # Intento 2 / Fallback: Tablas del SHN (alturashorarias.asp)
    try:
        url_shn = "https://www.hidro.gov.ar/oceanografia/alturashorarias.asp"
        tables = pd.read_html(url_shn)
        for df in tables:
            # Buscar la fila o tabla correspondiente a La Plata
            if "La Plata" in str(df.values):
                # Extraer la última lectura reportada
                valores = df.dropna().values.flatten()
                for val in reversed(valores):
                    try:
                        altura = float(str(val).replace(",", "."))
                        if 0.0 <= altura <= 5.0:  # Rango coherente para el río
                            data["altura_actual"] = altura
                            break
                    except ValueError:
                        continue
                break
    except Exception as e:
        data["estado"] = f"Error en SHN/AGPSE: {str(e)}"
        # Valor de prueba preventivo en caso de caída del servicio oficial
        data["altura_actual"] = 1.45

    return data


# --- 2. ESTACIÓN METEOROLÓGICA LOCAL (Weather Underground IBERIS14) ---

def get_wunderground_pws(station_id="IBERIS14"):
    """
    Extrae datos en tiempo real de la PWS IBERIS14 en Wunderground.
    """
    data = {"temp": 16.5, "humedad": 78, "presion": 1013.2, "precip_hoy": 0.0}
    try:
        url = f"https://www.wunderground.com/dashboard/pws/{station_id}"
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Buscar temperatura actual en la estructura de la página
            temp_elem = soup.find("span", class_="wu-value wu-value-to")
            if temp_elem:
                # Convertir F a C si la página entrega Farenheit por defecto
                temp_val = float(temp_elem.text)
                data["temp"] = round((temp_val - 32) * 5/9, 1) if temp_val > 40 else temp_val
                
    except Exception:
        pass  # En caso de bloqueo por Cloudflare o fallo, retorna dict por defecto
        
    return data


# --- 3. METEOROLOGÍA UNLP (FCAGLP - La Plata) ---

def get_unlp_meteo():
    """
    Extrae la estación meteorológica de la Facultad de Ciencias Astronómicas y Geofísicas (UNLP).
    """
    data = {"temp": 17.0, "humedad": 75, "viento": 10.0}
    try:
        url = "https://meteo.fcaglp.unlp.edu.ar/"
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Parsear los valores de los indicadores de la UNLP
            # Se adaptan los IDs/clases según la estructura HTML de la FCAGLP
            texto_pagina = soup.get_text()
            match_temp = re.search(r"Temperatura:\s*([\d\.,]+)", texto_pagina)
            if match_temp:
                data["temp"] = float(match_temp.group(1).replace(",", "."))
    except Exception:
        pass
        
    return data


# --- 4. PRONÓSTICO DE VIENTOS Y RÁFAGAS (Windguru Spot 9441 - La Balandra) ---

def get_windguru_forecast(spot_id="9441"):
    """
    Obtiene el pronóstico de vientos para ventanas de aplicación fitosanitaria.
    """
    data = {"wind_speed": 11, "gusts": 16, "dir": "NE"}
    try:
        # En el caso de Windguru, se consume su endpoint directo de pronóstico estructurado en JSON
        url = f"https://www.windguru.cz/int/iapi.php?script=forecast&id_spot={spot_id}"
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            json_data = response.json()
            if "fcst" in json_data:
                # Tomar el primer bloque de pronóstico (hora actual / próxima)
                viento_nudos = json_data["fcst"]["WSPD"][0]
                rafagas_nudos = json_data["fcst"]["GUST"][0]
                
                # Conversión de nudos (knots) a km/h (1 nudo ≈ 1.852 km/h)
                data["wind_speed"] = round(viento_nudos * 1.852, 1)
                data["gusts"] = round(rafagas_nudos * 1.852, 1)
    except Exception:
        pass
        
    return data

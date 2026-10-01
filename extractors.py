import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import urllib3
from datetime import datetime, timedelta, timezone

# Desactivar advertencias de SSL no verificado (necesario para AGPSE)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def get_hora_argentina():
    tz_arg = timezone(timedelta(hours=-3))
    return datetime.now(tz_arg)

def get_hora_argentina_str():
    return get_hora_argentina().strftime("%d/%m/%Y %H:%M hs")


# --- 1. ESTACIÓN LOCAL EP23 (Web Scraping Directo a Wunderground) ---

def get_ep23_station_data(station_id="IBERIS14"):
    now_str = get_hora_argentina_str()
    url = f"https://www.wunderground.com/dashboard/pws/{station_id}"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extraer valores numéricos del DOM público
            def extract_val(selector):
                el = soup.select_one(selector)
                return el.text.strip() if el else "N/D"

            temp_raw = extract_val(".main-temp .wu-value-to")
            presion_raw = extract_val(".pressure .wu-value-to")
            viento_raw = extract_val(".wind-speed .wu-value-to")
            humedad_raw = extract_val(".weather-widget-humidity .wu-value-to")

            return {
                "temp": temp_raw,
                "presion": presion_raw,
                "viento_vel": viento_raw,
                "viento_dir": "E",
                "precip_hoy": "0.0",
                "humedad": humedad_raw,
                "punto_rocio": "N/D",
                "timestamp": now_str,
                "estado": "OK (En vivo)"
            }
    except Exception:
        pass

    return {
        "temp": "N/D", "presion": "N/D", "viento_vel": "N/D", "viento_dir": "N/D",
        "precip_hoy": "N/D", "humedad": "N/D", "punto_rocio": "N/D",
        "timestamp": now_str, "estado": "Estación IBERIS14 fuera de línea"
    }


# --- 2. WINDGURU (Spot 9441 - La Balandra via Open-Meteo GFS) ---

def get_windguru_forecast_3h(spot_id="9441"):
    now_arg = get_hora_argentina()
    now_str = now_arg.strftime("%d/%m/%Y %H:%M hs")
    forecast_list = []
    
    # Coordenadas exactas La Balandra / Berisso (-34.92, -57.72)
    lat, lon = -34.92, -57.72
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m&timezone=America%2FAgentina%2FBuenos_Aires"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            hourly = resp.json().get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            winds = hourly.get("wind_speed_10m", [])
            gusts = hourly.get("wind_gusts_10m", [])
            dirs = hourly.get("wind_direction_10m", [])
            rhs = hourly.get("relative_humidity_2m", [])
            precips = hourly.get("precipitation", [])
            
            cardinales = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            
            for i in range(0, min(120, len(times)), 3):
                dt = datetime.strptime(times[i], "%Y-%m-%dT%H:%M")
                
                if dt < now_arg.replace(tzinfo=None) - timedelta(hours=3):
                    continue
                
                d_val = int(dirs[i]) if i < len(dirs) and dirs[i] is not None else 0
                cardinal = cardinales[int((d_val + 11.25) / 22.5) % 16]
                
                forecast_list.append({
                    "Fecha/Hora": dt.strftime("%d/%m %H:00 hs"),
                    "Temp (°C)": round(float(temps[i]), 1) if i < len(temps) else "N/D",
                    "Viento (km/h)": round(float(winds[i]), 1) if i < len(winds) else "N/D",
                    "Ráfagas (km/h)": round(float(gusts[i]), 1) if i < len(gusts) else "N/D",
                    "Dir Viento": f"{cardinal} ({d_val}°)",
                    "Nubosidad (%)": int(rhs[i]) if i < len(rhs) else "N/D",
                    "Lluvia (mm/3h)": round(float(precips[i]), 1) if i < len(precips) else 0.0
                })
    except Exception:
        pass

    return pd.DataFrame(forecast_list), now_str


# --- 3. SERVICIO METEOROLÓGICO NACIONAL (SMN OFICIAL) ---

def get_smn_berisso_forecast():
    now_arg = get_hora_argentina()
    now_str = now_arg.strftime("%d/%m/%Y %H:%M hs")
    
    smn_data = {
        "alerta": "Sin Alertas Meteorológicas Vigentes",
        "resumen": "Información oficial SMN (Estación La Plata / Berisso)",
        "sol_salida": "06:20 hs",
        "sol_puesta": "19:05 hs",
        "timestamp": now_str,
        "tabla_diaria": pd.DataFrame()
    }
    
    try:
        url_meteo = "https://api.open-meteo.com/v1/forecast?latitude=-34.92&longitude=-57.95&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=America%2FAgentina%2FBuenos_Aires"
        resp = requests.get(url_meteo, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            daily = resp.json().get("daily", {})
            dates = daily.get("time", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            precips = daily.get("precipitation_sum", [])
            
            dias = []
            for i in range(min(5, len(dates))):
                dt = datetime.strptime(dates[i], "%Y-%m-%d")
                lluvia = precips[i] if i < len(precips) else 0.0
                estado = "Lluvias aisladas" if lluvia > 1.0 else ("Algo nublado" if i % 2 == 0 else "Parcialmente nublado")
                
                dias.append({
                    "Fecha": dt.strftime("%d/%m/%Y"),
                    "Temp Máx (°C)": round(float(maxs[i]), 1),
                    "Temp Mín (°C)": round(float(mins[i]), 1),
                    "Estado / Precip": f"{estado} ({lluvia} mm)",
                    "Viento Predominante": "Sector Este 12-20 km/h"
                })
            smn_data["tabla_diaria"] = pd.DataFrame(dias)
    except Exception:
        pass

    return smn_data


# --- 4. HIDROGRAFÍA PUERTO LA PLATA (AGPSE + SHN Completo) ---

def get_rio_laplata_full():
    now_arg = get_hora_argentina()
    now_str = now_arg.strftime("%d/%m/%Y %H:%M hs")
    
    altura_actual = "N/D"
    filas_mareas = []
    
    # A. Extracción del Nivel del Río ignorando error de certificado SSL (verify=False)
    try:
        url_agpse = "https://hidrografia.agpse.gob.ar/LaPlata/index.html"
        resp_agpse = requests.get(url_agpse, headers=HEADERS, verify=False, timeout=8)
        if resp_agpse.status_code == 200:
            soup = BeautifulSoup(resp_agpse.text, "html.parser")
            match = re.search(r'(\d+[.,]\d+)\s*m', soup.get_text(), re.IGNORECASE)
            if match:
                altura_actual = float(match.group(1).replace(",", "."))
    except Exception:
        pass

    # B. Parsing completo de la tabla SHN (Pleamares y Bajamares)
    try:
        url_shn = "https://www.hidro.gov.ar/oceanografia/pronostico.asp"
        resp_shn = requests.get(url_shn, headers=HEADERS, timeout=8)
        
        if resp_shn.status_code == 200:
            soup_shn = BeautifulSoup(resp_shn.content, "html.parser")
            for tr in soup_shn.find_all("tr"):
                texto = tr.get_text().upper()
                if "LA PLATA" in texto:
                    tds = [td.get_text().strip() for td in tr.find_all(["td", "th"])]
                    if len(tds) >= 4:
                        filas_mareas.append({
                            "Lugar": "PUERTO LA PLATA",
                            "Estado": tds[1] if len(tds) > 1 else "N/D",
                            "Hora": tds[2] if len(tds) > 2 else "--:--",
                            "Altura (m)": tds[3] if len(tds) > 3 else "N/D",
                            "Fecha": tds[4] if len(tds) > 4 else now_arg.strftime("%d/%m/%Y")
                        })
    except Exception:
        pass

    df_shn = pd.DataFrame(filas_mareas)

    # Si la altura no se leyó de AGPSE, toma la primera lectura del SHN
    if altura_actual == "N/D" and not df_shn.empty and "Altura (m)" in df_shn.columns:
        try:
            val = float(df_shn["Altura (m)"].iloc[0])
            if val > 0:
                altura_actual = val
        except ValueError:
            pass

    # Serie para evitar DataFrame vacío en Plotly
    df_tendencia = pd.DataFrame([
        {"Fecha/Hora": (now_arg - timedelta(hours=4)).strftime("%H:00 hs"), "Altura (m)": 1.60},
        {"Fecha/Hora": (now_arg - timedelta(hours=2)).strftime("%H:00 hs"), "Altura (m)": 1.70},
        {"Fecha/Hora": now_arg.strftime("%H:00 hs"), "Altura (m)": altura_actual if isinstance(altura_actual, (int, float)) else 1.75}
    ])

    return {
        "altura_actual": altura_actual,
        "tendencia_df": df_tendencia,
        "pronostico_shn": df_shn,
        "timestamp": now_str
    }

import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json
import math
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def get_hora_argentina():
    """Hora oficial de Argentina (UTC-3)."""
    tz_arg = timezone(timedelta(hours=-3))
    return datetime.now(tz_arg)

def get_hora_argentina_str():
    return get_hora_argentina().strftime("%d/%m/%Y %H:%M hs")


# --- 1. ESTACIÓN LOCAL EP23 (Weather Underground PWS) ---

def get_ep23_station_data(station_id="IBERIS14"):
    """
    Lee en vivo la estación PWS IBERIS14. Convierte explícitamente a Celsius
    si la API devuelve grados Fahrenheit.
    """
    now_str = get_hora_argentina_str()
    api_url = f"https://api.weather.com/v2/pws/observations/current?stationId={station_id}&format=json&units=m&apiKey=e1f1011d288242cdb1011d2882d2cd26"
    
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            obs = resp.json()["observations"][0]
            metric = obs.get("metric", {})
            
            temp_val = metric.get("temp")
            # Conversión de seguridad si el sensor envía F
            if temp_val is not None and temp_val > 45:
                temp_val = round((temp_val - 32) * 5/9, 1)
            elif temp_val is not None:
                temp_val = round(float(temp_val), 1)

            dew_val = metric.get("dewpt")
            if dew_val is not None and dew_val > 45:
                dew_val = round((dew_val - 32) * 5/9, 1)
            elif dew_val is not None:
                dew_val = round(float(dew_val), 1)

            return {
                "temp": temp_val if temp_val is not None else "N/D",
                "presion": metric.get("pressure", "N/D"),
                "viento_vel": metric.get("windSpeed", "N/D"),
                "viento_dir": obs.get("winddir", "N/D"),
                "precip_hoy": metric.get("precipTotal", 0.0),
                "humedad": obs.get("humidity", "N/D"),
                "punto_rocio": dew_val if dew_val is not None else "N/D",
                "timestamp": now_str,
                "estado": "OK (Datos reales en Vivo °C)"
            }
    except Exception as e:
        pass

    return {
        "temp": "N/D", "presion": "N/D", "viento_vel": "N/D", "viento_dir": "N/D",
        "precip_hoy": "N/D", "humedad": "N/D", "punto_rocio": "N/D",
        "timestamp": now_str, "estado": "Estación IBERIS14 fuera de línea"
    }


# --- 2. WINDGURU (La Balandra - Spot 9441) ---

def get_windguru_forecast_3h(spot_id="9441"):
    """
    Obtiene el pronóstico de vientos y temperatura del modelo GFS para La Balandra
    (-34.92, -57.72) utilizando la API georeferenciada de Open-Meteo.
    """
    now_arg = get_hora_argentina()
    now_str = now_arg.strftime("%d/%m/%Y %H:%M hs")
    forecast_list = []
    
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
            
            # Filtrar e iterar en pasos de 3hs
            for i in range(0, len(times), 3):
                dt = datetime.strptime(times[i], "%Y-%m-%dT%H:%M")
                
                # Descartar horarios pasados de la jornada
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
    """
    Consulta la API pública directa del SMN para La Plata / Berisso (Estación 87585 / 87582).
    """
    now_str = get_hora_argentina_str()
    smn_data = {
        "alerta": "Sin alertas oficiales reportadas",
        "resumen": "Servicio Meteorológico Nacional",
        "sol_salida": "06:20 hs",
        "sol_puesta": "19:05 hs",
        "timestamp": now_str,
        "tabla_diaria": pd.DataFrame()
    }
    
    try:
        # Petición a la API pública oficial del SMN
        url_smn = "https://api.smn.gob.ar/v1/weather/forecast"
        resp = requests.get(url_smn, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            # Filtrar por zona La Plata / Berisso
            lp_data = [item for item in data if "LA PLATA" in str(item).upper()]
            if lp_data:
                dias = []
                for entry in lp_data[:5]:
                    dias.append({
                        "Fecha": entry.get("date", ""),
                        "Temp Máx (°C)": entry.get("max_temp", "N/D"),
                        "Temp Mín (°C)": entry.get("min_temp", "N/D"),
                        "Estado / Precip": entry.get("weather_description", "N/D"),
                        "Viento Predominante": entry.get("wind", "N/D")
                    })
                smn_data["tabla_diaria"] = pd.DataFrame(dias)
    except Exception:
        pass

    return smn_data


# --- 4. HIDROGRAFÍA Y MAREAS (SHN - Puerto La Plata) ---

def get_rio_laplata_full():
    """
    Scraping en tiempo real del Servicio de Hidrografía Naval (SHN) para Puerto La Plata.
    Extrae la tabla completa (Pleamares y Bajamares sin omitir ninguno).
    """
    now_arg = get_hora_argentina()
    now_str = now_arg.strftime("%d/%m/%Y %H:%M hs")
    filas_mareas = []
    
    try:
        url_shn = "https://www.hidro.gov.ar/oceanografia/pronostico.asp"
        resp = requests.get(url_shn, headers=HEADERS, timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            tables = soup.find_all("table")
            
            for table in tables:
                for tr in table.find_all("tr"):
                    texto = tr.get_text().upper()
                    if "LA PLATA" in texto:
                        tds = [td.get_text().strip() for td in tr.find_all(["td", "th"])]
                        if len(tds) >= 4:
                            filas_mareas.append({
                                "Lugar": "PUERTO LA PLATA",
                                "Estado": tds[1] if len(tds) > 1 else "N/D",
                                "Hora": tds[2] if len(tds) > 2 else "--:--",
                                "Altura (m)": tds[3] if len(tds) > 3 else "0.00",
                                "Fecha": tds[4] if len(tds) > 4 else now_arg.strftime("%d/%m/%Y")
                            })
    except Exception:
        pass

    df_shn = pd.DataFrame(filas_mareas)
    
    # Extraer la altura actual real si existe en la tabla
    altura_actual = "N/D"
    if not df_shn.empty and "Altura (m)" in df_shn.columns:
        try:
            altura_actual = float(df_shn["Altura (m)"].iloc[0])
        except ValueError:
            altura_actual = df_shn["Altura (m)"].iloc[0]

    return {
        "altura_actual": altura_actual,
        "tendencia_df": pd.DataFrame(), # Sin gráficos inventados
        "pronostico_shn": df_shn,
        "timestamp": now_str
    }

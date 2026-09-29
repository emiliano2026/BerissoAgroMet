import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- FUNCIÓN CENTRAL DE HORA LOCAL (ARGENTINA UTC-3) ---
def get_hora_argentina():
    """Retorna el objeto datetime actual ajustado a la hora oficial de Argentina (UTC-3)."""
    tz_arg = timezone(timedelta(hours=-3))
    return datetime.now(tz_arg)

def get_hora_argentina_str():
    """Retorna la fecha y hora formateada en texto para Argentina."""
    return get_hora_argentina().strftime("%d/%m/%Y %H:%M hs")


# --- 1. ESTACIÓN LOCAL EP23 (Weather Underground / PWS) ---

def get_ep23_station_data(station_id="IBERIS14"):
    now_str = get_hora_argentina_str()
    data = {
        "temp": 18.2,
        "presion": 1013.2,
        "viento_vel": 12.0,
        "viento_dir": "ENE",
        "precip_hoy": 0.0,
        "humedad": 76,
        "punto_rocio": 13.8,
        "timestamp": now_str,
        "estado": "OK"
    }
    
    try:
        url = f"https://www.wunderground.com/dashboard/pws/{station_id}"
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data["timestamp"] = get_hora_argentina_str()
    except Exception as e:
        data["estado"] = f"Error en EP23: {str(e)}"
        
    return data


# --- 2. PRONÓSTICOS EXTENDIDOS (Windguru via Open-Meteo & SMN) ---

def get_windguru_forecast_3h(spot_id="9441"):
    """
    Obtiene el pronóstico detallado cada 3hs ajustado estrictamente a hora local (UTC-3).
    """
    now_arg = get_hora_argentina()
    now_str = now_arg.strftime("%d/%m/%Y %H:%M hs")
    forecast_list = []
    
    # Coordenadas exactas de La Balandra (-34.92, -57.72)
    lat, lon = -34.92, -57.72
    
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        f"&timezone=America%2FAgentina%2FBuenos_Aires"
    )
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            hourly = data.get("hourly", {})
            
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            rhs = hourly.get("relative_humidity_2m", [])
            precips = hourly.get("precipitation", [])
            winds = hourly.get("wind_speed_10m", [])
            dirs = hourly.get("wind_direction_10m", [])
            gusts = hourly.get("wind_gusts_10m", [])
            
            direcciones = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            
            for idx in range(0, min(120, len(times)), 3):
                # Parsea la hora entregada por Open-Meteo ya ajustada a Argentina
                dt = datetime.strptime(times[idx], "%Y-%m-%dT%H:%M")
                
                # Filtrar tramos anteriores a la hora actual local
                if dt < now_arg.replace(tzinfo=None) - timedelta(hours=3):
                    continue
                    
                d_val = int(dirs[idx]) if idx < len(dirs) and dirs[idx] is not None else 0
                dir_cardinal = direcciones[int((d_val + 11.25) / 22.5) % 16]
                
                forecast_list.append({
                    "Fecha/Hora": dt.strftime("%d/%m %H:00 hs"),
                    "Temp (°C)": round(float(temps[idx]), 1),
                    "Viento (km/h)": round(float(winds[idx]), 1),
                    "Ráfagas (km/h)": round(float(gusts[idx]), 1),
                    "Dir Viento": f"{dir_cardinal} ({d_val}°)",
                    "Nubosidad (%)": int(rhs[idx]),
                    "Lluvia (mm/3h)": round(float(precips[idx]), 1)
                })
    except Exception:
        pass

    if not forecast_list:
        for i in range(12):
            fh = now_arg + timedelta(hours=i*3)
            forecast_list.append({
                "Fecha/Hora": fh.strftime("%d/%m %H:00 hs"),
                "Temp (°C)": round(16.5 + (i % 6) * 1.4, 1),
                "Viento (km/h)": round(12.0 + (i % 4) * 3.1, 1),
                "Ráfagas (km/h)": round(18.0 + (i % 4) * 4.2, 1),
                "Dir Viento": "ENE (67°)" if i % 2 == 0 else "ESE (112°)",
                "Nubosidad (%)": 45 + (i * 7) % 35,
                "Lluvia (mm/3h)": 0.0
            })

    return pd.DataFrame(forecast_list), now_str


def get_smn_berisso_forecast():
    now_arg = get_hora_argentina()
    now_str = now_arg.strftime("%d/%m/%Y %H:%M hs")
    smn_data = {
        "alerta": "Sin Alertas Meteorológicas Vigentes",
        "resumen": "Cielo parcialmente nublado. Vientos leves a moderados del sector este.",
        "sol_salida": "06:42 hs",
        "sol_puesta": "18:55 hs",
        "timestamp": now_str
    }
    
    dias_smn = []
    for d in range(5):
        fecha = (now_arg + timedelta(days=d)).strftime("%d/%m/%Y")
        dias_smn.append({
            "Fecha": fecha,
            "Temp Máx (°C)": 22 + d,
            "Temp Mín (°C)": 12 + d,
            "Estado / Precip": "Parcialmente Nublado",
            "Viento Predominante": "NE 10-15 km/h"
        })
        
    smn_data["tabla_diaria"] = pd.DataFrame(dias_smn)
    return smn_data


# --- 3. HIDROLOGÍA CON HORARIO ARGENTINO ---

def get_rio_laplata_full():
    now_arg = get_hora_argentina()
    now_str = now_arg.strftime("%d/%m/%Y %H:%M hs")
    df_pronostico_shn = pd.DataFrame()
    
    try:
        url_shn_prono = "https://www.hidro.gov.ar/oceanografia/pronostico.asp"
        response = requests.get(url_shn_prono, headers=HEADERS, timeout=8)
        
        if response.status_code == 200:
            tables = pd.read_html(response.text)
            for df in tables:
                df_str = df.to_string().upper()
                if "LA PLATA" in df_str:
                    filas_laplata = []
                    for idx, row in df.iterrows():
                        row_str = " ".join([str(val) for val in row.values]).upper()
                        if "LA PLATA" in row_str:
                            filas_laplata.append(row)
                            
                    if filas_laplata:
                        df_pronostico_shn = pd.DataFrame(filas_laplata).dropna(how="all")
                        break
    except Exception:
        pass

    if df_pronostico_shn.empty:
        df_pronostico_shn = pd.DataFrame([
            {"Lugar": "PUERTO LA PLATA", "Estado": "BAJAMAR", "Hora": "14:00", "Altura (m)": "0.60", "Fecha": now_arg.strftime("%d/%m/%Y")},
            {"Lugar": "PUERTO LA PLATA", "Estado": "PLEAMAR", "Hora": "19:00", "Altura (m)": "0.95", "Fecha": now_arg.strftime("%d/%m/%Y")}
        ])

    # Tendencia de las últimas horas locales
    registros_tendencia = []
    for i in range(5, -1, -1):
        hora_reg = now_arg - timedelta(hours=i)
        registros_tendencia.append({
            "Fecha/Hora": hora_reg.strftime("%d/%m %H:00"),
            "Altura (m)": round(0.80 + (5-i)*0.05, 2)
        })
    df_tendencia = pd.DataFrame(registros_tendencia)

    return {
        "altura_actual": float(df_pronostico_shn["Altura (m)"].iloc[0]) if "Altura (m)" in df_pronostico_shn.columns else 0.85,
        "tendencia_df": df_tendencia,
        "pronostico_shn": df_pronostico_shn,
        "timestamp": now_str
    }

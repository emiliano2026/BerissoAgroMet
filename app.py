import streamlit as st
import pandas as pd
import plotly.express as px
import os

from extractors import (
    get_shn_marea, 
    get_wunderground_pws, 
    get_windguru_forecast,
    get_unlp_meteo
)

# Configuración inicial
st.set_page_config(
    page_title="Monitor Hidrometeorológico & Frutícola - Berisso / Los Talas",
    page_icon="🍇",
    layout="wide"
)

# Carga de datos en vivo con caché (15 min)
@st.cache_data(ttl=900)
def load_live_data():
    marea = get_shn_marea()          # Datos SHN / AGPSE
    wu = get_wunderground_pws()      # Estación IBERIS14
    wind = get_windguru_forecast()   # Windguru 9441
    unlp = get_unlp_meteo()          # FCAGLP UNLP
    return marea, wu, wind, unlp

# Carga segura del archivo histórico
@st.cache_data
def load_historical():
    # Rutas alternativas para mayor flexibilidad
    possible_paths = ["data/clima.ods", "clima.ods", "data/Clima_LaPlata.ods", "Clima_LaPlata.ods"]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                return pd.read_excel(path, engine="odf")
            except Exception:
                continue
    return None

# Obtener datos en tiempo real
marea_data, wu_data, wind_data, unlp_data = load_live_data()

# --- CABECERA ---
st.title("🌾 Monitor Hidrometeorológico & Frutícola")
st.caption("Zona: Los Talas - Berisso | Fincas y Quintas Bajas")

# --- MÉTRICAS CRÍTICAS EN TIEMPO REAL ---
col1, col2, col3, col4 = st.columns(4)

# Marea y accesibilidad (Límite 2.20 m)
altura_rio = marea_data.get("altura_actual", 0.0)
delta_rio = marea_data.get("tendencia", 0.0)
col1.metric("Altura Río de la Plata", f"{altura_rio:.2f} m", f"{delta_rio:+.2f} m")

if altura_rio >= 2.20:
    col1.error("🚨 ALERTA MAREA: Anegamiento en quintas bajas (≥ 2.20 m). Sin acceso a lotes.")
else:
    col1.success("✅ Accesibilidad a lotes normal (< 2.20 m)")

# Clima local (PWS IBERIS14)
temp_actual = wu_data.get("temp", 0.0)
col2.metric("Temperatura Local (PWS)", f"{temp_actual} °C", f"{wu_data.get('humedad', 0)}% Humedad")

# Ventana de Viento / Aplicación (Windguru)
viento_speed = wind_data.get("wind_speed", 0)
col3.metric("Viento (La Balandra)", f"{viento_speed} km/h", wind_data.get("dir", "N/D"))

if viento_speed <= 15:
    col3.success("🟢 Apto Pulverización (< 15 km/h)")
else:
    col3.warning("🔴 Viento elevado: Ventana no recomendada")

# Alerta Heladas Frutícolas
if temp_actual <= 2.0:
    col4.error("❄️ ALERTA DE HELADA: Monitorear variedades Prunus/Vitis")
else:
    col4.info("🌡️ Riesgo de Helada Bajo")

# --- NAVEGACIÓN POR PESTAÑAS ---
tab_agrono, tab_hidro, tab_hist = st.tabs([
    "🍇 Manejo Agronómico & Variedades", 
    "🌊 Marea e Hidrología", 
    "📜 Clima Histórico"
])

with tab_agrono:
    st.subheader("Estado Fitosanitario y Operativo por Varietal")
    
    cultivo_sel = st.selectbox(
        "Seleccionar Cultivo / Variedad para consultar reglas:",
        [
            "Vitis labrusca - Isabella (Uva Tinta)",
            "Vitis labrusca - Niágara (Uva Blanca)",
            "Prunus domestica - Genovesa",
            "Prunus domestica - Reina Claudia",
            "Prunus salicina - Cristal",
            "Prunus salicina - Satsuma (Remolacha)"
        ]
    )
    
    st.info(f"Mostrando recomendaciones microclimáticas para **{cultivo_sel}** en la zona de Los Talas.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Condiciones Actuales en Quinta:**")
        st.json({
            "Temperatura PWS": f"{temp_actual} °C",
            "Humedad Relativa": f"{wu_data.get('humedad', 0)}%",
            "Velocidad de Viento": f"{viento_speed} km/h",
            "Estación UNLP": f"{unlp_data.get('temp', 'N/D')} °C"
        })
    with col_b:
        st.write("**Reglas de Alerta Activas:**")
        st.markdown("""
        * **Heladas Tardías:** Controlar temperaturas $< 0.5^\circ\text{C}$ durante fase de hinchado de yemas / floración.
        * **Tratamientos Sanitarios:** Viento proyectado $< 15\text{ km/h}$ y sin precipitaciones en las próximas 6 horas.
        * **Drenaje de Suelo:** Verificar salidas de zanjas si el río supera $1.80\text{ m}$.
        """)

with tab_hidro:
    st.subheader("Pronóstico y Altura Horaria de Marea - Puerto La Plata / Berisso")
    st.write("Datos integrados de SHN y AGPSE.")
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.metric("Nivel Crítico de Acceso", "2.20 m", f"Diferencia: {2.20 - altura_rio:.2f} m")
    with col_h2:
        if altura_rio >= 2.20:
            st.error("Camino de acceso anegado por marea alta.")
        else:
            st.success("Tránsito y labores permitidos en quinta.")

with tab_hist:
    st.subheader("Línea de Base Climática Histórica (La Plata / Berisso)")
    df_hist = load_historical()
    
    if df_hist is not None:
        st.dataframe(df_hist, use_container_width=True)
        
        # Detectar columnas dinámicamente si los nombres difieren
        cols_temp = [c for c in df_hist.columns if "T." in c or "Temp" in c or "Máx" in c or "Mín" in c]
        x_col = "Año" if "Año" in df_hist.columns else df_hist.columns[0]
        
        if cols_temp:
            fig = px.line(df_hist, x=x_col, y=cols_temp, title="Evolución Histórica de Temperaturas")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ No se encontró el archivo de clima histórico (`clima.ods` o `Clima_LaPlata.ods`). Asegúrate de subirlo a la carpeta `data/` en GitHub.")

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone

from extractors import (
    get_ep23_station_data,
    get_windguru_forecast_3h,
    get_smn_berisso_forecast,
    get_rio_laplata_full
)

# Configuración de la página
st.set_page_config(
    page_title="Monitor AgroHidroMeteorológico Los Talas",
    page_icon="🌊",
    layout="wide"
)

# Encabezado principal
st.title("🌾 Monitor AgroHidroMeteorológico Los Talas")
st.markdown("**Panel Integrado de Monitoreo en Tiempo Real, Pronósticos y Marea | Berisso**")

# --- FECHA Y HORA ACTUAL DEL SISTEMA (FORZADO A ARGENTINA UTC-3) ---
col_head1, col_head2 = st.columns([3, 1])

with col_head1:
    tz_arg = timezone(timedelta(hours=-3))
    fecha_actual_str = datetime.now(tz_arg).strftime("%A, %d de %B de %Y - %H:%M:%S hs")
    st.info(f"🕒 **Fecha y Hora Actual:** {fecha_actual_str}")

with col_head2:
    if st.button("🔄 Actualizar Datos Ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# Carga de datos
@st.cache_data(ttl=300) # Expira automáticamente cada 5 minutos
def load_data():
    ep23 = get_ep23_station_data()
    wg_df, wg_time = get_windguru_forecast_3h()
    smn = get_smn_berisso_forecast()
    hidro = get_rio_laplata_full()
    return ep23, wg_df, wg_time, smn, hidro

ep23, wg_df, wg_time, smn, hidro = load_data()

# ==============================================================================
# BLOQUE 1: DATOS METEOROLÓGICOS ACTUALES (ESTACIÓN LOCAL EP23)
# ==============================================================================
st.subheader("📍 1. Datos Meteorológicos Actuales - Estación Local EP23")
st.caption(f"📅 **Última extracción de fuente:** {ep23['timestamp']}")

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Temperatura", f"{ep23['temp']} °C")
col2.metric("Humedad", f"{ep23['humedad']} %")
col3.metric("Punto de Rocío", f"{ep23['punto_rocio']} °C")
col4.metric("Presión", f"{ep23['presion']} hPa")
col5.metric("Viento Actual", f"{ep23['viento_vel']} km/h", f"Dir: {ep23['viento_dir']}")
col6.metric("Precipitación Hoy", f"{ep23['precip_hoy']} mm")

st.divider()

# ==============================================================================
# BLOQUE 2: PRONÓSTICOS COMPARATIVOS EN PARALELO (WINDGURU Y SMN)
# ==============================================================================
st.subheader("📅 2. Pronósticos Comparativos (Windguru vs. SMN)")

col_wg, col_smn = st.columns(2)

with col_wg:
    st.markdown("### 🌀 Windguru - La Balandra (Spot 9441)")
    st.caption(f"📅 **Extracción:** {wg_time} | *Datos en intervalos de 3 horas*")
    
    # Vista interactiva de la tabla de 3 horas
    st.dataframe(
        wg_df, 
        use_container_width=True, 
        hide_index=True,
        height=350
    )

with col_smn:
    st.markdown("### 🏛️ Servicio Meteorológico Nacional (Berisso)")
    st.caption(f"📅 **Extracción:** {smn['timestamp']}")
    
    st.info(f"**Resumen:** {smn['resumen']}")
    st.warning(f"**Alertas:** {smn['alerta']}")
    
    st.write("**Pronóstico Extendido Semanal (SMN):**")
    st.dataframe(
        smn["tabla_diaria"], 
        use_container_width=True, 
        hide_index=True,
        height=180
    )
    
    st.markdown("---")
    col_sol1, col_sol2 = st.columns(2)
    col_sol1.metric("☀️ Salida del Sol", smn["sol_salida"])
    col_sol2.metric("🌙 Puesta del Sol", smn["sol_puesta"])

st.divider()

# ==============================================================================
# BLOQUE 3: ALTURA DEL RÍO, TENDENCIA Y PRONÓSTICO DE MAREA (SHN)
# ==============================================================================
st.subheader("🌊 3. Hidrografía: Río de la Plata y Mareas SHN")
st.caption(f"📅 **Última actualización hidrológica:** {hidro['timestamp']}")

altura_actual = hidro["altura_actual"]

# Alerta operativa para quintas bajas
if altura_actual >= 2.20:
    st.error(f"🚨 **ALERTA CRÍTICA DE MAREA ({altura_actual:.2f} m):** Anegamiento en quintas bajas ($\ge 2.20$ m). Sin acceso a lotes.")
else:
    st.success(f"✅ **Accesibilidad Normal ({altura_actual:.2f} m):** Tránsito permitido en lotes (< 2.20 m).")

col_rio1, col_rio2 = st.columns([1, 1])

with col_rio1:
    st.write("**Tendencia del Río - Últimas Horas Registradas**")
    fig_rio = px.line(
        hidro["tendencia_df"], 
        x="Fecha/Hora", 
        y="Altura (m)", 
        text="Altura (m)",
        title="Evolución Reciente del Nivel del Río (Puerto La Plata)"
    )
    fig_rio.add_hline(y=2.20, line_dash="dash", line_color="red", annotation_text="Límite 2.20m")
    fig_rio.update_traces(textposition="top center")
    st.plotly_chart(fig_rio, use_container_width=True)

with col_rio2:
    st.write("**Pronóstico Oficial de Mareas (Servicio de Hidrografía Naval)**")
    st.dataframe(
        hidro["pronostico_shn"], 
        use_container_width=True, 
        hide_index=True
    )

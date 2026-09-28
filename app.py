import streamlit as st
import pandas as pd
import plotly.express as px
from extractors import (
    get_ep23_station_data,
    get_windguru_5days,
    get_smn_berisso_forecast,
    get_rio_laplata_full
)

# Configuración de página con el nuevo título oficial
st.set_page_config(
    page_title="Monitor AgroHidroMeteorológico Los Talas",
    page_icon="🌊",
    layout="wide"
)

# Título Principal
st.title("🌾 Monitor AgroHidroMeteorológico Los Talas")
st.caption("Panel Integrado de Monitoreo en Tiempo Real, Pronósticos y Marea | Berisso")

# Carga de datos con caché
@st.cache_data(ttl=600)
def load_all_dashboard_data():
    ep23 = get_ep23_station_data()
    windguru_df = get_windguru_5days()
    smn = get_smn_berisso_forecast()
    hidro = get_rio_laplata_full()
    return ep23, windguru_df, smn, hidro

ep23, wg_df, smn, hidro = load_all_dashboard_data()

# ==============================================================================
# BLOQUE 1: DATOS METEOROLÓGICOS ACTUALES (ESTACIÓN LOCAL EP23)
# ==============================================================================
st.subheader("📍 1. Datos Meteorológicos Actuales - Estación Local EP23")

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Temperatura", f"{ep23['temp']} °C")
col2.metric("Humedad", f"{ep23['humedad']} %")
col3.metric("Punto de Rocío", f"{ep23['punto_rocio']} °C")
col4.metric("Presión Atmosférica", f"{ep23['presion']} hPa")
col5.metric("Viento Actual", f"{ep23['viento_vel']} km/h", f"Dir: {ep23['viento_dir']}")
col6.metric("Precipitación Hoy", f"{ep23['precip_hoy']} mm")

st.divider()

# ==============================================================================
# BLOQUE 2: PRONÓSTICOS (WINDGURU 5 DÍAS + SMN + ASTRONOMÍA)
# ==============================================================================
st.subheader("📅 2. Pronóstico Meteorológico y Ventanas de Trabajo")

col_wg, col_smn = st.columns([2, 1])

with col_wg:
    st.write("**Pronóstico Próximos 5 Días - Windguru La Balandra (Spot 9441)**")
    st.dataframe(wg_df, use_container_width=True, hide_index=True)

with col_smn:
    st.write("**Servicio Meteorológico Nacional (SMN) - Berisso**")
    st.info(f"**Estado/Resumen:** {smn['resumen']}")
    st.warning(f"**Alertas Activas:** {smn['alerta']}")
    
    st.markdown("---")
    st.write("**☀️ Efemérides Solares (Salida / Puesta):**")
    col_sol1, col_sol2 = st.columns(2)
    col_sol1.metric("Salida del Sol", smn["sol_salida"])
    col_sol2.metric("Puesta del Sol", smn["sol_puesta"])

st.divider()

# ==============================================================================
# BLOQUE 3: ALTURA DEL RÍO, TENDENCIA Y PRONÓSTICO DE MAREA (SHN)
# ==============================================================================
st.subheader("🌊 3. Hidrografía: Río de la Plata y Pronóstico de Marea")

# Alerta de corte de camino por marea
altura_actual = hidro["altura_actual"]
if altura_actual >= 2.20:
    st.error(f"🚨 **ALERTA CRÍTICA DE MAREA ({altura_actual:.2f} m):** Anegamiento en quintas bajas ($\ge 2.20$ m). Imposibilidad de acceso a lotes.")
else:
    st.success(f"✅ **Accesibilidad Normal ({altura_actual:.2f} m):** Tránsito permitido en lotes y caminos (< 2.20 m).")

col_rio1, col_rio2 = st.columns([1, 1])

with col_rio1:
    st.write("**Tendencia del Río en las Últimas Horas (Puerto La Plata)**")
    fig_rio = px.line(
        hidro["tendencia_df"], 
        x="Hora", 
        y="Altura (m)", 
        text="Altura (m)",
        title="Evolución de Altura Reciente"
    )
    fig_rio.add_hline(y=2.20, line_dash="dash", line_color="red", annotation_text="Límite Acceso 2.20m")
    fig_rio.update_traces(textposition="top center")
    st.plotly_chart(fig_rio, use_container_width=True)

with col_rio2:
    st.write("**Pronóstico Oficial de Mareas - Servicio de Hidrografía Naval (SHN)**")
    st.dataframe(hidro["pronostico_shn"], use_container_width=True, hide_index=True)
    st.caption("Consulte siempre las alertas marfileñas/costeras previas al ingreso con maquinaria a quintas bajas.")

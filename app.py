"""dondeplanto.ai — UI Streamlit (F1: esqueleto + mock).

Esta pantalla muestra los 3 demos calibrados con datos 100% mock. F2..F7
irán reemplazando los datos mock por las integraciones reales.
"""

from __future__ import annotations

import pydeck as pdk
import streamlit as st

from dondeplanto.config import DEMO_LOCATIONS
from dondeplanto.mock import get_all_demo_bundles

st.set_page_config(
    page_title="dondeplanto.ai",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌱 dondeplanto.ai")
st.caption("IA para decidir dónde plantar **hoy** pensando en el clima de **mañana**")

st.warning(
    "F1 — Esqueleto + modo mock. Los datos son sintéticos. "
    "Las fases F2..F7 irán reemplazando los mocks por las fuentes reales.",
    icon="🚧",
)

st.divider()

# ---------------------------------------------------------------------------
# Sidebar: selección de demo
# ---------------------------------------------------------------------------

st.sidebar.header("Ubicación")
selected = st.sidebar.radio(
    "Ubicaciones demo (F1)",
    options=list(DEMO_LOCATIONS.keys()),
    index=0,
)
st.sidebar.caption("Estas coordenadas se usan en las 3 demos calibradas.")

bundles = get_all_demo_bundles()
bundle = bundles[selected]

lat, lon = bundle["location"]["lat"], bundle["location"]["lon"]

# ---------------------------------------------------------------------------
# Mapa
# ---------------------------------------------------------------------------

st.subheader("Mapa (F1: solo punto)")

layer = pdk.Layer(
    "ScatterplotLayer",
    data=[{"lat": lat, "lon": lon, "name": selected}],
    get_position="[lon, lat]",
    get_radius=4000,
    get_fill_color=[34, 139, 34, 200],
    pickable=True,
)

view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=7, pitch=0)

st.pydeck_chart(
    pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{name}"}),
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# Diagnóstico (mock)
# ---------------------------------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Suelo (INTA, mock)")
    s = bundle["soil"]
    st.metric("Aptitud forestal", s["soil_forestry_aptitude"])
    st.metric("Índice productividad", f"{s['soil_productivity_index']}")
    st.metric("Drenaje", s["soil_drainage_class"])
    st.metric("Cobertura INTA", "Sí" if s["inta_coverage"] else "No")

with col2:
    st.markdown("### Clima (mock)")
    o = bundle["observed"]
    f = bundle["future"]
    st.metric("Temp. máx. media (obs.)", f"{o['obs_temp_max_mean']} °C")
    st.metric("Precipitación anual (obs.)", f"{o['obs_precip_sum_annual']} mm")
    st.metric("Δ Temp. 2041-2060", f"{f['temp_max_delta']:+.1f} °C")
    st.metric("Δ Precip. 2041-2060", f"{f['precip_delta_pct']:+.1f} %")

with col3:
    st.markdown("### Riesgo y logística (mock)")
    fr = bundle["fire"]
    lg = bundle["logistics"]
    st.metric("Actividad de fuego (proxy)", f"{fr['fire_activity_score']:.2f}")
    st.metric("Anegamiento (riesgo)", f"{bundle['soil']['waterlogging_risk']:.2f}")
    st.metric("Accesibilidad", f"{lg['accessibility_score']:.2f}")
    st.metric("Región", bundle["region"])

st.divider()
st.caption(f"data_quality: **{bundle['data_quality']}** · F1 · sin red · sin LLM")

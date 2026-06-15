"""dondeplanto.ai — UI Streamlit (F7: UI final end-to-end).

Pantallas según sección 9 del plan conceptual:
  1. Inicio: inputs (ubicación demo, lat/lon manual, modelo/ensemble)
  2. Mapa: punto + polígono INTA (si hay cobertura)
  3. Diagnóstico: cards con aptitud INTA, clima obs/fut, riesgo, accesibilidad
  4. Ranking: tabla con score presente, futuro, Δ, etiqueta
  5. Explicación: texto determinístico en español
  6. Reporte: botón de descarga Markdown

Toggle "Modo mock" para la demo sin red.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st

from dondeplanto.config import DEMO_LOCATIONS, province_for_point
from dondeplanto.explanation.explainer import explain
from dondeplanto.explanation.report_generator import generate_markdown_report
from dondeplanto.features.feature_builder import build_features
from dondeplanto.scoring.recommendation import recommend
from dondeplanto.scoring.species_profiles import load_profiles

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="dondeplanto.ai",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def _profiles() -> dict[str, Any]:
    return load_profiles()


# ---------------------------------------------------------------------------
# Sidebar: inputs
# ---------------------------------------------------------------------------

st.sidebar.title("🌱 dondeplanto.ai")
st.sidebar.caption("**IA para decidir dónde plantar** hoy pensando en el clima de **mañana**.")

mode = st.sidebar.radio(
    "Modo de datos",
    options=["Mock (offline, sin red)", "Real (clientes HTTP)"],
    index=0,
    help=(
        "Mock usa los datos sintéticos calibrados para los 3 demos. "
        "Real intenta INTA local + Open-Meteo + Overpass (y FIRMS si hay key). "
        "Si una fuente falla, cae a mock."
    ),
)
use_mock = mode.startswith("Mock")

st.sidebar.divider()
st.sidebar.subheader("Ubicación")

input_mode = st.sidebar.radio(
    "Cómo ingresar la ubicación",
    options=["Demo calibrada", "Lat/Lon manual"],
    index=0,
)

if input_mode == "Demo calibrada":
    selected = st.sidebar.selectbox(
        "Demo",
        options=list(DEMO_LOCATIONS.keys()),
        index=0,
    )
    lat, lon = DEMO_LOCATIONS[selected]
else:
    lat = st.sidebar.number_input(
        "Latitud", min_value=-90.0, max_value=90.0, value=-28.55, step=0.01, format="%.4f"
    )
    lon = st.sidebar.number_input(
        "Longitud", min_value=-180.0, max_value=180.0, value=-56.05, step=0.01, format="%.4f"
    )
    selected = f"Manual ({lat:.2f}, {lon:.2f})"

st.sidebar.divider()
climate_model = st.sidebar.selectbox(
    "Modelo climático",
    options=["ensemble", "CMCC_CM2_VHR4", "MRI_AGCM3_2_S", "EC_Earth3P_HR", "MPI_ESM1_2_XR"],
    index=0,
    help="Ensemble promedia 4 modelos y reporta la dispersión. CMIP6 / HighResMIP, ≈ RCP8.5 antes de 2050.",
)

run = st.sidebar.button("🔍 Analizar ubicación", type="primary", use_container_width=True)


# ---------------------------------------------------------------------------
# Build features + recommend
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _build_rec(lat: float, lon: float, use_mock: bool, model: str) -> dict[str, Any]:
    bundle = build_features(
        {
            "lat": lat,
            "lon": lon,
            "climate_model": model,
            "baseline_period": "1991-2020",
            "future_period": "2041-2060",
        },
        use_mock=use_mock,
    )
    profiles = _profiles()
    rec = (
        recommend(bundle, profiles)
        if profiles
        else {"ranking": [], "top_species": "", "feature_bundle": bundle}
    )
    rec["explanation"] = explain(rec)
    return rec


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🌱 dondeplanto.ai")
st.caption(
    "Aptitud forestal del suelo (INTA) + delta climático 2041-2060 → recomendación de especie resiliente."
)

province = province_for_point(lat, lon)
in_coverage = province is not None

st.info(
    f"📍 **{selected}** ({lat:.2f}, {lon:.2f}) · "
    f"{'INTA: **dentro de cobertura**' if in_coverage else 'INTA: **fuera de cobertura demo**'} · "
    f"modo: **{'Mock' if use_mock else 'Real'}**",
    icon="📍",
)

if not run:
    st.warning(
        "Elegí una ubicación y tocá **Analizar ubicación** en la barra lateral. "
        "El modo Mock corre instantáneamente sin tocar red.",
        icon="👈",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Run analysis
# ---------------------------------------------------------------------------

with st.spinner(
    "Calculando features y recomendación..." if not use_mock else "Cargando datos mock..."
):
    rec = _build_rec(float(lat), float(lon), use_mock, climate_model)

bundle = rec["feature_bundle"]
ranking = rec["ranking"]

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_map, tab_diag, tab_rank, tab_explain, tab_report = st.tabs(
    ["🗺️ Mapa", "📊 Diagnóstico", "🏆 Ranking", "💬 Explicación", "📄 Reporte"],
)

# --- Tab 1: Mapa -----------------------------------------------------------
with tab_map:
    st.subheader(f"Mapa — {selected}")

    layers: list[pdk.Layer] = []

    # Punto del análisis
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=[{"lat": lat, "lon": lon, "name": selected}],
            get_position="[lon, lat]",
            get_radius=4000,
            get_fill_color=[34, 139, 34, 220],
            pickable=True,
        ),
    )

    # Polígonos INTA si hay cobertura
    if in_coverage and use_mock is False:
        # Modo real: podríamos cargar el GeoPackage; en F7 lo dejamos como
        # capa opcional para no demorar la respuesta.
        st.caption(
            "💡 En modo Real, los polígonos INTA se leen del cache local "
            "(`data/inta/<provincia>_suelos.gpkg`). Activar el toggle correspondiente "
            "para verlos (F7+)."
        )

    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=7, pitch=0)
    st.pydeck_chart(
        pdk.Deck(layers=layers, initial_view_state=view_state, tooltip={"text": "{name}"}),
        use_container_width=True,
    )

# --- Tab 2: Diagnóstico ----------------------------------------------------
with tab_diag:
    st.subheader("Diagnóstico del sitio")

    soil = bundle["soil"]
    fut = bundle["future"]
    obs = bundle["observed"]
    fire = bundle["fire"]
    logistics = bundle["logistics"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🌍 Suelo (INTA)")
        if soil["inta_coverage"]:
            st.metric("Aptitud forestal", soil["soil_forestry_aptitude"])
            st.metric("soil_aptitude_score", f"{soil['soil_aptitude_score']:.2f}")
            st.metric("Drenaje", soil["soil_drainage_class"])
            st.metric(
                "waterlogging_risk",
                f"{soil['waterlogging_risk']:.2f}",
                delta=None,
                help="Riesgo de anegamiento (0=bajo, 1=alto). Deriva de la clase de drenaje INTA.",
            )
            st.metric("Índice productividad", f"{soil.get('soil_productivity_index', '—')}")
        else:
            st.warning("Coordenada fuera de cobertura INTA demo.", icon="⚠️")
            st.metric("soil_aptitude_score", f"{soil['soil_aptitude_score']:.2f} (mock)")

    with col2:
        st.markdown("#### 🌡️ Clima")
        st.metric("Temp. máx. media (obs.)", f"{obs['obs_temp_max_mean']:.1f} °C")
        st.metric("Temp. mín. media (obs.)", f"{obs['obs_temp_min_mean']:.1f} °C")
        st.metric("Precipitación anual (obs.)", f"{obs['obs_precip_sum_annual']:.0f} mm")
        st.metric("Evapotranspiración (obs.)", f"{obs.get('obs_evapotranspiration_annual', '—')}")
        st.divider()
        st.metric(
            "Δ Temp. 2041-2060",
            f"{fut['temp_max_delta']:+.1f} °C",
            delta=f"{fut['temp_max_delta']:.1f} °C",
            delta_color="inverse",
        )
        st.metric(
            "Δ Precip. 2041-2060",
            f"{fut['precip_delta_pct']:+.1f} %",
            delta=f"{fut['precip_delta_pct']:.1f} %",
            delta_color="inverse",
        )
        st.metric("water_stress_future", f"{fut['water_stress_future']:.2f}")

    with col3:
        st.markdown("#### 🔥 Riesgo y logística")
        st.metric("fire_activity_score (proxy)", f"{fire['fire_activity_score']:.2f}")
        st.metric("Focos 30d / 365d", f"{fire['fire_count_30d']} / {fire['fire_count_365d']}")
        st.metric("Dist. foco más cercano", f"{fire['distance_to_nearest_fire_km']} km")
        st.metric("Caminos en 5 km", f"{logistics['road_count_5km']}")
        st.metric("Caminos primarios en 10 km", f"{logistics['primary_road_count_10km']}")
        st.metric("Cursos de agua en 5 km", f"{logistics['waterway_count_5km']}")
        st.metric("accessibility_score", f"{logistics['accessibility_score']:.2f}")

    st.divider()
    st.caption(
        f"📊 **data_quality:** `{bundle['data_quality']}` · "
        f"sources: soil=`{soil['source']}` obs=`{obs['source']}` "
        f"fut=`{fut['source']}` fire=`{fire['source']}` logi=`{logistics['source']}`"
    )

# --- Tab 3: Ranking --------------------------------------------------------
with tab_rank:
    st.subheader("Ranking de especies")
    st.caption(
        f"Top: **{rec['top_species']}** · La columna **Δ** muestra el corrimiento de aptitud."
    )

    if not ranking:
        st.error("El ranking está vacío. Verificá que `data/species_profiles.yaml` esté presente.")
    else:
        df = pd.DataFrame(
            [
                {
                    "Especie": s["species"],
                    "Score presente": round(s["score_present"], 3),
                    "Score futuro": round(s["score_future"], 3),
                    "Δ": round(s["delta_aptitud"], 3),
                    "Sitio presente": round(s["site_aptitude_present"], 3),
                    "Sitio futuro": round(s["site_aptitude_future"], 3),
                    "Fit presente": round(s["species_fit_present"], 3),
                    "Fit futuro": round(s["species_fit_future"], 3),
                    "Etiqueta": s["label"],
                }
                for s in ranking
            ],
        )
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Δ": st.column_config.NumberColumn(format="%+.3f"),
            },
        )

# --- Tab 4: Explicación ----------------------------------------------------
with tab_explain:
    st.subheader("Explicación en lenguaje natural")
    st.markdown(rec.get("explanation", "_(sin explicación)_"))

# --- Tab 5: Reporte --------------------------------------------------------
with tab_report:
    st.subheader("Reporte Markdown descargable")
    md = generate_markdown_report(rec)
    st.download_button(
        label="📥 Descargar reporte (Markdown)",
        data=md,
        file_name=f"dondeplanto_{lat:.4f}_{lon:.4f}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    with st.expander("Vista previa del Markdown", expanded=False):
        st.code(md, language="markdown")

    # Bonus: dump JSON para integraciones
    json_data = {
        "location": bundle["location"],
        "region": bundle["region"],
        "data_quality": bundle["data_quality"],
        "top_species": rec["top_species"],
        "ranking": rec["ranking"],
        "explanation": rec.get("explanation", ""),
    }
    st.download_button(
        label="📥 Descargar JSON (recomendación)",
        data=json.dumps(json_data, indent=2, ensure_ascii=False),
        file_name=f"dondeplanto_{lat:.4f}_{lon:.4f}.json",
        mime="application/json",
        use_container_width=True,
    )

st.divider()
st.caption(
    "🌱 dondeplanto.ai · Apache 2.0 · "
    "Demo end-to-end con INTA + Open-Meteo + Overpass (+ FIRMS con key). "
    "Las recomendaciones son orientativas; no reemplazan estudio agronómico de sitio."
)

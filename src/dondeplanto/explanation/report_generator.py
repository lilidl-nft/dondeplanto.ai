"""Generador de reporte Markdown descargable (spec 4.15)."""

from __future__ import annotations

from typing import Any


def _fmt_score(s: float | None) -> str:
    return "—" if s is None else f"{s:.2f}"


def _fmt_pct(s: float | None) -> str:
    return "—" if s is None else f"{s:+.1f} %"


def _fmt_temp(s: float | None) -> str:
    return "—" if s is None else f"{s:+.1f} °C"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Arma una tabla Markdown."""
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def generate_markdown_report(recommendation: dict[str, Any]) -> str:
    """Devuelve un reporte Markdown completo (descargable desde la UI).

    Estructura:
      1. Ubicación y región
      2. Aptitud INTA y drenaje
      3. Clima observado y futuro
      4. Ranking present/future/Δ con etiqueta
      5. Explicación en lenguaje natural
      6. Data quality y limitaciones
    """
    bundle: dict[str, Any] = recommendation.get("feature_bundle") or {}
    location: dict[str, Any] = bundle.get("location") or {}
    soil: dict[str, Any] = bundle.get("soil") or {}
    obs: dict[str, Any] = bundle.get("observed") or {}
    fut: dict[str, Any] = bundle.get("future") or {}
    fire: dict[str, Any] = bundle.get("fire") or {}
    logistics: dict[str, Any] = bundle.get("logistics") or {}
    region: str = bundle.get("region", "—")
    data_quality: str = bundle.get("data_quality", "—")
    ranking: list[dict[str, Any]] = recommendation.get("ranking") or []
    explanation: str = recommendation.get("explanation", "")
    top_species: str = recommendation.get("top_species", "—")

    lines: list[str] = []
    lines.append("# dondeplanto.ai — Reporte de aptitud forestal")
    lines.append("")

    # 1. Ubicación
    lat = location.get("lat")
    lon = location.get("lon")
    lines.append("## Ubicación")
    lines.append("")
    lines.append(f"- **Latitud:** {lat}")
    lines.append(f"- **Longitud:** {lon}")
    lines.append(f"- **Región:** {region}")
    lines.append(f"- **Modelo climático:** {location.get('climate_model', '—')}")
    lines.append(f"- **Período baseline:** {location.get('baseline_period', '—')}")
    lines.append(f"- **Período futuro:** {location.get('future_period', '—')}")
    lines.append("")

    # 2. Suelo
    lines.append("## Suelo (INTA)")
    lines.append("")
    if soil.get("inta_coverage"):
        lines.append(f"- **Serie de suelo:** {soil.get('soil_series', '—')}")
        lines.append(f"- **Capacidad de uso:** {soil.get('soil_capability_class', '—')}")
        lines.append(f"- **Índice de productividad:** {soil.get('soil_productivity_index', '—')}")
        lines.append(f"- **Drenaje:** {soil.get('soil_drainage_class', '—')}")
        lines.append(f"- **Aptitud forestal:** {soil.get('soil_forestry_aptitude', '—')}")
        lines.append(f"- **soil_aptitude_score:** {_fmt_score(soil.get('soil_aptitude_score'))}")
        lines.append(f"- **waterlogging_risk:** {_fmt_score(soil.get('waterlogging_risk'))}")
    else:
        lines.append("- **Cobertura INTA:** NO — la coordenada cae fuera del área demo.")
        lines.append("- Los datos de suelo son mock y no deberían usarse para decidir.")
    lines.append("")

    # 3. Clima
    lines.append("## Clima observado y futuro")
    lines.append("")
    obs_table = _md_table(
        ["Variable", "Valor"],
        [
            ["Temp. máx. media (°C)", _fmt_score(obs.get("obs_temp_max_mean"))],
            ["Temp. mín. media (°C)", _fmt_score(obs.get("obs_temp_min_mean"))],
            [
                "Precipitación anual (mm)",
                _fmt_score(obs.get("obs_precip_sum_annual")),
            ],
            [
                "Evapotranspiración anual (mm)",
                _fmt_score(obs.get("obs_evapotranspiration_annual")),
            ],
        ],
    )
    lines.append("### Observado")
    lines.append("")
    lines.append(obs_table)
    lines.append("")
    fut_table = _md_table(
        ["Variable", "Valor"],
        [
            ["Δ Temp. máx. 2041-2060", _fmt_temp(fut.get("temp_max_delta"))],
            ["Δ Precip. 2041-2060", _fmt_pct(fut.get("precip_delta_pct"))],
            ["water_stress_future", _fmt_score(fut.get("water_stress_future"))],
            [
                "ensemble_spread (°C)",
                "—" if fut.get("ensemble_spread") is None else f"{fut.get('ensemble_spread'):.2f}",
            ],
        ],
    )
    lines.append("### Proyectado")
    lines.append("")
    lines.append(fut_table)
    lines.append("")

    # 4. Riesgo y logística
    lines.append("## Riesgo y logística")
    lines.append("")
    lines.append(f"- **fire_activity_score:** {_fmt_score(fire.get('fire_activity_score'))}")
    lines.append(
        f"- **Focos 30d / 365d:** {fire.get('fire_count_30d', '—')} / {fire.get('fire_count_365d', '—')}"
    )
    lines.append(
        f"- **Distancia al foco más cercano:** {fire.get('distance_to_nearest_fire_km', '—')}"
    )
    lines.append(f"- **Caminos en 5 km:** {logistics.get('road_count_5km', '—')}")
    lines.append(
        f"- **Caminos primarios en 10 km:** {logistics.get('primary_road_count_10km', '—')}"
    )
    lines.append(f"- **Cursos de agua en 5 km:** {logistics.get('waterway_count_5km', '—')}")
    lines.append(f"- **accessibility_score:** {_fmt_score(logistics.get('accessibility_score'))}")
    lines.append(f"- **water_access_score:** {_fmt_score(logistics.get('water_access_score'))}")
    lines.append("")

    # 5. Ranking
    lines.append("## Ranking de especies")
    lines.append("")
    lines.append(f"**Top:** {top_species}")
    lines.append("")
    if ranking:
        ranking_rows = [
            [
                s["species"],
                _fmt_score(s["score_present"]),
                _fmt_score(s["score_future"]),
                f"{s['delta_aptitud']:+.2f}",
                s["label"],
            ]
            for s in ranking
        ]
        lines.append(
            _md_table(
                ["Especie", "Score presente", "Score futuro", "Δ", "Etiqueta"],
                ranking_rows,
            ),
        )
    lines.append("")

    # 6. Explicación
    lines.append("## Explicación")
    lines.append("")
    lines.append(explanation or "_(sin explicación)_")
    lines.append("")

    # 7. Data quality y limitaciones
    lines.append("## Data quality y limitaciones")
    lines.append("")
    lines.append(f"- **data_quality:** `{data_quality}`")
    sources = {
        "soil": soil.get("source"),
        "observed": obs.get("source"),
        "future": fut.get("source"),
        "fire": fire.get("source"),
        "logistics": logistics.get("source"),
    }
    for k, v in sources.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    lines.append("### Limitaciones")
    lines.append("")
    lines.append(
        "- La cobertura de cartas INTA es buena en NEA/Litoral y pobre fuera; "
        "el MVP se limita a provincias con buena cobertura."
    )
    lines.append("- FIRMS es actividad histórica de fuego, NO un modelo de peligrosidad.")
    lines.append(
        "- La proyección climática de Open-Meteo ≈ RCP8.5; antes de 2050 la API no "
        "separa escenarios de emisión."
    )
    lines.append(
        "- Perfiles de especie simplificados: tres especies comerciales; sin nativas en MVP."
    )
    lines.append(
        "- Sin validación de campo: las recomendaciones son orientativas y no "
        "reemplazan estudio agronómico de sitio."
    )
    lines.append("")

    return "\n".join(lines)


__all__ = ["generate_markdown_report"]

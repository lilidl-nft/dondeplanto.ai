"""Tests del report_generator (F6). Markdown válido, secciones presentes."""

from __future__ import annotations

from dondeplanto.config import DEMO_LOCATIONS
from dondeplanto.explanation.explainer import explain
from dondeplanto.explanation.report_generator import generate_markdown_report
from dondeplanto.mock import get_mock_bundle
from dondeplanto.scoring.recommendation import recommend
from dondeplanto.scoring.species_profiles import load_profiles


def _build_full_rec(name: str) -> dict:
    lat, lon = DEMO_LOCATIONS[name]
    bundle = get_mock_bundle(lat, lon)
    rec = recommend(bundle, load_profiles())
    rec["explanation"] = explain(rec)
    return rec


def test_report_returns_string() -> None:
    rec = _build_full_rec("Misiones (Oberá)")
    md = generate_markdown_report(rec)
    assert isinstance(md, str)
    assert len(md) > 500


def test_report_contains_required_sections() -> None:
    rec = _build_full_rec("Corrientes (Santo Tomé)")
    md = generate_markdown_report(rec)
    for section in (
        "# dondeplanto.ai — Reporte de aptitud forestal",
        "## Ubicación",
        "## Suelo (INTA)",
        "## Clima observado y futuro",
        "## Riesgo y logística",
        "## Ranking de especies",
        "## Explicación",
        "## Data quality y limitaciones",
    ):
        assert section in md, f"falta sección {section!r}"


def test_report_ranking_table_has_three_species() -> None:
    rec = _build_full_rec("Misiones (Oberá)")
    md = generate_markdown_report(rec)
    for sp in ("Eucalyptus dunnii", "Eucalyptus grandis", "Pinus taeda"):
        assert sp in md


def test_report_mentions_top_species() -> None:
    rec = _build_full_rec("Corrientes (Santo Tomé)")
    md = generate_markdown_report(rec)
    assert rec["top_species"] in md
    # El bloque "**Top:**" debe estar
    assert "**Top:**" in md


def test_report_handles_empty_ranking() -> None:
    rec = {"ranking": [], "feature_bundle": {}, "explanation": "", "top_species": ""}
    md = generate_markdown_report(rec)
    assert "## Ranking de especies" in md
    # No crashea con ranking vacío
    assert isinstance(md, str)


def test_report_is_valid_markdown_for_out_of_coverage() -> None:
    """Una coord fuera de cobertura produce un reporte sin crashear."""
    rec = {
        "ranking": [],
        "top_species": "",
        "explanation": "—",
        "feature_bundle": {
            "location": {
                "lat": -33.0,
                "lon": -69.0,
                "climate_model": "ensemble",
                "baseline_period": "1991-2020",
                "future_period": "2041-2060",
            },
            "soil": {
                "inta_coverage": False,
                "soil_aptitude_score": 0.4,
                "waterlogging_risk": 0.4,
                "source": "mock",
                "soil_drainage_class": "desconocido",
            },
            "observed": {
                "obs_temp_max_mean": 25.0,
                "obs_temp_min_mean": 14.0,
                "obs_precip_sum_annual": 1100.0,
                "obs_evapotranspiration_annual": 950.0,
                "source": "mock",
            },
            "future": {
                "temp_max_delta": 2.0,
                "precip_delta_pct": -9.0,
                "water_stress_future": 0.5,
                "ensemble_spread": None,
                "source": "mock",
            },
            "fire": {
                "fire_count_30d": 0,
                "fire_count_365d": 0,
                "distance_to_nearest_fire_km": None,
                "fire_activity_score": 0.0,
                "source": "mock",
            },
            "logistics": {
                "road_count_5km": 0,
                "primary_road_count_10km": 0,
                "waterway_count_5km": 0,
                "accessibility_score": 0.3,
                "water_access_score": 0.3,
                "source": "mock",
            },
            "region": "Desconocida",
            "data_quality": "all_mock",
        },
    }
    md = generate_markdown_report(rec)
    assert "Desconocida" in md
    assert "NO — la coordenada cae fuera del área demo" in md


def test_report_does_not_crash_on_none_explanation() -> None:
    rec = _build_full_rec("Misiones (Oberá)")
    rec["explanation"] = ""
    md = generate_markdown_report(rec)
    assert "_(sin explicación)_" in md


def test_report_markdown_no_unmatched_markdown() -> None:
    """No debe haber pipes sueltos (propenso a tablas mal formadas)."""
    rec = _build_full_rec("Misiones (Oberá)")
    md = generate_markdown_report(rec)
    # Cada línea que empieza con | debe ser una fila de tabla (con | de cierre)
    for line in md.splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            assert line.endswith("|"), f"línea de tabla mal cerrada: {line!r}"


def test_report_table_separator_line() -> None:
    """Toda tabla Markdown debe tener la línea de separación |---|---|."""
    rec = _build_full_rec("Misiones (Oberá)")
    md = generate_markdown_report(rec)
    assert "|--" in md or "| ---" in md

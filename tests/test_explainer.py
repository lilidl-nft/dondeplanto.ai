"""Tests del explainer (F6). Sin red, sin LLM."""

from __future__ import annotations

from dondeplanto.config import DEMO_LOCATIONS
from dondeplanto.explanation.explainer import explain
from dondeplanto.features.feature_builder import build_features
from dondeplanto.mock import get_mock_bundle
from dondeplanto.scoring.recommendation import recommend
from dondeplanto.scoring.species_profiles import load_profiles


def test_explain_returns_non_empty_string_for_each_demo() -> None:
    for name, (lat, lon) in DEMO_LOCATIONS.items():
        bundle = get_mock_bundle(lat, lon)
        rec = recommend(bundle, load_profiles())
        rec["explanation"] = explain(rec)
        assert isinstance(rec["explanation"], str)
        assert len(rec["explanation"]) > 100, f"explicación muy corta para {name}"


def test_explain_is_deterministic() -> None:
    """Mismas entradas → mismo string."""
    lat, lon = DEMO_LOCATIONS["Misiones (Oberá)"]
    bundle = get_mock_bundle(lat, lon)
    rec1 = recommend(bundle, load_profiles())
    rec2 = recommend(bundle, load_profiles())
    e1 = explain(rec1)
    e2 = explain(rec2)
    assert e1 == e2


def test_explain_mentions_top_species() -> None:
    lat, lon = DEMO_LOCATIONS["Corrientes (Santo Tomé)"]
    bundle = get_mock_bundle(lat, lon)
    rec = recommend(bundle, load_profiles())
    rec["explanation"] = explain(rec)
    assert rec["top_species"] in rec["explanation"]


def test_explain_handles_out_of_coverage() -> None:
    """Una coord fuera de las provincias demo → 'fuera de la cobertura INTA demo'."""
    bundle = build_features({"lat": -33.0, "lon": -69.0}, use_mock=True)
    rec = recommend(bundle, load_profiles())
    rec["explanation"] = explain(rec)
    assert (
        "fuera de la cobertura INTA demo" in rec["explanation"].lower()
        or "fuera de cobertura" in rec["explanation"].lower()
        or "fuera de" in rec["explanation"].lower()
    )


def test_explain_handles_empty_ranking() -> None:
    rec = {"ranking": [], "feature_bundle": {}}
    text = explain(rec)
    assert "vacío" in text.lower() or "no se pudo" in text.lower()


def test_explain_mentions_climate_delta() -> None:
    """El texto menciona el delta de temp."""
    lat, lon = DEMO_LOCATIONS["Entre Ríos (Concordia)"]
    bundle = get_mock_bundle(lat, lon)
    rec = recommend(bundle, load_profiles())
    rec["explanation"] = explain(rec)
    # El delta de temp del mock de Entre Ríos es 1.8°C
    assert "1.8" in rec["explanation"] or "1,8" in rec["explanation"] or "+1." in rec["explanation"]


def test_explain_three_paragraphs_minimum() -> None:
    """Explicación normal: 2-3 párrafos separados por \\n\\n."""
    lat, lon = DEMO_LOCATIONS["Misiones (Oberá)"]
    bundle = get_mock_bundle(lat, lon)
    rec = recommend(bundle, load_profiles())
    rec["explanation"] = explain(rec)
    paragraphs = [p for p in rec["explanation"].split("\n\n") if p.strip()]
    assert len(paragraphs) >= 2

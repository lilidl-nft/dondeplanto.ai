"""Tests del recommendation engine (spec 5.6)."""

from __future__ import annotations

import pytest

from dondeplanto.config import DEMO_LOCATIONS
from dondeplanto.mock import get_mock_bundle
from dondeplanto.scoring.recommendation import rank_species, recommend
from dondeplanto.scoring.species_profiles import load_profiles


def _profiles() -> dict:
    return load_profiles()


def test_recommend_returns_ranking_with_all_species() -> None:
    bundle = get_mock_bundle(*DEMO_LOCATIONS["Misiones (Oberá)"])
    rec = recommend(bundle, _profiles())
    assert "ranking" in rec
    assert "top_species" in rec
    assert "explanation" in rec
    assert "feature_bundle" in rec
    assert rec["explanation"] == ""  # F6 lo llena
    assert len(rec["ranking"]) == 3


def test_ranking_is_sorted_by_score_future_desc() -> None:
    bundle = get_mock_bundle(*DEMO_LOCATIONS["Corrientes (Santo Tomé)"])
    ranking = rank_species(bundle, _profiles())
    for i in range(len(ranking) - 1):
        assert ranking[i]["score_future"] >= ranking[i + 1]["score_future"]


def test_ranking_is_deterministic() -> None:
    """Mismas entradas → mismas salidas."""
    bundle = get_mock_bundle(*DEMO_LOCATIONS["Misiones (Oberá)"])
    r1 = rank_species(bundle, _profiles())
    r2 = rank_species(bundle, _profiles())
    for a, b in zip(r1, r2, strict=True):
        assert a == b


def test_species_score_contract_has_all_keys() -> None:
    bundle = get_mock_bundle(*DEMO_LOCATIONS["Misiones (Oberá)"])
    ranking = rank_species(bundle, _profiles())
    for s in ranking:
        for key in (
            "species",
            "site_aptitude_present",
            "site_aptitude_future",
            "species_fit_present",
            "species_fit_future",
            "score_present",
            "score_future",
            "delta_aptitud",
            "label",
        ):
            assert key in s, f"falta {key} en SpeciesScore"


def test_recommend_top_species_is_first_in_ranking() -> None:
    bundle = get_mock_bundle(*DEMO_LOCATIONS["Misiones (Oberá)"])
    rec = recommend(bundle, _profiles())
    assert rec["top_species"] == rec["ranking"][0]["species"]


def test_at_least_one_species_has_negative_delta() -> None:
    """Para algún demo, al menos una especie debe tener delta_aptitud negativo
    (es la señal clave del corrimiento climático que muestra la app)."""
    for _name, (lat, lon) in DEMO_LOCATIONS.items():
        bundle = get_mock_bundle(lat, lon)
        ranking = rank_species(bundle, _profiles())
        deltas = [s["delta_aptitud"] for s in ranking]
        if any(d < -0.05 for d in deltas):
            return  # ok, al menos una
    pytest.fail("Ningún demo produjo delta_aptitud marcadamente negativo")


def test_label_values_are_valid() -> None:
    """Las etiquetas son del conjunto cerrado definido por la regla 5.6."""
    bundle = get_mock_bundle(*DEMO_LOCATIONS["Misiones (Oberá)"])
    ranking = rank_species(bundle, _profiles())
    valid = {"Recomendada", "Viable", "Pierde aptitud a futuro", "No prioritaria"}
    for s in ranking:
        assert s["label"] in valid


def test_scores_in_unit_interval() -> None:
    bundle = get_mock_bundle(*DEMO_LOCATIONS["Misiones (Oberá)"])
    ranking = rank_species(bundle, _profiles())
    for s in ranking:
        for key in (
            "site_aptitude_present",
            "site_aptitude_future",
            "species_fit_present",
            "species_fit_future",
            "score_present",
            "score_future",
        ):
            assert 0.0 <= s[key] <= 1.0, f"{key} fuera de [0,1] en {s['species']}"


def test_recommend_empty_profiles_returns_empty_ranking() -> None:
    bundle = get_mock_bundle(*DEMO_LOCATIONS["Misiones (Oberá)"])
    rec = recommend(bundle, {})
    assert rec["ranking"] == []
    assert rec["top_species"] == ""

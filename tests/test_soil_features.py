"""Tests de las funciones puras de features.soil_features.

Cobertura:
- drainage_to_waterlogging_risk: tabla 5.4 + variantes con acentos + unknown
- forestry_aptitude_to_score: tabla 5.5 + unknown
- productivity_index_to_score: clamp 0..1 + None/NaN
- raw_to_soil_features: prioridad aptitude vs productivity, normalización,
  metadata (source, inta_coverage).
"""

from __future__ import annotations

import math

import pytest

from dondeplanto.features.soil_features import (
    drainage_to_waterlogging_risk,
    forestry_aptitude_to_score,
    productivity_index_to_score,
    raw_to_soil_features,
)


@pytest.mark.parametrize(
    ("drainage", "expected"),
    [
        ("excesivamente drenado", 0.10),
        ("bien drenado", 0.10),
        ("moderadamente bien drenado", 0.30),
        ("imperfectamente drenado", 0.60),
        ("pobremente drenado", 0.85),
        ("muy pobremente drenado", 1.00),
        ("anegadizo", 1.00),
        ("desconocido", 0.40),
    ],
)
def test_drainage_to_waterlogging_risk_table(drainage: str, expected: float) -> None:
    assert drainage_to_waterlogging_risk(drainage) == expected


def test_drainage_handles_accents_and_case() -> None:
    assert drainage_to_waterlogging_risk("Bien Drenado") == 0.10
    assert drainage_to_waterlogging_risk("IMPERFECTAMENTE DRENADO") == 0.60


def test_drainage_handles_slash_variant_from_spec() -> None:
    assert drainage_to_waterlogging_risk("muy pobremente drenado / anegadizo") == 1.00


def test_drainage_unknown_returns_default() -> None:
    assert drainage_to_waterlogging_risk("clase inventada") == 0.40
    assert drainage_to_waterlogging_risk(None) == 0.40


@pytest.mark.parametrize(
    ("apt", "expected"),
    [
        ("Alta", 0.85),
        ("Media", 0.60),
        ("Baja", 0.35),
        ("Marginal", 0.15),
        ("desconocida", 0.40),
    ],
)
def test_forestry_aptitude_to_score_table(apt: str, expected: float) -> None:
    assert forestry_aptitude_to_score(apt) == expected


def test_forestry_aptitude_unknown_returns_default() -> None:
    assert forestry_aptitude_to_score("inventada") == 0.40
    assert forestry_aptitude_to_score(None) == 0.40


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, 0.0),
        (50, 0.5),
        (100, 1.0),
        (75.5, 0.755),
    ],
)
def test_productivity_index_to_score_normal(index: float, expected: float) -> None:
    assert math.isclose(productivity_index_to_score(index), expected, rel_tol=1e-9)


def test_productivity_index_clamps() -> None:
    assert productivity_index_to_score(-10) == 0.0
    assert productivity_index_to_score(150) == 1.0


def test_productivity_index_none_and_nan() -> None:
    assert productivity_index_to_score(None) == 0.40
    assert productivity_index_to_score(float("nan")) == 0.40


def test_raw_to_soil_features_uses_aptitude_when_known() -> None:
    raw = {
        "soil_series": "S-001",
        "soil_capability_class": "IIIs",
        "soil_productivity_index": 60.0,
        "soil_drainage_class": "bien drenado",
        "soil_forestry_aptitude": "Alta",
    }
    f = raw_to_soil_features(raw, source="inta_local", inta_coverage=True)
    assert f["soil_aptitude_score"] == 0.85  # viene de Alta, no de productivity
    assert f["waterlogging_risk"] == 0.10
    assert f["inta_coverage"] is True
    assert f["source"] == "inta_local"
    assert f["soil_series"] == "S-001"


def test_raw_to_soil_features_uses_productivity_when_aptitude_unknown() -> None:
    raw = {
        "soil_series": "S-002",
        "soil_capability_class": "IIs",
        "soil_productivity_index": 80.0,
        "soil_drainage_class": "imperfectamente drenado",
        "soil_forestry_aptitude": "desconocida",
    }
    f = raw_to_soil_features(raw, source="inta_local", inta_coverage=True)
    assert f["soil_aptitude_score"] == 0.80  # viene del productivity
    assert f["waterlogging_risk"] == 0.60


def test_raw_to_soil_features_handles_missing_fields() -> None:
    f = raw_to_soil_features({}, source="mock", inta_coverage=False)
    assert f["soil_series"] is None
    assert f["soil_capability_class"] is None
    assert f["soil_productivity_index"] is None
    assert f["soil_drainage_class"] == "desconocido"
    assert f["soil_forestry_aptitude"] == "desconocida"
    assert f["soil_aptitude_score"] == 0.40  # unknown fallback
    assert f["waterlogging_risk"] == 0.40
    assert f["inta_coverage"] is False
    assert f["source"] == "mock"


def test_raw_to_soil_features_handles_accents() -> None:
    raw = {
        "soil_drainage_class": "MODERADAMENTE BIEN DRENADO",
        "soil_forestry_aptitude": "media",
    }
    f = raw_to_soil_features(raw)
    assert f["waterlogging_risk"] == 0.30
    assert f["soil_aptitude_score"] == 0.60

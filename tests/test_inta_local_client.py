"""Tests del cliente INTA local (point-in-polygon sobre GeoPackage).

Reglas del spec sección 7:
- punto dentro devuelve aptitud y drainage
- punto fuera marca inta_coverage=False
- sin red

Usa los GeoPackages mock commiteados en data/inta/.
"""

from __future__ import annotations

import pytest

from dondeplanto.clients.inta_local_client import get_soil_aptitude
from dondeplanto.config import DEMO_LOCATIONS, province_for_point


def test_get_soil_aptitude_inside_corrientes() -> None:
    """Punto demo de Corrientes: cae dentro del GeoPackage, cobertura=True."""
    lat, lon = DEMO_LOCATIONS["Corrientes (Santo Tomé)"]
    f = get_soil_aptitude(lat, lon)
    assert f["inta_coverage"] is True
    assert f["source"] == "inta_local"
    assert f["soil_drainage_class"] is not None
    assert 0.0 <= f["waterlogging_risk"] <= 1.0
    assert 0.0 <= f["soil_aptitude_score"] <= 1.0


def test_get_soil_aptitude_inside_entre_rios() -> None:
    lat, lon = DEMO_LOCATIONS["Entre Ríos (Concordia)"]
    f = get_soil_aptitude(lat, lon)
    assert f["inta_coverage"] is True
    assert f["source"] == "inta_local"


def test_get_soil_aptitude_inside_misiones() -> None:
    lat, lon = DEMO_LOCATIONS["Misiones (Oberá)"]
    f = get_soil_aptitude(lat, lon)
    assert f["inta_coverage"] is True
    assert f["source"] == "inta_local"


def test_get_soil_aptitude_outside_province_bboxes_marks_uncovered() -> None:
    """Mendoza cae fuera de toda provincia demo → cobertura=False, mock."""
    f = get_soil_aptitude(-33.0, -69.0)
    assert f["inta_coverage"] is False
    assert f["source"] == "mock"


def test_get_soil_aptitude_use_mock_returns_mock_source() -> None:
    """Con use_mock=True, devuelve mock sin tocar GeoPackage."""
    f = get_soil_aptitude(-28.55, -56.05, use_mock=True)
    assert f["source"] == "mock"


def test_get_soil_aptitude_does_not_make_http_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """El cliente no debe hacer HTTP: bloqueamos requests y verificamos que no falle."""

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("inta_local_client no debe hacer HTTP")

    monkeypatch.setattr("requests.get", _fail)
    monkeypatch.setattr("requests.post", _fail)
    # Re-llamamos para cada demo
    for lat, lon in DEMO_LOCATIONS.values():
        f = get_soil_aptitude(lat, lon)
        assert f["inta_coverage"] is True
    # Y un punto fuera de cobertura
    f = get_soil_aptitude(-33.0, -69.0)
    assert f["inta_coverage"] is False


def test_get_soil_aptitude_returns_full_soil_features_contract() -> None:
    """Verifica que el dict respeta el contrato SoilFeatures (sección 2.2 del spec)."""
    lat, lon = DEMO_LOCATIONS["Corrientes (Santo Tomé)"]
    f = get_soil_aptitude(lat, lon)
    for key in (
        "soil_series",
        "soil_capability_class",
        "soil_productivity_index",
        "soil_drainage_class",
        "soil_forestry_aptitude",
        "soil_aptitude_score",
        "waterlogging_risk",
        "inta_coverage",
        "source",
    ):
        assert key in f, f"falta clave {key} en SoilFeatures"


def test_province_for_point_demo_locations() -> None:
    """Sanity check: los 3 demos caen en provincias distintas y conocidas."""
    assert province_for_point(*DEMO_LOCATIONS["Corrientes (Santo Tomé)"]) == "corrientes"
    assert province_for_point(*DEMO_LOCATIONS["Entre Ríos (Concordia)"]) == "entre_rios"
    assert province_for_point(*DEMO_LOCATIONS["Misiones (Oberá)"]) == "misiones"

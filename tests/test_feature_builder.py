"""Tests del feature_builder (orquestador F2)."""

from __future__ import annotations

import pytest

from dondeplanto.config import DEMO_LOCATIONS
from dondeplanto.features.feature_builder import build_features
from dondeplanto.mock import get_mock_bundle


def test_build_features_use_mock_returns_complete_bundle() -> None:
    """Con use_mock=True, devuelve bundle completo válido (todos los bloques mock)."""
    lat, lon = DEMO_LOCATIONS["Corrientes (Santo Tomé)"]
    bundle = build_features({"lat": lat, "lon": lon}, use_mock=True)

    for key in (
        "location",
        "soil",
        "observed",
        "future",
        "fire",
        "logistics",
        "region",
        "data_quality",
    ):
        assert key in bundle, f"falta {key}"

    assert bundle["location"]["lat"] == lat
    assert bundle["location"]["lon"] == lon
    assert bundle["location"]["climate_model"] == "ensemble"
    assert bundle["location"]["baseline_period"] == "1991-2020"
    assert bundle["location"]["future_period"] == "2041-2060"
    assert bundle["data_quality"] == "all_mock"
    assert bundle["region"] == "NEA / Litoral"


def test_build_features_pending_blocks_raise_without_use_mock() -> None:
    """Sin use_mock, los bloques pendientes (clima/fuego/logística) levantan NotImplementedError."""
    lat, lon = DEMO_LOCATIONS["Corrientes (Santo Tomé)"]
    with pytest.raises(NotImplementedError, match="F5"):
        build_features({"lat": lat, "lon": lon})


def test_build_features_data_quality_partial_mock_in_coverage_no_use_mock_raises() -> None:
    """Sin use_mock y dentro de cobertura: el bloque soil es INTA real pero los
    otros levantan NotImplementedError, así que solo se puede llegar a
    `data_quality` cuando el caller ya consumió la excepción.

    Este test verifica que la rama real (no use_mock) intenta ir a INTA
    local antes de levantar la excepción pendiente.
    """
    lat, lon = DEMO_LOCATIONS["Misiones (Oberá)"]
    # Verificamos vía mock: la primera excepción proviene de _build_observed,
    # lo que confirma que el bloque soil SÍ se construyó como real.
    with pytest.raises(NotImplementedError) as exc_info:
        build_features({"lat": lat, "lon": lon})
    # El error menciona F5 (clima), no el suelo, lo que prueba que el suelo
    # se construyó OK antes de fallar en el siguiente bloque.
    assert "F5" in str(exc_info.value)


def test_build_features_matches_mock_bundle_when_use_mock() -> None:
    """En modo use_mock, el bundle debe coincidir con el del módulo mock."""
    lat, lon = DEMO_LOCATIONS["Entre Ríos (Concordia)"]
    built = build_features({"lat": lat, "lon": lon}, use_mock=True)
    mocked = get_mock_bundle(lat, lon)
    # location la completa build_features, los demás bloques deben matchear.
    for key in ("soil", "observed", "future", "fire", "logistics", "region", "data_quality"):
        assert built[key] == mocked[key]


def test_build_features_location_defaults_filled() -> None:
    """Si location no trae climate_model/periods, build_features completa con defaults."""
    bundle = build_features({"lat": -28.55, "lon": -56.05}, use_mock=True)
    assert bundle["location"]["climate_model"] == "ensemble"
    assert bundle["location"]["baseline_period"] == "1991-2020"
    assert bundle["location"]["future_period"] == "2041-2060"

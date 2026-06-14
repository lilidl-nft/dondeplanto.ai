"""Tests del feature_builder (orquestador F2)."""

from __future__ import annotations

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
    """En F5 todos los bloques están integrados, así que ya no hay NotImplementedError.

    Sin use_mock=True, los clientes reales intentan la red. Si fallan,
    caen a mock (sin levantar). Esta propiedad la verificamos con todos
    los requests bloqueados.
    """
    from dondeplanto.features import feature_builder as fb_mod

    def _fail(*_a: object, **_k: object) -> object:
        raise AssertionError("no debe llamar red en este test")

    # Hack: patcheamos requests.get y requests.post en cada cliente via
    # feature_builder para verificar que no se levante nada.
    import dondeplanto.clients.firms_client as fir_mod
    import dondeplanto.clients.open_meteo_climate_client as clim_mod
    import dondeplanto.clients.open_meteo_observed_client as obs_mod
    import dondeplanto.clients.overpass_client as ovr_mod

    saved = {
        "obs": obs_mod.requests.get,
        "clim": clim_mod.requests.get,
        "fir": fir_mod.requests.get,
        "ovr_post": ovr_mod.requests.post,
        "ovr_get": ovr_mod.requests.get,
    }
    obs_mod.requests.get = _fail  # type: ignore[assignment]
    clim_mod.requests.get = _fail  # type: ignore[assignment]
    fir_mod.requests.get = _fail  # type: ignore[assignment]
    ovr_mod.requests.post = _fail  # type: ignore[assignment]
    ovr_mod.requests.get = _fail  # type: ignore[assignment]
    try:
        lat, lon = DEMO_LOCATIONS["Corrientes (Santo Tomé)"]
        # No debe levantar; los clientes observados/clima/fuego/logística
        # degradan a mock. El bloque soil SÍ es real (INTA local).
        bundle = build_features({"lat": lat, "lon": lon})
        for key in ("observed", "future", "fire", "logistics"):
            assert key in bundle
            assert bundle[key]["source"] == "mock", (
                f"{key} no degradó a mock: {bundle[key].get('source')}"
            )
        # Soil debe ser INTA real (no tocado por los mocks de red)
        assert bundle["soil"]["source"] == "inta_local"
    finally:
        obs_mod.requests.get = saved["obs"]
        clim_mod.requests.get = saved["clim"]
        fir_mod.requests.get = saved["fir"]
        ovr_mod.requests.post = saved["ovr_post"]
        ovr_mod.requests.get = saved["ovr_get"]
    # Marca el import usado para que ruff no se queje
    _ = fb_mod


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

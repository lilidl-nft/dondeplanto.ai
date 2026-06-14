"""Tests del cliente Open-Meteo Climate (F4) con HTTP mockeado.

Reglas:
- Sin red (monkeypatch sobre requests.get).
- use_mock=True nunca toca red.
- Cache evita segunda llamada.
- Fallo de red → mock con source='mock'.
- Ensemble: promedia 4 modelos y calcula ensemble_spread.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from dondeplanto.clients import open_meteo_climate_client as client_mod
from dondeplanto.clients.open_meteo_climate_client import (
    cache_info,
    clear_cache,
    get_climate_delta,
    get_climate_period,
)
from dondeplanto.config import CLIMATE_MODELS, DEMO_LOCATIONS


def _ok_response(tmax_mean: float = 25.0, precip_sum: float = 1300.0) -> dict[str, Any]:
    return {
        "latitude": -28.5,
        "longitude": -56.0,
        "daily": {
            "time": [f"1991-01-{i + 1:02d}" for i in range(30)],
            "temperature_2m_max": [tmax_mean] * 30,
            "temperature_2m_min": [tmax_mean - 5.0] * 30,
            "precipitation_sum": [precip_sum / 30.0] * 30,
        },
    }


def _mock_get_ok(monkeypatch: pytest.MonkeyPatch, response_payload: dict[str, Any]) -> MagicMock:
    """Mockea requests.get para devolver la respuesta dada."""
    mock_response = MagicMock()
    mock_response.json.return_value = response_payload
    mock_response.raise_for_status = MagicMock()
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    return mock_get


def test_get_climate_period_uses_http(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    mock_get = _mock_get_ok(monkeypatch, _ok_response())
    resp = get_climate_period(-28.55, -56.05, "1991-01-01", "1991-12-31", "CMCC_CM2_VHR4")
    assert "daily" in resp
    assert mock_get.call_count == 1
    # Verifica que se pasaron los params correctos
    kwargs = mock_get.call_args.kwargs
    assert "params" in kwargs
    assert kwargs["params"]["latitude"] == "-28.55"
    assert kwargs["params"]["longitude"] == "-56.05"
    assert kwargs["params"]["models"] == "CMCC_CM2_VHR4"
    assert "timeout" in kwargs


def test_get_climate_period_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    mock_get = _mock_get_ok(monkeypatch, _ok_response())
    get_climate_period(-28.55, -56.05, "1991-01-01", "1991-12-31", "CMCC_CM2_VHR4")
    get_climate_period(-28.55, -56.05, "1991-01-01", "1991-12-31", "CMCC_CM2_VHR4")
    assert mock_get.call_count == 1
    assert cache_info().hits >= 1


def test_get_climate_period_use_mock_skips_http(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    mock_get = MagicMock()
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    resp = get_climate_period(
        -28.55, -56.05, "1991-01-01", "1991-12-31", "CMCC_CM2_VHR4", use_mock=True
    )
    assert resp.get("_source") == "mock"
    assert mock_get.call_count == 0


def test_get_climate_period_falls_back_to_mock_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_cache()
    mock_get = MagicMock(side_effect=ConnectionError("network down"))
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    resp = get_climate_period(-28.55, -56.05, "1991-01-01", "1991-12-31", "CMCC_CM2_VHR4")
    assert resp.get("_source") == "mock"


def test_get_climate_period_falls_back_to_mock_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    clear_cache()
    mock_get = MagicMock(side_effect=requests.Timeout("timeout"))
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    resp = get_climate_period(-28.55, -56.05, "1991-01-01", "1991-12-31", "CMCC_CM2_VHR4")
    assert resp.get("_source") == "mock"


def test_get_climate_delta_single_model(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    baseline = _ok_response(tmax_mean=25.0, precip_sum=1300.0)
    future = _ok_response(tmax_mean=27.0, precip_sum=1200.0)

    def _fake_get(url: str, params: dict[str, Any] | None = None, timeout: Any = None) -> MagicMock:
        # Devuelve baseline o future según el start_date
        start = (params or {}).get("start_date", "")
        mock_response = MagicMock()
        if start.startswith("1991"):
            mock_response.json.return_value = baseline
        else:
            mock_response.json.return_value = future
        mock_response.raise_for_status = MagicMock()
        return mock_response

    monkeypatch.setattr(client_mod.requests, "get", MagicMock(side_effect=_fake_get))

    fc = get_climate_delta(-28.55, -56.05, model="CMCC_CM2_VHR4")
    assert fc["temp_max_delta"] == pytest.approx(2.0)
    assert fc["source"] == "open_meteo_climate"
    assert fc["ensemble_spread"] is None  # un solo modelo
    # precip_delta_pct = (1200 - 1300) / 1300 * 100 ≈ -7.69
    assert fc["precip_delta_pct"] == pytest.approx(-7.692, rel=0.01)


def test_get_climate_delta_ensemble_averages_and_spread(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    # 4 modelos con deltas: 1, 2, 3, 4 °C. Cada modelo pide baseline+future
    # en orden, así que el índice de modelo es (call_count - 1) // 2.
    call_count = {"n": 0}
    deltas_per_model = [1.0, 2.0, 3.0, 4.0]

    def _fake_get(url: str, params: dict[str, Any] | None = None, timeout: Any = None) -> MagicMock:
        call_count["n"] += 1
        start = (params or {}).get("start_date", "")
        model_idx = (call_count["n"] - 1) // 2
        if start.startswith("1991"):
            tmax = 25.0
            precip = 1300.0
        else:
            tmax = 25.0 + deltas_per_model[model_idx]
            precip = 1200.0
        mock_response = MagicMock()
        mock_response.json.return_value = _ok_response(tmax_mean=tmax, precip_sum=precip)
        mock_response.raise_for_status = MagicMock()
        return mock_response

    monkeypatch.setattr(client_mod.requests, "get", MagicMock(side_effect=_fake_get))

    fc = get_climate_delta(-28.55, -56.05, model="ensemble")
    # promedio de deltas = (1+2+3+4)/4 = 2.5
    assert fc["temp_max_delta"] == pytest.approx(2.5)
    assert fc["source"] == "open_meteo_climate"
    # stdev poblacional de [1,2,3,4] = sqrt(1.25) ≈ 1.118
    assert fc["ensemble_spread"] == pytest.approx(1.118, rel=0.01)


def test_get_climate_delta_use_mock_returns_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    mock_get = MagicMock()
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    lat, lon = DEMO_LOCATIONS["Misiones (Oberá)"]
    fc = get_climate_delta(lat, lon, use_mock=True)
    assert fc["source"] == "mock"
    assert mock_get.call_count == 0


def test_get_climate_delta_falls_back_to_mock_on_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si un modelo falla, todo el ensemble cae a mock."""
    clear_cache()
    fail_count = {"n": 0}

    def _fake_get(url: str, params: dict[str, Any] | None = None, timeout: Any = None) -> MagicMock:
        fail_count["n"] += 1
        if fail_count["n"] == 3:  # 3er request falla
            raise ConnectionError("red caída")
        mock_response = MagicMock()
        mock_response.json.return_value = _ok_response(tmax_mean=25.0, precip_sum=1300.0)
        mock_response.raise_for_status = MagicMock()
        return mock_response

    monkeypatch.setattr(client_mod.requests, "get", MagicMock(side_effect=_fake_get))

    lat, lon = DEMO_LOCATIONS["Corrientes (Santo Tomé)"]
    fc = get_climate_delta(lat, lon, model="ensemble")
    assert fc["source"] == "mock"


def test_does_not_use_network_when_all_clients_avoid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sanity check: con todos los mocks bloqueados, use_mock=True no falla."""

    def _fail(*_a: object, **_k: object) -> Any:
        raise AssertionError("no debe tocar red con use_mock=True")

    monkeypatch.setattr(client_mod.requests, "get", _fail)
    monkeypatch.setattr(client_mod.requests, "post", _fail)
    for _name, (lat, lon) in DEMO_LOCATIONS.items():
        get_climate_period(lat, lon, "1991-01-01", "1991-12-31", "ensemble", use_mock=True)
        get_climate_delta(lat, lon, use_mock=True)


def test_config_has_climate_models_for_ensemble() -> None:
    """Sanity: el ensemble usa exactamente los modelos de config."""
    assert len(CLIMATE_MODELS) >= 2

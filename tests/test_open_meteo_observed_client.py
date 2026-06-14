"""Tests del cliente Open-Meteo Archive (F5) con HTTP mockeado.

Reglas:
- Sin red (monkeypatch).
- Cache por (lat, lon, período).
- Fallback mock ante error de red.
- use_mock=True nunca toca red.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dondeplanto.clients import open_meteo_observed_client as client_mod
from dondeplanto.clients.open_meteo_observed_client import (
    cache_info,
    clear_cache,
    get_observed_climate,
)


def _ok_payload(
    tmax_mean: float = 25.0, precip_total: float = 1200.0, et_total: float = 900.0
) -> dict:
    n = 365
    return {
        "daily": {
            "time": [f"2024-01-{i + 1:02d}" for i in range(n)],
            "temperature_2m_max": [tmax_mean] * n,
            "temperature_2m_min": [tmax_mean - 5.0] * n,
            "precipitation_sum": [precip_total / n] * n,
            "et0_fao_evapotranspiration": [et_total / n] * n,
        }
    }


def test_use_mock_true_skips_http(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    mock_get = MagicMock()
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    f = get_observed_climate(-28.55, -56.05, use_mock=True)
    assert f["source"] == "mock"
    assert mock_get.call_count == 0


def test_http_error_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    mock_get = MagicMock(side_effect=ConnectionError("red caída"))
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    f = get_observed_climate(-28.55, -56.05)
    assert f["source"] == "mock"


def test_successful_response_summarizes(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(
        return_value=_ok_payload(tmax_mean=27.5, precip_total=1500.0, et_total=1000.0)
    )
    mock_get = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    f = get_observed_climate(-28.55, -56.05, today_iso="2026-06-14")
    assert f["source"] == "open_meteo_archive"
    assert f["obs_temp_max_mean"] == pytest.approx(27.5)
    assert f["obs_temp_min_mean"] == pytest.approx(22.5)
    assert f["obs_precip_sum_annual"] == pytest.approx(1500.0, rel=0.01)
    assert f["obs_evapotranspiration_annual"] == pytest.approx(1000.0, rel=0.01)


def test_summarizes_handles_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Faltan algunos campos en la respuesta: el summary devuelve None para ellos."""
    clear_cache()
    payload = {
        "daily": {
            "time": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "temperature_2m_max": [25.0, 26.0, 27.0],
            # tmin, precip, et faltantes
        }
    }
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    mock_get = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    f = get_observed_climate(-28.55, -56.05, today_iso="2026-06-14")
    assert f["obs_temp_max_mean"] == pytest.approx(26.0)
    assert f["obs_temp_min_mean"] is None
    assert f["obs_precip_sum_annual"] is None
    assert f["obs_evapotranspiration_annual"] is None


def test_cache_avoids_second_http_call(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_cache()
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=_ok_payload())
    mock_get = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    get_observed_climate(-28.55, -56.05, today_iso="2026-06-14")
    get_observed_climate(-28.55, -56.05, today_iso="2026-06-14")
    assert mock_get.call_count == 1
    assert cache_info().hits >= 1

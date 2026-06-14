"""Tests del cliente FIRMS (F5) con HTTP mockeado.

Reglas:
- Sin red (monkeypatch sobre requests.get o en requests.get del módulo).
- Sin FIRMS_MAP_KEY → mock.
- Red caída → mock.
- use_mock=True nunca toca red.
- CSV parseado correctamente.
"""

from __future__ import annotations

import datetime as _dt
from unittest.mock import MagicMock

import pytest

from dondeplanto.clients import firms_client as client_mod
from dondeplanto.clients.firms_client import get_fire_activity


def _setup_env(monkeypatch: pytest.MonkeyPatch, key: str | None) -> None:
    if key is None:
        monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    else:
        monkeypatch.setenv("FIRMS_MAP_KEY", key)


def test_use_mock_true_skips_env_and_http(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_env(monkeypatch, key="somekey")
    mock_get = MagicMock()
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    f = get_fire_activity(-28.55, -56.05, use_mock=True)
    assert f["source"] == "mock"
    assert mock_get.call_count == 0


def test_no_key_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_env(monkeypatch, key=None)
    mock_get = MagicMock()
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    f = get_fire_activity(-28.55, -56.05)
    assert f["source"] == "mock"
    assert mock_get.call_count == 0


def test_http_error_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_env(monkeypatch, key="somekey")
    mock_get = MagicMock(side_effect=ConnectionError("red caída"))
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    f = get_fire_activity(-28.55, -56.05)
    assert f["source"] == "mock"


def test_http_status_error_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_env(monkeypatch, key="somekey")
    resp = MagicMock()
    resp.raise_for_status = MagicMock(side_effect=Exception("500"))
    mock_get = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    f = get_fire_activity(-28.55, -56.05)
    assert f["source"] == "mock"


def test_successful_response_parses_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_env(monkeypatch, key="somekey")
    today = _dt.date(2026, 6, 14)
    recent_date = (today - _dt.timedelta(days=10)).isoformat()
    old_date = (today - _dt.timedelta(days=200)).isoformat()
    csv_text = (
        "latitude,longitude,acq_date\n"
        f"-28.55,-56.05,{recent_date}\n"
        f"-28.60,-56.10,{old_date}\n"
        "99.0,99.0,2026-05-22\n"  # fuera del radio
    )
    resp = MagicMock()
    resp.text = csv_text
    resp.raise_for_status = MagicMock()
    mock_get = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    f = get_fire_activity(-28.55, -56.05, radius_km=25.0)
    assert f["source"] == "firms"
    # 1 reciente + 1 viejo dentro del radio
    assert f["fire_count_30d"] == 1
    assert f["fire_count_365d"] == 2
    # El de (99,99) está fuera del radio
    assert f["fire_count_365d"] != 3


def test_uses_env_key_in_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_env(monkeypatch, key="mysecret")
    resp = MagicMock()
    resp.text = "latitude,longitude,acq_date\n"
    resp.raise_for_status = MagicMock()
    mock_get = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    get_fire_activity(-28.55, -56.05, radius_km=25.0)
    called_url = mock_get.call_args.args[0]
    assert "mysecret" in called_url

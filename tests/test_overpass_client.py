"""Tests del cliente Overpass (F5) con HTTP mockeado.

Reglas:
- Mock fallback es OBLIGATORIO (Overpass se cae seguido).
- POST a config.OVERPASS con query Overpass-QL.
- Contadores: road_count, primary_road_count, waterway_count.
- Scores: accessibility, water_access.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from dondeplanto.clients import overpass_client as client_mod
from dondeplanto.clients.overpass_client import get_logistics


def _ok_payload(roads: int, primaries: int, waterways: int) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []
    for i in range(roads):
        elements.append(
            {
                "type": "way",
                "tags": {"highway": "primary" if i < primaries else "residential"},
            },
        )
    for _ in range(waterways):
        elements.append({"type": "way", "tags": {"waterway": "river"}})
    return {"elements": elements}


def test_use_mock_true_skips_http(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_get = MagicMock()
    mock_post = MagicMock()
    monkeypatch.setattr(client_mod.requests, "get", mock_get)
    monkeypatch.setattr(client_mod.requests, "post", mock_post)
    f = get_logistics(-28.55, -56.05, use_mock=True)
    assert f["source"] == "mock"
    assert mock_get.call_count == 0
    assert mock_post.call_count == 0


def test_http_error_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_post = MagicMock(side_effect=ConnectionError("overpass caído"))
    monkeypatch.setattr(client_mod.requests, "post", mock_post)
    f = get_logistics(-28.55, -56.05)
    assert f["source"] == "mock"


def test_http_500_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    resp = MagicMock()
    resp.raise_for_status = MagicMock(side_effect=Exception("500"))
    mock_post = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "post", mock_post)
    f = get_logistics(-28.55, -56.05)
    assert f["source"] == "mock"


def test_invalid_json_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(side_effect=ValueError("invalid json"))
    mock_post = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "post", mock_post)
    f = get_logistics(-28.55, -56.05)
    assert f["source"] == "mock"


def test_successful_response_counts_features(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _ok_payload(roads=10, primaries=2, waterways=3)
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    mock_post = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "post", mock_post)
    f = get_logistics(-28.55, -56.05, radius_m=5000)
    assert f["source"] == "overpass"
    assert f["road_count_5km"] == 10
    assert f["primary_road_count_10km"] == 2
    assert f["waterway_count_5km"] == 3
    # accessibility = (10*0.6 + 2*0.4) / 30 = 6.8/30 ≈ 0.227
    assert f["accessibility_score"] == pytest.approx((10 * 0.6 + 2 * 0.4) / 30.0)
    # water_access = 3/10 = 0.3
    assert f["water_access_score"] == pytest.approx(0.3)


def test_posts_query_with_correct_around(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _ok_payload(roads=0, primaries=0, waterways=0)
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    mock_post = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "post", mock_post)
    get_logistics(-28.55, -56.05, radius_m=3000)
    data = mock_post.call_args.kwargs.get("data", {})
    assert "data" in data
    assert "around:3000" in data["data"]


def test_scores_clamped_to_unit_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _ok_payload(roads=200, primaries=50, waterways=20)
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    mock_post = MagicMock(return_value=resp)
    monkeypatch.setattr(client_mod.requests, "post", mock_post)
    f = get_logistics(-28.55, -56.05)
    assert 0.0 <= f["accessibility_score"] <= 1.0
    assert 0.0 <= f["water_access_score"] <= 1.0

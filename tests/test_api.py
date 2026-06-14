"""Tests de la API FastAPI (F6). Usamos TestClient de FastAPI (sin servidor)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from dondeplanto.api.app import app

client = TestClient(app)


def test_health_endpoint() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_post_report_use_mock_returns_valid_response() -> None:
    """Con use_mock=True y coord en demo Misiones, devuelve un JSON válido."""
    resp = client.post(
        "/api/report",
        json={"lat": -27.49, "lon": -55.12, "use_mock": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in ("location", "region", "data_quality", "top_species", "ranking", "explanation"):
        assert key in data
    assert data["region"] == "NEA / Litoral"
    assert len(data["ranking"]) == 3
    # format=json (default) → markdown_report ausente
    assert data["markdown_report"] is None


def test_post_report_format_markdown_includes_report() -> None:
    resp = client.post(
        "/api/report",
        json={"lat": -27.49, "lon": -55.12, "use_mock": True, "format": "markdown"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["markdown_report"] is not None
    assert "# dondeplanto.ai — Reporte de aptitud forestal" in data["markdown_report"]


def test_post_report_validation_errors() -> None:
    """Lat fuera de rango → 422 (validación de pydantic)."""
    resp = client.post("/api/report", json={"lat": 200.0, "lon": 0.0, "use_mock": True})
    assert resp.status_code == 422


def test_post_report_invalid_format_rejected() -> None:
    resp = client.post(
        "/api/report",
        json={"lat": -27.49, "lon": -55.12, "use_mock": True, "format": "pdf"},
    )
    assert resp.status_code == 422


def test_post_report_top_species_is_first_in_ranking() -> None:
    resp = client.post(
        "/api/report",
        json={"lat": -28.55, "lon": -56.05, "use_mock": True},
    )
    data = resp.json()
    assert data["top_species"] == data["ranking"][0]["species"]


def test_post_report_explanation_is_non_empty() -> None:
    resp = client.post(
        "/api/report",
        json={"lat": -27.49, "lon": -55.12, "use_mock": True},
    )
    data = resp.json()
    assert len(data["explanation"]) > 50


def test_post_report_out_of_coverage_returns_200_with_mock_data() -> None:
    """Coord fuera de cobertura: bundle es all_mock, recomendación OK."""
    resp = client.post(
        "/api/report",
        json={"lat": -33.0, "lon": -69.0, "use_mock": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_quality"] == "all_mock"
    assert data["region"] == "Desconocida"

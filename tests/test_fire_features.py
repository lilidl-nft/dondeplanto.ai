"""Tests de las funciones puras de features.fire_features (F5)."""

from __future__ import annotations

import pytest

from dondeplanto.features.fire_features import fires_to_features, haversine_km


def test_haversine_known_distances() -> None:
    """Distancias conocidas: ~0 km entre el mismo punto, ~111 km por grado de latitud."""
    assert haversine_km(0.0, 0.0, 0.0, 0.0) == pytest.approx(0.0, abs=1e-6)
    # 1 grado de latitud ≈ 111 km
    assert haversine_km(0.0, 0.0, 1.0, 0.0) == pytest.approx(111.0, abs=1.0)
    # 1 grado de longitud en el ecuador ≈ 111 km
    assert haversine_km(0.0, 0.0, 0.0, 1.0) == pytest.approx(111.0, abs=1.0)
    # Corrientes → Misiones: ~150 km (la latitud cambia 1°, la longitud ~1°)
    d = haversine_km(-28.55, -56.05, -27.49, -55.12)
    assert 140 < d < 160


def test_fires_to_features_empty_list() -> None:
    f = fires_to_features([], 0.0, 0.0, 25.0, source="firms")
    assert f["fire_count_30d"] == 0
    assert f["fire_count_365d"] == 0
    assert f["distance_to_nearest_fire_km"] is None
    assert f["fire_activity_score"] == 0.0
    assert f["source"] == "firms"


def test_fires_to_features_counts_recent_and_old() -> None:
    """Focos de hace 10 días cuentan en 30d y 365d; de hace 100 días solo en 365d."""
    import datetime as _dt

    now = _dt.datetime(2026, 6, 1, tzinfo=_dt.UTC)
    now_ts = now.timestamp()
    fire_recent = {
        "lat": -28.55,
        "lon": -56.05,
        "acq_date": "2026-05-22",  # ~10 días
    }
    fire_old = {
        "lat": -28.60,
        "lon": -56.10,
        "acq_date": "2025-09-01",  # ~270 días
    }
    fire_too_old = {
        "lat": -28.55,
        "lon": -56.05,
        "acq_date": "2024-01-01",  # > 365 días
    }
    f = fires_to_features(
        [fire_recent, fire_old, fire_too_old],
        -28.55,
        -56.05,
        radius_km=25.0,
        now_ts=now_ts,
    )
    assert f["fire_count_30d"] == 1
    assert f["fire_count_365d"] == 2
    assert f["distance_to_nearest_fire_km"] is not None
    assert f["distance_to_nearest_fire_km"] < 5.0  # fire_recent está casi encima


def test_fires_to_features_filters_outside_radius() -> None:
    fire_far = {"lat": 10.0, "lon": 10.0, "acq_date": "2026-05-22"}
    f = fires_to_features([fire_far], 0.0, 0.0, radius_km=25.0, now_ts=None)
    assert f["fire_count_30d"] == 0
    assert f["fire_count_365d"] == 0
    assert f["distance_to_nearest_fire_km"] is None


def test_fires_to_features_ignores_malformed() -> None:
    items = [
        {"lat": None, "lon": -56.0, "acq_date": "2026-05-22"},
        {"lat": -28.5, "lon": None, "acq_date": "2026-05-22"},
        {"lat": -28.5, "lon": -56.0, "acq_date": None},
        {"lat": -28.5, "lon": -56.0},  # falta acq_date
        {},
    ]
    f = fires_to_features(items, -28.55, -56.05, radius_km=25.0, now_ts=None)
    # Todos son inválidos → contadores en 0
    assert f["fire_count_30d"] == 0
    assert f["fire_count_365d"] == 0


def test_fires_to_features_score_clamped() -> None:
    """Muchos focos → score = 1.0 (clamp)."""
    many = [{"lat": -28.55, "lon": -56.05, "acq_date": "2026-05-22"} for _ in range(100)]
    f = fires_to_features(many, -28.55, -56.05, radius_km=25.0, now_ts=None)
    assert f["fire_activity_score"] == pytest.approx(1.0)


def test_fires_to_features_propagates_source() -> None:
    f = fires_to_features([], 0.0, 0.0, 25.0, source="mock")
    assert f["source"] == "mock"

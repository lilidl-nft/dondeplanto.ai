"""Tests de las funciones puras de features.climate_features (F4).

Cobertura:
- _safe_mean, _safe_sum: bordes (None, NaN, vacío)
- _extract_daily: alineación de arrays, campos faltantes
- annual_means_from_response: caso normal, caso campos faltantes
- compute_delta: temp_max_delta, precip_delta_pct, casos con None
- compute_water_stress_future: con/sin ET, clamp
- build_future_climate: shape del FutureClimate
"""

from __future__ import annotations

import math

import pytest

from dondeplanto.features.climate_features import (
    annual_means_from_response,
    build_future_climate,
    build_future_climate_from_deltas,
    compute_delta,
    compute_water_stress_future,
)


def _daily_response(
    tmax: list[float | None],
    tmin: list[float] | None = None,
    precip: list[float] | None = None,
) -> dict:
    n = len(tmax)
    return {
        "daily": {
            "time": [f"1991-01-{i + 1:02d}" for i in range(n)],
            "temperature_2m_max": tmax,
            "temperature_2m_min": tmin
            if tmin is not None
            else [(v - 5) if v is not None else None for v in tmax],
            "precipitation_sum": precip if precip is not None else [0.0] * n,
        }
    }


def test_annual_means_normal_case() -> None:
    resp = _daily_response([20.0, 30.0], tmin=[10.0, 20.0], precip=[0.0, 10.0])
    means = annual_means_from_response(resp)
    assert means["temp_max_mean"] == pytest.approx(25.0)
    assert means["temp_min_mean"] == pytest.approx(15.0)
    assert means["precip_sum"] == pytest.approx(10.0)


def test_annual_means_handles_none_values() -> None:
    resp = _daily_response([20.0, None, 30.0], tmin=[10.0, 15.0, 20.0])
    means = annual_means_from_response(resp)
    assert means["temp_max_mean"] == pytest.approx(25.0)  # ignora None
    assert means["temp_min_mean"] == pytest.approx(15.0)


def test_annual_means_handles_nan() -> None:
    resp = _daily_response([20.0, float("nan"), 30.0])
    means = annual_means_from_response(resp)
    assert means["temp_max_mean"] == pytest.approx(25.0)


def test_annual_means_all_none_returns_none() -> None:
    resp = _daily_response([None, None, None])
    means = annual_means_from_response(resp)
    assert means["temp_max_mean"] is None


def test_annual_means_missing_daily_returns_none() -> None:
    means = annual_means_from_response({})
    assert means["temp_max_mean"] is None
    assert means["temp_min_mean"] is None
    assert means["precip_sum"] is None


def test_compute_delta_temp_and_precip() -> None:
    baseline = _daily_response([25.0] * 30, precip=[0.0] * 30)
    future = _daily_response([27.0] * 30, precip=[0.0] * 29 + [100.0])
    d = compute_delta(baseline, future)
    assert d["baseline_temp_max_mean"] == pytest.approx(25.0)
    assert d["future_temp_max_mean"] == pytest.approx(27.0)
    assert d["temp_max_delta"] == pytest.approx(2.0)
    # precip delta: future 100, baseline 0 → inf% (protegemos por None)
    # mejor caso con precip no-cero
    baseline2 = _daily_response([25.0] * 30, precip=[50.0] * 30)
    future2 = _daily_response([27.0] * 30, precip=[40.0] * 30)
    d2 = compute_delta(baseline2, future2)
    assert d2["baseline_precip_sum"] == pytest.approx(1500.0)
    assert d2["future_precip_sum"] == pytest.approx(1200.0)
    assert d2["precip_delta_pct"] == pytest.approx(-20.0)


def test_compute_delta_handles_missing_data() -> None:
    """Si algún campo falta, los deltas son None en vez de crashear."""
    empty = _daily_response([], precip=[])
    full = _daily_response([25.0] * 30, precip=[0.0] * 30)
    d = compute_delta(empty, full)
    assert d["temp_max_delta"] is None
    assert d["precip_delta_pct"] is None


def test_compute_delta_zero_baseline_precip() -> None:
    """Baseline precip=0 no rompe el cálculo (precip_delta_pct=None)."""
    baseline = _daily_response([25.0] * 30, precip=[0.0] * 30)
    future = _daily_response([27.0] * 30, precip=[10.0] * 30)
    d = compute_delta(baseline, future)
    assert d["precip_delta_pct"] is None


def test_compute_water_stress_future_no_et() -> None:
    # temp=3 → 1.0; precip=-30 → 1.0; sin ET → 1.0*0.57 + 1.0*0.43 = 1.0
    assert compute_water_stress_future(3.0, -30.0) == pytest.approx(1.0)


def test_compute_water_stress_future_with_et() -> None:
    # temp=1.5 → 0.5; precip=-15 → 0.5; et=0.5
    # 0.5*0.5 + 0.5*0.35 + 0.5*0.15 = 0.25 + 0.175 + 0.075 = 0.5
    assert compute_water_stress_future(1.5, -15.0, evapotranspiration_norm=0.5) == pytest.approx(
        0.5
    )


def test_compute_water_stress_future_clamped_to_unit_interval() -> None:
    # temp muy alto y precip muy negativa
    v = compute_water_stress_future(100.0, -100.0)
    assert 0.0 <= v <= 1.0


def test_compute_water_stress_future_handles_none() -> None:
    """None se trata como 0 (degradación controlada)."""
    v = compute_water_stress_future(None, None)
    assert v == pytest.approx(0.0)


def test_build_future_climate_from_deltas_full_shape() -> None:
    delta = {
        "baseline_temp_max_mean": 25.0,
        "future_temp_max_mean": 27.0,
        "temp_max_delta": 2.0,
        "baseline_precip_sum": 1300.0,
        "future_precip_sum": 1200.0,
        "precip_delta_pct": -7.69,
    }
    fc = build_future_climate_from_deltas(delta, source="open_meteo_climate", ensemble_spread=0.4)
    for key in (
        "baseline_temp_max_mean",
        "future_temp_max_mean",
        "temp_max_delta",
        "baseline_precip_sum",
        "future_precip_sum",
        "precip_delta_pct",
        "water_stress_future",
        "ensemble_spread",
        "source",
    ):
        assert key in fc
    assert fc["source"] == "open_meteo_climate"
    assert fc["ensemble_spread"] == 0.4
    assert fc["temp_max_delta"] == 2.0


def test_build_future_climate_end_to_end() -> None:
    baseline = _daily_response([25.0] * 30, precip=[40.0] * 30)
    future = _daily_response([27.0] * 30, precip=[40.0] * 30)
    fc = build_future_climate(baseline, future, source="open_meteo_climate")
    assert fc["temp_max_delta"] == pytest.approx(2.0)
    assert fc["source"] == "open_meteo_climate"
    assert 0.0 <= fc["water_stress_future"] <= 1.0
    assert math.isfinite(fc["water_stress_future"])

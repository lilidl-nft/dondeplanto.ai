"""Tests de la Capa A del scoring: aptitud del sitio (spec 5.1, 5.3, 5.4)."""

from __future__ import annotations

import pytest

from dondeplanto.scoring.site_scoring import (
    environmental_risk,
    site_aptitude,
    water_stress_future,
    water_stress_present,
)


def _bundle(
    *,
    soil_score: float = 0.7,
    waterlog: float = 0.3,
    fire: float = 0.3,
    access: float = 0.6,
    precip: float = 1200.0,
    et: float | None = 900.0,
    precip_delta: float = -5.0,
    temp_delta: float = 1.5,
    et_norm: float | None = None,
) -> dict:
    return {
        "soil": {"soil_aptitude_score": soil_score, "waterlogging_risk": waterlog},
        "fire": {"fire_activity_score": fire},
        "logistics": {"accessibility_score": access},
        "observed": {
            "obs_precip_sum_annual": precip,
            "obs_evapotranspiration_annual": et,
        },
        "future": {
            "temp_max_delta": temp_delta,
            "precip_delta_pct": precip_delta,
            "evapotranspiration_norm": et_norm,
        },
    }


def test_water_stress_future_uses_precomputed_if_present() -> None:
    b = _bundle()
    b["future"]["water_stress_future"] = 0.42
    assert water_stress_future(b["future"]) == pytest.approx(0.42)


def test_water_stress_future_without_et_uses_57_43_weights() -> None:
    # temp_delta=3 → norm=1.0; precip_delta=-30 → norm=1.0; sin et.
    # 1.0*0.57 + 1.0*0.43 = 1.0 (clamp).
    fut = {"temp_max_delta": 3.0, "precip_delta_pct": -30.0, "evapotranspiration_norm": None}
    assert water_stress_future(fut) == pytest.approx(1.0)


def test_water_stress_future_with_et_uses_50_35_15_weights() -> None:
    # temp=3.0/3.0=1.0, precip=-15/30=0.5, et=0.5
    # 1.0*0.50 + 0.5*0.35 + 0.5*0.15 = 0.5 + 0.175 + 0.075 = 0.75
    fut = {"temp_max_delta": 3.0, "precip_delta_pct": -15.0, "evapotranspiration_norm": 0.5}
    assert water_stress_future(fut) == pytest.approx(0.75)


def test_water_stress_future_in_unit_interval() -> None:
    """Aunque los inputs sean extremos, el resultado está en [0,1]."""
    fut = {"temp_max_delta": 100.0, "precip_delta_pct": -100.0, "evapotranspiration_norm": 1.0}
    v = water_stress_future(fut)
    assert 0.0 <= v <= 1.0


def test_water_stress_present_uses_precip_normalized() -> None:
    # precip=1000 (óptimo), et=0 → dryness = (1-1)*(0.5+0) = 0
    obs = {"obs_precip_sum_annual": 1000.0, "obs_evapotranspiration_annual": 0.0}
    assert water_stress_present(obs) == pytest.approx(0.0, abs=1e-9)


def test_water_stress_present_high_when_precip_low() -> None:
    # precip=200, et=0 → precip_norm=0.2; dryness = 0.8 * 0.5 = 0.4
    obs = {"obs_precip_sum_annual": 200.0, "obs_evapotranspiration_annual": 0.0}
    assert water_stress_present(obs) == pytest.approx(0.4)


def test_water_stress_present_none_returns_placeholder() -> None:
    assert water_stress_present({"obs_precip_sum_annual": None}) == 0.30


def test_environmental_risk_present_uses_observed_water_stress() -> None:
    b = _bundle(fire=0.0, waterlog=0.0, precip=1500.0, et=500.0)
    risk = environmental_risk(b, "present")
    assert 0.0 <= risk <= 1.0


def test_environmental_risk_future_uses_delta_water_stress() -> None:
    b = _bundle(fire=0.0, waterlog=0.0, precip_delta=-20.0, temp_delta=2.0, et_norm=None)
    risk = environmental_risk(b, "future")
    # temp_term=2/3, precip_term=20/30=2/3, sin et → stress = (2/3)*0.57+(2/3)*0.43 = 2/3
    # risk = 0*0.35 + (2/3)*0.40 + 0*0.25 = 0.8/3
    assert risk == pytest.approx((2.0 / 3.0) * 0.40)


def test_environmental_risk_invalid_scenario_raises() -> None:
    with pytest.raises(ValueError, match="scenario inválido"):
        environmental_risk(_bundle(), "pasado")


def test_site_aptitude_in_unit_interval() -> None:
    b = _bundle()
    for scenario in ("present", "future"):
        v = site_aptitude(b, scenario)
        assert 0.0 <= v <= 1.0


def test_site_aptitude_better_soil_higher_score() -> None:
    b1 = _bundle(soil_score=0.4)
    b2 = _bundle(soil_score=0.9)
    assert site_aptitude(b2, "present") > site_aptitude(b1, "present")


def test_site_aptitude_higher_risk_lower_score() -> None:
    b1 = _bundle(fire=0.1, waterlog=0.1)
    b2 = _bundle(fire=0.9, waterlog=0.9)
    assert site_aptitude(b1, "future") > site_aptitude(b2, "future")


def test_site_aptitude_higher_access_higher_score() -> None:
    b1 = _bundle(access=0.2)
    b2 = _bundle(access=0.9)
    assert site_aptitude(b2, "present") > site_aptitude(b1, "present")


def test_site_aptitude_monotonic_in_soil() -> None:
    """Monotonicidad: a mejor suelo, mayor aptitud (riesgo y acceso constantes)."""
    last = -1.0
    for s in [0.0, 0.2, 0.5, 0.8, 1.0]:
        v = site_aptitude(_bundle(soil_score=s, fire=0.0, waterlog=0.0, access=0.0), "present")
        assert v >= last
        last = v

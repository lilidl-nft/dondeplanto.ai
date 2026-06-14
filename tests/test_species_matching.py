"""Tests de la Capa B del scoring: match especie-sitio (spec 5.5)."""

from __future__ import annotations

import pytest

from dondeplanto.scoring.species_matching import species_climate_fit, species_fit_future

_DUNNII = {
    "temp_min_c": 12,
    "temp_opt_low_c": 18,
    "temp_opt_high_c": 24,
    "temp_max_c": 28,
    "precip_min_mm": 800,
    "precip_opt_low_mm": 1000,
    "precip_opt_high_mm": 1400,
    "precip_max_mm": 1800,
    "drought_tolerance": 0.7,
    "fire_sensitivity": 0.5,
}


def test_species_climate_fit_in_optimal_returns_one() -> None:
    """Temp 20°C, precip 1200 mm están en el óptimo de dunnii → 1.0."""
    assert species_climate_fit(_DUNNII, 20.0, 1200.0) == pytest.approx(1.0)


def test_species_climate_fit_below_range_returns_low() -> None:
    """Temp 5°C está por debajo del mínimo (12) → temp fit = 0."""
    # precip=1200 (óptimo=1.0), temp=5 → temp=0
    # fit = 0.5*0 + 0.5*1.0 = 0.5
    assert species_climate_fit(_DUNNII, 5.0, 1200.0) == pytest.approx(0.5)


def test_species_climate_fit_above_range_returns_low() -> None:
    """Temp 35°C está por encima del máximo (28) → temp fit = 0."""
    assert species_climate_fit(_DUNNII, 35.0, 1200.0) == pytest.approx(0.5)


def test_species_climate_fit_incomplete_profile_returns_zero() -> None:
    """Perfil sin campos requeridos → 0 (no crashea)."""
    assert species_climate_fit({}, 20.0, 1200.0) == 0.0


def test_species_fit_future_drought_tolerance_amortigua_caida() -> None:
    """Mayor drought_tolerance amortigua la caída de fit al pasar a clima peor.

    Comparamos dos perfiles idénticos salvo drought_tolerance, ante el mismo
    cambio climático.
    """
    p_low_drought = dict(_DUNNII, drought_tolerance=0.2)
    p_high_drought = dict(_DUNNII, drought_tolerance=0.8)
    future = {"future_temp_max_mean": 27.0, "future_precip_sum": 850.0}
    # Present fit idéntico para ambos
    present = species_climate_fit(_DUNNII, 20.0, 1200.0)  # 1.0
    fit_low = species_fit_future(p_low_drought, future, present)
    fit_high = species_fit_future(p_high_drought, future, present)
    # Especie tolerante a la sequía debe perder menos aptitud → fit mayor
    assert fit_high > fit_low


def test_species_fit_future_worse_climate_loses_more_fit_for_low_tolerance() -> None:
    """Una especie con drought_tolerance baja cae más fuerte si el clima empeora."""
    p = dict(_DUNNII, drought_tolerance=0.0)
    future = {"future_temp_max_mean": 30.0, "future_precip_sum": 700.0}
    present = species_climate_fit(p, 20.0, 1200.0)
    fit = species_fit_future(p, future, present)
    # Present es 1.0, raw_future es bajo, sin amortiguación → fit debe bajar
    assert fit < present


def test_species_fit_future_never_exceeds_unit_interval() -> None:
    p = dict(_DUNNII, drought_tolerance=1.0)  # máxima amortiguación
    future = {"future_temp_max_mean": 21.0, "future_precip_sum": 1200.0}  # casi igual
    present = species_climate_fit(p, 20.0, 1200.0)
    fit = species_fit_future(p, future, present)
    assert 0.0 <= fit <= 1.0


def test_species_fit_future_does_not_exceed_present() -> None:
    """Si el clima futuro es peor, el fit futuro no supera al presente (con
    cualquier tolerancia). La amortiguación es un piso, no un impulso."""
    p = dict(_DUNNII, drought_tolerance=0.0)
    future = {"future_temp_max_mean": 30.0, "future_precip_sum": 700.0}
    present = species_climate_fit(p, 20.0, 1200.0)
    fit = species_fit_future(p, future, present)
    assert fit <= present

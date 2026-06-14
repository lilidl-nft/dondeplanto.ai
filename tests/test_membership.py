"""Tests de la membresía trapezoidal (fórmula 5.2 del spec).

Cobertura obligatoria (sección 7):
- bordes: x <= x_min y x >= x_max → 0
- óptimo: opt_low <= x <= opt_high → 1
- rampas lineales en ambos flancos
"""

from __future__ import annotations

import pytest

from dondeplanto.scoring.membership import trapezoidal


@pytest.mark.parametrize("x", [-100.0, 0.0, 10.0])
def test_trapezoidal_below_min_returns_zero(x: float) -> None:
    """Por debajo o igual al mínimo absoluto → 0."""
    assert trapezoidal(x, 10.0, 20.0, 30.0, 40.0) == 0.0


@pytest.mark.parametrize("x", [40.0, 50.0, 1000.0])
def test_trapezoidal_above_max_returns_zero(x: float) -> None:
    """Por encima o igual al máximo absoluto → 0."""
    assert trapezoidal(x, 10.0, 20.0, 30.0, 40.0) == 0.0


@pytest.mark.parametrize("x", [20.0, 25.0, 30.0])
def test_trapezoidal_in_optimum_returns_one(x: float) -> None:
    """Dentro de la meseta óptima → 1."""
    assert trapezoidal(x, 10.0, 20.0, 30.0, 40.0) == 1.0


def test_trapezoidal_ramp_left_linear() -> None:
    """Rampa izquierda lineal de x_min a opt_low."""
    # (15 - 10) / (20 - 10) = 0.5
    assert trapezoidal(15.0, 10.0, 20.0, 30.0, 40.0) == pytest.approx(0.5)
    # (12 - 10) / (20 - 10) = 0.2
    assert trapezoidal(12.0, 10.0, 20.0, 30.0, 40.0) == pytest.approx(0.2)


def test_trapezoidal_ramp_right_linear() -> None:
    """Rampa derecha lineal de opt_high a x_max."""
    # (40 - 35) / (40 - 30) = 0.5
    assert trapezoidal(35.0, 10.0, 20.0, 30.0, 40.0) == pytest.approx(0.5)
    # (40 - 38) / (40 - 30) = 0.2
    assert trapezoidal(38.0, 10.0, 20.0, 30.0, 40.0) == pytest.approx(0.2)


def test_trapezoidal_monotone_on_left_flank() -> None:
    """La rampa izquierda es monótona creciente."""
    prev = -1.0
    for x in [10.5, 12.0, 15.0, 18.0, 19.9]:
        v = trapezoidal(x, 10.0, 20.0, 30.0, 40.0)
        assert v > prev
        prev = v


def test_trapezoidal_monotone_on_right_flank() -> None:
    """La rampa derecha es monótona decreciente."""
    prev = 2.0
    for x in [30.1, 32.0, 35.0, 38.0, 39.5]:
        v = trapezoidal(x, 10.0, 20.0, 30.0, 40.0)
        assert v < prev
        prev = v


def test_trapezoidal_result_in_unit_interval() -> None:
    """Cualquier entrada razonable da resultado en [0, 1]."""
    for x in [9.999, 10.0, 10.001, 15.0, 20.0, 25.0, 30.0, 35.0, 39.999, 40.0, 40.001]:
        v = trapezoidal(x, 10.0, 20.0, 30.0, 40.0)
        assert 0.0 <= v <= 1.0


def test_trapezoidal_invalid_borders_returns_zero() -> None:
    """Bordes invertidos → 0 y warning (no crashea)."""
    # opt_low > opt_high
    assert trapezoidal(15.0, 10.0, 30.0, 20.0, 40.0) == 0.0
    # x_min > opt_low
    assert trapezoidal(15.0, 25.0, 20.0, 30.0, 40.0) == 0.0

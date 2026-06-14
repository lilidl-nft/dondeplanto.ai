"""Funciones de membresía difusa (cap A del scoring).

Implementa la membresía trapezoidal del spec sección 5.2, usada para
evaluar si un valor escalar (temperatura, precipitación) cae dentro del
rango óptimo de una especie o de un perfil de suelo.
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

# Tipos esperados por argumento (documentación, no enforced en runtime).
_SCORE_MIN: Final[float] = 0.0
_SCORE_MAX: Final[float] = 1.0


def trapezoidal(
    x: float,
    x_min: float,
    opt_low: float,
    opt_high: float,
    x_max: float,
) -> float:
    """Membresía trapezoidal (fórmula 5.2 del spec).

    Devuelve 1.0 si `x` está dentro de la meseta óptima `[opt_low, opt_high]`,
    baja linealmente a 0 en los extremos `[x_min, opt_low]` y `[opt_high, x_max]`,
    y vale 0 fuera de `[x_min, x_max]`.

    Args:
        x: valor a evaluar.
        x_min: borde inferior absoluto (por debajo → 0).
        opt_low: borde inferior de la meseta óptima.
        opt_high: borde superior de la meseta óptima.
        x_max: borde superior absoluto (por encima → 0).

    Returns:
        Membresía en [0.0, 1.0]. Si los bordes no satisfacen
        `x_min <= opt_low <= opt_high <= x_max` se devuelve 0.0
        y se loggea un warning (configuración inválida).
    """
    if x_min > opt_low or opt_low > opt_high or opt_high > x_max:
        logger.warning(
            "trapezoidal: bordes inválidos min=%s opt_low=%s opt_high=%s max=%s",
            x_min,
            opt_low,
            opt_high,
            x_max,
        )
        return _SCORE_MIN

    if x <= x_min or x >= x_max:
        return _SCORE_MIN
    if opt_low <= x <= opt_high:
        return _SCORE_MAX

    # Rampa ascendente: x_min < x < opt_low
    if x < opt_low:
        denom = opt_low - x_min
        if denom == 0:
            return _SCORE_MAX
        return (x - x_min) / denom

    # Rampa descendente: opt_high < x < x_max
    denom = x_max - opt_high
    if denom == 0:
        return _SCORE_MAX
    return (x_max - x) / denom

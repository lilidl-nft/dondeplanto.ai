"""Capa B del scoring: match especie-sitio (spec sección 5.5).

Funciones puras, determinísticas, sin I/O. Proyectan la temperatura y
precipitación de un sitio sobre los rangos óptimos de una especie
(usando `membership.trapezoidal`) y aplican la tolerancia a la sequía
para amortiguar la caída de aptitud al pasar al clima futuro.
"""

from __future__ import annotations

import logging
from typing import Any

from dondeplanto.scoring.membership import trapezoidal

logger = logging.getLogger(__name__)


def species_climate_fit(profile: dict[str, Any], temp: float, precip: float) -> float:
    """Ajuste climático de una especie a un par (temp, precip) (fórmula 5.5).

    Combina 50/50 la membresía trapezoidal de la temperatura y la de la
    precipitación contra los rangos del perfil. Las claves del perfil
    siguen la sección 2.8 del spec.

    Args:
        profile: dict con `temp_min_c`, `temp_opt_low_c`, `temp_opt_high_c`,
            `temp_max_c`, `precip_min_mm`, `precip_opt_low_mm`,
            `precip_opt_high_mm`, `precip_max_mm`.
        temp: temperatura media de máximas (°C).
        precip: precipitación acumulada anual (mm).

    Returns:
        Fit en [0, 1]. Si el perfil está incompleto, devuelve 0.0.
    """
    try:
        t = trapezoidal(
            float(temp),
            float(profile["temp_min_c"]),
            float(profile["temp_opt_low_c"]),
            float(profile["temp_opt_high_c"]),
            float(profile["temp_max_c"]),
        )
        p = trapezoidal(
            float(precip),
            float(profile["precip_min_mm"]),
            float(profile["precip_opt_low_mm"]),
            float(profile["precip_opt_high_mm"]),
            float(profile["precip_max_mm"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("species_climate_fit: perfil inválido (%s)", exc)
        return 0.0
    return 0.5 * t + 0.5 * p


def species_fit_future(
    profile: dict[str, Any],
    future_climate: dict[str, Any],
    present_fit: float,
) -> float:
    """Fit futuro ajustado por `drought_tolerance` (fórmula 5.5).

    Implementación "simple" recomendada por el spec:
        `raw_future = species_climate_fit(future_temp, future_precip)`
        `penalizacion = (present_fit - raw_future) * (1 - drought_tolerance)`
        `species_fit_future = clamp(present_fit - penalizacion, 0, 1)`

    Especies con mayor `drought_tolerance` pierden menos aptitud al pasar
    del clima presente al clima futuro.

    Args:
        profile: dict con `drought_tolerance` (0..1) y rangos trapezoidales.
        future_climate: bloque `future` del bundle, con `future_temp_max_mean`
            y `future_precip_sum`.
        present_fit: fit presente calculado previamente (0..1).

    Returns:
        Fit futuro en [0, 1].
    """
    raw_future = species_climate_fit(
        profile,
        float(future_climate["future_temp_max_mean"]),
        float(future_climate["future_precip_sum"]),
    )
    drought = float(profile.get("drought_tolerance", 0.0))
    if not 0.0 <= drought <= 1.0:
        logger.warning("drought_tolerance fuera de [0,1]: %s — clipping", drought)
        drought = max(0.0, min(1.0, drought))

    penalizacion = (present_fit - raw_future) * (1.0 - drought)
    fit = present_fit - penalizacion
    if fit < 0.0:
        return 0.0
    if fit > 1.0:
        return 1.0
    return fit

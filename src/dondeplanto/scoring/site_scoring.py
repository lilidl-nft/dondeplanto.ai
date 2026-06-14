"""Capa A del scoring: aptitud del sitio (spec sección 5.1 y 5.4).

Funciones puras, determinísticas, sin I/O. Combinan la aptitud del suelo
(INTA) con el riesgo ambiental (fuego + estrés hídrico + anegamiento)
para producir la aptitud del sitio en escenario presente o futuro.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Pesos del score (fórmula 5.1) y del riesgo ambiental (5.4).
_SOIL_WEIGHT: float = 0.45
_ENV_SAFE_WEIGHT: float = 0.35  # peso de (1 - environmental_risk)
_ACCESS_WEIGHT: float = 0.20

_FIRE_WEIGHT: float = 0.35
_WATER_STRESS_WEIGHT: float = 0.40
_WATERLOG_WEIGHT: float = 0.25

# Pesos internos de la fórmula 5.3 (estrés hídrico futuro).
_TEMP_WEIGHT_WITH_ET: float = 0.50
_PRECIP_WEIGHT_WITH_ET: float = 0.35
_ET_WEIGHT: float = 0.15
# Si no hay ET, redistribuir a 0.57 / 0.43 (escala cerrada a 1.0).
_TEMP_WEIGHT_NO_ET: float = 0.57
_PRECIP_WEIGHT_NO_ET: float = 0.43

# Constantes de normalización de la fórmula 5.3.
_TEMP_DELTA_REF_C: float = 3.0
_PRECIP_DELTA_REF_PCT: float = 30.0

# Precipitación óptima de referencia para el estrés hídrico "presente".
# 1000 mm/yr es el punto medio del rango óptimo de las 3 especies
# comerciales del NEA en `data/species_profiles.yaml`
# (dunnii: 1000-1400, grandis: 1200-1800, taeda: 900-1500).
# Documentado en `docs/scoring_methodology.md`.
_PRESENT_PRECIP_OPT_MM: float = 1000.0


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Satura un valor al rango [lo, hi]."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def water_stress_future(future: dict[str, Any]) -> float:
    """Calcula `water_stress_future` con la fórmula 5.3.

    Si `evapotranspiration_norm` está ausente, redistribuye el peso a
    temperatura y precipitación (0.57/0.43) manteniendo la suma 1.0.

    Args:
        future: bloque `future` del FeatureBundle. Se esperan las keys
            `temp_max_delta` (°C), `precip_delta_pct` (%) y, opcionalmente,
            `evapotranspiration_norm` (0..1). Si la ya viene pre-computada
            `water_stress_future` en el bundle (caso F4) se usa ese valor
            como atajo.
    """
    if "water_stress_future" in future and future["water_stress_future"] is not None:
        return _clamp(float(future["water_stress_future"]))

    temp_term = _clamp(float(future.get("temp_max_delta", 0.0)) / _TEMP_DELTA_REF_C)
    precip_term = _clamp(-float(future.get("precip_delta_pct", 0.0)) / _PRECIP_DELTA_REF_PCT)
    et_raw = future.get("evapotranspiration_norm")
    et_term = _clamp(float(et_raw)) if et_raw is not None else None

    if et_term is None:
        return _clamp(temp_term * _TEMP_WEIGHT_NO_ET + precip_term * _PRECIP_WEIGHT_NO_ET)
    return _clamp(
        temp_term * _TEMP_WEIGHT_WITH_ET
        + precip_term * _PRECIP_WEIGHT_WITH_ET
        + et_term * _ET_WEIGHT
    )


def water_stress_present(observed: dict[str, Any]) -> float:
    """Calcula un proxy de estrés hídrico observado (presente).

    No hay un campo `water_stress` explícito en el bloque `observed`, así
    que se aproxima a partir de la precipitación anual observada: a menor
    precipitación efectiva, mayor estrés.

    Estrategia (justificada):
        `stress = 1 - clamp(obs_precip / PRECIP_OPT, 0, 1) * (1 - et_severity)`
        donde `et_severity = clamp(obs_et / obs_precip, 0, 1)` castiga los
        sitios donde la evapotranspiración se acerca a la precipitación
        recibida (sequía efectiva alta).

    Si faltan datos (None), se devuelve 0.30 como placeholder neutro
    (documentado como TODO en `docs/scoring_methodology.md` para que F5
    lo reemplace cuando integre un índice observado explícito).
    """
    precip = observed.get("obs_precip_sum_annual")
    if precip is None:
        logger.debug("water_stress_present: precip faltante, uso placeholder 0.30")
        return 0.30

    precip_norm = _clamp(float(precip) / _PRESENT_PRECIP_OPT_MM)

    et = observed.get("obs_evapotranspiration_annual")
    et_severity = 0.0
    if et is not None and float(precip) > 0:
        et_severity = _clamp(float(et) / float(precip))

    # dryness = (1 - precip_norm) modulado por severidad de ET.
    dryness = (1.0 - precip_norm) * (0.5 + 0.5 * et_severity)
    return _clamp(dryness)


def environmental_risk(bundle: dict[str, Any], scenario: str) -> float:
    """Riesgo ambiental del sitio (fórmula 5.4).

    `scenario="present"` usa el agua estresada observada (proxy de
    `water_stress_present`); `scenario="future"` usa `water_stress_future`
    derivado del delta climático.

    Args:
        bundle: FeatureBundle completo.
        scenario: `"present"` o `"future"`.

    Returns:
        Riesgo ambiental en [0, 1].
    """
    fire_score = float(bundle["fire"]["fire_activity_score"])
    water_stress: float
    if scenario == "future":
        water_stress = water_stress_future(bundle["future"])
    elif scenario == "present":
        water_stress = water_stress_present(bundle["observed"])
    else:
        raise ValueError(f"scenario inválido: {scenario!r} (esperado 'present' o 'future')")

    waterlog = float(bundle["soil"]["waterlogging_risk"])
    risk = (
        fire_score * _FIRE_WEIGHT
        + water_stress * _WATER_STRESS_WEIGHT
        + waterlog * _WATERLOG_WEIGHT
    )
    return _clamp(risk)


def site_aptitude(bundle: dict[str, Any], scenario: str) -> float:
    """Aptitud del sitio (fórmula 5.1).

    Args:
        bundle: FeatureBundle completo.
        scenario: `"present"` o `"future"`.

    Returns:
        Aptitud en [0, 1].
    """
    soil_score = float(bundle["soil"]["soil_aptitude_score"])
    env_risk = environmental_risk(bundle, scenario)
    access = float(bundle["logistics"]["accessibility_score"])
    return _clamp(
        soil_score * _SOIL_WEIGHT + (1.0 - env_risk) * _ENV_SAFE_WEIGHT + access * _ACCESS_WEIGHT
    )

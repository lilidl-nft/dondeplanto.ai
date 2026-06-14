"""Funciones puras: respuestas crudas de Open-Meteo Climate API -> FutureClimate.

Estas funciones son determinísticas, sin I/O, sin red, y son la base de
los tests de F4. Reciben la respuesta cruda de la API y la reducen a
promedios anuales y deltas.

Contrato de salida (sección 2.4 del build spec): FutureClimate.

Para la fórmula de `water_stress_future` (5.3) ver
`scoring.site_scoring.water_stress_future` (F3 ya la implementó); acá solo
se ofrece un helper `compute_water_stress_future` que la invoca de forma
idéntica, útil para que el cliente `open_meteo_climate_client` calcule el
campo sin tener que importar de scoring.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

# Constantes de normalización de la fórmula 5.3 (idénticas a site_scoring).
# Definidas localmente para evitar acoplamiento inverso (cliente -> features)
# manteniendo los valores sincronizados manualmente.
_TEMP_DELTA_REF_C: float = 3.0
_PRECIP_DELTA_REF_PCT: float = 30.0
_TEMP_WEIGHT_NO_ET: float = 0.57
_PRECIP_WEIGHT_NO_ET: float = 0.43
_TEMP_WEIGHT_WITH_ET: float = 0.50
_PRECIP_WEIGHT_WITH_ET: float = 0.35
_ET_WEIGHT: float = 0.15

# Claves esperadas en la respuesta cruda de Open-Meteo Climate API.
_DAILY_KEY_TIME: str = "time"
_DAILY_KEY_TMAX: str = "temperature_2m_max"
_DAILY_KEY_TMIN: str = "temperature_2m_min"
_DAILY_KEY_PRECIP: str = "precipitation_sum"

# Daily unit expected (todos los daily de Open-Meteo vienen en estas).
_DAILY_FIELDS: tuple[str, ...] = (_DAILY_KEY_TMAX, _DAILY_KEY_TMIN, _DAILY_KEY_PRECIP)


def _safe_mean(values: list[float | None] | None) -> float | None:
    """Promedia una lista ignorando None y NaN. None si no hay valores válidos."""
    if not values:
        return None
    clean = [v for v in values if v is not None and not math.isnan(v)]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _safe_sum(values: list[float | None] | None) -> float | None:
    """Suma una lista ignorando None y NaN. None si no hay valores válidos."""
    if not values:
        return None
    clean = [v for v in values if v is not None and not math.isnan(v)]
    if not clean:
        return None
    return float(sum(clean))


def _extract_daily(response: dict[str, Any]) -> dict[str, list[float | None]]:
    """Extrae los arrays de `daily` de la respuesta cruda.

    Acepta tanto la forma estándar (`response["daily"]["temperature_2m_max"]`)
    como la forma que devuelve la API cuando un modelo no provee el campo
    (el campo se omite en vez de ser None). Devuelve listas alineadas con
    `time`, rellenando con None donde el modelo no reportó.
    """
    daily = response.get("daily") or {}
    time_list = list(daily.get(_DAILY_KEY_TIME) or [])
    n = len(time_list)
    out: dict[str, list[float | None]] = {
        _DAILY_KEY_TIME: time_list,
        _DAILY_KEY_TMAX: list(daily.get(_DAILY_KEY_TMAX) or [])
        if _DAILY_KEY_TMAX in daily
        else [None] * n,
        _DAILY_KEY_TMIN: list(daily.get(_DAILY_KEY_TMIN) or [])
        if _DAILY_KEY_TMIN in daily
        else [None] * n,
        _DAILY_KEY_PRECIP: (
            list(daily.get(_DAILY_KEY_PRECIP) or []) if _DAILY_KEY_PRECIP in daily else [None] * n
        ),
    }
    # Alinear longitudes.
    for key in (_DAILY_KEY_TMAX, _DAILY_KEY_TMIN, _DAILY_KEY_PRECIP):
        arr = out[key]
        if len(arr) < n:
            arr.extend([None] * (n - len(arr)))
        elif len(arr) > n:
            del arr[n:]
    return out


def annual_means_from_response(response: dict[str, Any]) -> dict[str, float | None]:
    """Reduce la respuesta cruda de un período a promedios anuales.

    Returns:
        dict con `temp_max_mean`, `temp_min_mean`, `precip_sum` (anual).
        Cada valor puede ser None si la API no reportó el campo.
    """
    daily = _extract_daily(response)
    return {
        "temp_max_mean": _safe_mean(daily[_DAILY_KEY_TMAX]),
        "temp_min_mean": _safe_mean(daily[_DAILY_KEY_TMIN]),
        "precip_sum": _safe_sum(daily[_DAILY_KEY_PRECIP]),
    }


def compute_delta(
    baseline_response: dict[str, Any],
    future_response: dict[str, Any],
) -> dict[str, float | None]:
    """Calcula `temp_max_delta` y `precip_delta_pct` entre dos respuestas.

    Returns:
        dict con `baseline_temp_max_mean`, `future_temp_max_mean`,
        `temp_max_delta`, `baseline_precip_sum`, `future_precip_sum`,
        `precip_delta_pct`. Cualquier campo puede ser None si la API no
        reportó el dato correspondiente.
    """
    b = annual_means_from_response(baseline_response)
    f = annual_means_from_response(future_response)

    b_tmax = b["temp_max_mean"]
    f_tmax = f["temp_max_mean"]
    temp_max_delta: float | None = (
        None if b_tmax is None or f_tmax is None else float(f_tmax - b_tmax)
    )

    b_precip = b["precip_sum"]
    f_precip = f["precip_sum"]
    precip_delta_pct: float | None
    if b_precip is None or f_precip is None or float(b_precip) == 0.0:
        precip_delta_pct = None
    else:
        precip_delta_pct = float((f_precip - b_precip) / b_precip) * 100.0

    return {
        "baseline_temp_max_mean": b_tmax,
        "future_temp_max_mean": f_tmax,
        "temp_max_delta": temp_max_delta,
        "baseline_precip_sum": b_precip,
        "future_precip_sum": f_precip,
        "precip_delta_pct": precip_delta_pct,
    }


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Satura un valor al rango [lo, hi]."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def compute_water_stress_future(
    temp_max_delta: float | None,
    precip_delta_pct: float | None,
    evapotranspiration_norm: float | None = None,
) -> float:
    """Implementación de la fórmula 5.3 para el `FutureClimate.water_stress_future`.

    Es una copia deliberada de `scoring.site_scoring.water_stress_future`
    reducida a sus inputs escalares puros (no consulta dicts). Permite que
    el cliente de clima la use sin importar de `scoring`, manteniendo la
    capa de features como única transformadora pura.

    Si `temp_max_delta` o `precip_delta_pct` son None, se tratan como 0
    (degradación controlada, registrada como fuente mock si el caller lo
    decide).

    Si `evapotranspiration_norm` es None, redistribuye el peso a 0.57/0.43
    (temp/precip) manteniendo la suma 1.0.
    """
    temp_term = _clamp(float(temp_max_delta or 0.0) / _TEMP_DELTA_REF_C)
    precip_term = _clamp(-float(precip_delta_pct or 0.0) / _PRECIP_DELTA_REF_PCT)

    if evapotranspiration_norm is None:
        return _clamp(temp_term * _TEMP_WEIGHT_NO_ET + precip_term * _PRECIP_WEIGHT_NO_ET)
    et_term = _clamp(float(evapotranspiration_norm))
    return _clamp(
        temp_term * _TEMP_WEIGHT_WITH_ET
        + precip_term * _PRECIP_WEIGHT_WITH_ET
        + et_term * _ET_WEIGHT
    )


def build_future_climate(
    baseline_response: dict[str, Any],
    future_response: dict[str, Any],
    *,
    source: str = "open_meteo_climate",
    ensemble_spread: float | None = None,
    evapotranspiration_norm: float | None = None,
) -> dict[str, Any]:
    """Compone un FutureClimate a partir de las dos respuestas crudas.

    Es la función de ensamblado final: toma las dos respuestas (puede ser
    la misma forma que devuelve la API o la forma cruda que cachea el
    cliente), calcula los deltas y el water_stress, y devuelve el dict
    del contrato 2.4 listo para guardarlo en el FeatureBundle.

    Args:
        baseline_response: respuesta cruda del período baseline.
        future_response: respuesta cruda del período futuro.
        source: `"open_meteo_climate"` si vino de la API real;
            `"mock"` si el caller decidió degradar.
        ensemble_spread: std de temp_max_delta entre modelos (None si
            es un modelo único).
        evapotranspiration_norm: opcional, 0..1, si se tiene.
    """
    delta = compute_delta(baseline_response, future_response)
    return build_future_climate_from_deltas(
        delta,
        source=source,
        ensemble_spread=ensemble_spread,
        evapotranspiration_norm=evapotranspiration_norm,
    )


def build_future_climate_from_deltas(
    delta: dict[str, float | None],
    *,
    source: str = "open_meteo_climate",
    ensemble_spread: float | None = None,
    evapotranspiration_norm: float | None = None,
) -> dict[str, Any]:
    """Compone un FutureClimate a partir de deltas ya calculados.

    Útil cuando se promedian varios modelos (cada uno tiene su propio
    delta) y se quiere construir el FutureClimate final con los promedios.
    """
    ws = compute_water_stress_future(
        temp_max_delta=delta["temp_max_delta"],
        precip_delta_pct=delta["precip_delta_pct"],
        evapotranspiration_norm=evapotranspiration_norm,
    )
    return {
        "baseline_temp_max_mean": delta["baseline_temp_max_mean"],
        "future_temp_max_mean": delta["future_temp_max_mean"],
        "temp_max_delta": delta["temp_max_delta"],
        "baseline_precip_sum": delta["baseline_precip_sum"],
        "future_precip_sum": delta["future_precip_sum"],
        "precip_delta_pct": delta["precip_delta_pct"],
        "water_stress_future": ws,
        "ensemble_spread": ensemble_spread,
        "source": source,
    }

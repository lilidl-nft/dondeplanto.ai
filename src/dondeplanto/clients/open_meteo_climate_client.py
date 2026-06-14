"""Cliente Open-Meteo Climate API (modificador futuro, F4).

Endpoint: `config.OPEN_METEO_CLIMATE`
(https://climate-api.open-meteo.com/v1/climate)

Funciones públicas:
  - `get_climate_period(lat, lon, start_date, end_date, model, use_mock=False)`
      Devuelve la respuesta cruda con `daily.time`, `daily.temperature_2m_max`,
      `daily.temperature_2m_min` y `daily.precipitation_sum`. Se cachea por
      `(round(lat,2), round(lon,2), model, start_date, end_date)`.

  - `get_climate_delta(lat, lon, baseline_period, future_period, model="ensemble",
                       use_mock=False)`
      Devuelve el contrato `FutureClimate` (sección 2.4 del build spec)
      calculando el delta entre los dos períodos. `model="ensemble"` promedia
      los modelos de `config.CLIMATE_MODELS` y reporta la desviación estándar
      del `temp_max_delta` como `ensemble_spread`.

Reglas duras:
  - `use_mock=True` o cualquier excepción de red → mock con `source="mock"`.
  - Timeouts siempre (`config.HTTP_TIMEOUT_LONG`).
  - Sin red en tests (mockear `requests.get` o `httpx`).
"""

from __future__ import annotations

import logging
import math
from functools import lru_cache
from typing import Any, cast

import requests

from dondeplanto.config import (
    BASELINE_PERIOD,
    CLIMATE_MODELS,
    FUTURE_PERIOD,
    HTTP_TIMEOUT_LONG,
    OPEN_METEO_CLIMATE,
)
from dondeplanto.features.climate_features import (
    build_future_climate_from_deltas,
    compute_delta,
)
from dondeplanto.mock import get_mock_bundle

logger = logging.getLogger(__name__)

# Daily fields que pedimos a la API. Documentado en el spec sección 4.5.
_DAILY_FIELDS: str = "temperature_2m_max,temperature_2m_min,precipitation_sum"

# Identificador de fuente para los mocks devueltos por este cliente.
_SOURCE_API: str = "open_meteo_climate"


# ---------------------------------------------------------------------------
# Cache de respuestas crudas
# ---------------------------------------------------------------------------


@lru_cache(maxsize=256)
def _cached_request(
    lat_q: float,
    lon_q: float,
    model: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Cachea la respuesta cruda de la API por (lat, lon, model, período).

    El cache usa `lru_cache` con key posicional: `lat_q` y `lon_q` llegan
    ya redondeados a 2 decimales por el caller. Esto evita que dos puntos
    a 50 m de diferencia peguen dos requests distintas.
    """
    params: dict[str, str] = {
        "latitude": f"{lat_q:.2f}",
        "longitude": f"{lon_q:.2f}",
        "start_date": start_date,
        "end_date": end_date,
        "models": model,
        "daily": _DAILY_FIELDS,
        "timezone": "GMT",
    }
    logger.info(
        "Open-Meteo Climate: lat=%.2f lon=%.2f model=%s period=%s..%s",
        lat_q,
        lon_q,
        model,
        start_date,
        end_date,
    )
    response = requests.get(OPEN_METEO_CLIMATE, params=params, timeout=HTTP_TIMEOUT_LONG)
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    return payload


def _mock_response(lat: float, lon: float, start_date: str, end_date: str) -> dict[str, Any]:
    """Devuelve una respuesta cruda de la API con forma plausible pero mock.

    Sirve para que `get_climate_period` en modo mock devuelva un objeto
    estructurado igual al real, permitiendo que los features puros se
    calculen sin tocar red. NO es data real: marcada con `source="mock"`
    por el caller.

    Estrategia: deriva un único año "promedio" a partir de los `temp_max_mean`
    y `precip_sum` del bundle mock de la provincia, y lo replica día a día
    con un poco de jitter determinístico (basado en el día del año). Esto
    hace que los deltas anuales sean aproximadamente reproducibles.
    """
    bundle = get_mock_bundle(lat, lon)
    fut = bundle["future"]
    # Para el período baseline usamos los valores baseline del mock, para
    # el futuro los del future (períodos típicos: 1991-2020 y 2041-2060).
    # Si el caller pide un período futuro, usamos los deltas fut del mock.
    # La identificación la hace el caller (que conoce las fechas).
    # Acá devolvemos algo "neutro" reutilizable: promediamos ambos.
    base_tmax = (float(fut["baseline_temp_max_mean"]) + float(fut["future_temp_max_mean"])) / 2.0
    base_precip = (float(fut["baseline_precip_sum"]) + float(fut["future_precip_sum"])) / 2.0

    # Generamos 365 días con un poco de variación estacional senoidal
    # determinística según el día del año. La suma anual cierra
    # aproximadamente en `base_precip`; la media en `base_tmax`.
    n_days = 365
    times = [_mock_date_for_index(start_date, i) for i in range(n_days)]
    # Patrón estacional: ±4°C para tmax, ±30% para precipitación diaria.
    tmax_values: list[float | None] = []
    precip_values: list[float | None] = []
    for i in range(n_days):
        # día del año: 0..364
        doy = i
        seasonal_t = math.cos(2.0 * math.pi * (doy - 15) / 365.0) * 4.0
        seasonal_p = 1.0 + 0.4 * math.cos(2.0 * math.pi * (doy - 30) / 365.0)
        tmax_values.append(round(base_tmax + seasonal_t, 2))
        # precipitación diaria = precip_anual / 365 * factor estacional
        daily_p = (base_precip / 365.0) * max(0.1, seasonal_p)
        precip_values.append(round(daily_p, 2))

    return {
        "latitude": round(lat, 2),
        "longitude": round(lon, 2),
        "timezone": "GMT",
        "daily_units": {
            "time": "iso8601",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_sum": "mm",
        },
        "daily": {
            "time": times,
            "temperature_2m_max": tmax_values,
            "temperature_2m_min": [
                round(v - 8.0, 2) if v is not None else None for v in tmax_values
            ],
            "precipitation_sum": precip_values,
        },
        "_source": "mock",
    }


def _mock_date_for_index(start_date: str, index: int) -> str:
    """Devuelve la fecha `start_date + index días` en formato YYYY-MM-DD.

    Maneja el fin de mes/año de forma simple sin importar datetime.
    """
    year_s, month_s, day_s = start_date.split("-")
    year = int(year_s)
    month = int(month_s)
    day = int(day_s) + index
    # Días por mes (no bisiesto, suficiente para mock).
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    while day > days_in_month[month - 1]:
        day -= days_in_month[month - 1]
        month += 1
        if month > 12:
            month = 1
            year += 1
    return f"{year:04d}-{month:02d}-{day:02d}"


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def get_climate_period(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    model: str,
    use_mock: bool = False,
) -> dict[str, Any]:
    """Devuelve la respuesta cruda de la Climate API para un período.

    Args:
        lat, lon: coordenadas (WGS84).
        start_date, end_date: `"YYYY-MM-DD"`.
        model: nombre de modelo (ej. `"CMCC_CM2_VHR4"`) o `"ensemble"`.
        use_mock: si True, devuelve mock con `source="mock"` sin tocar red.

    Returns:
        dict con `daily.time`, `daily.temperature_2m_max`,
        `daily.temperature_2m_min`, `daily.precipitation_sum`. En modo
        mock, `response["_source"] == "mock"`.
    """
    if use_mock:
        return _mock_response(lat, lon, start_date, end_date)

    lat_q = round(float(lat), 2)
    lon_q = round(float(lon), 2)
    try:
        return _cached_request(lat_q, lon_q, model, start_date, end_date)
    except Exception as exc:  # noqa: BLE001 — degradación controlada a mock
        logger.warning(
            "Open-Meteo Climate: fallo de red (model=%s, %.2f,%.2f, %s..%s): %s; cayendo a mock",
            model,
            lat_q,
            lon_q,
            start_date,
            end_date,
            exc,
        )
        mock = _mock_response(lat, lon, start_date, end_date)
        mock["_source"] = "mock"
        return mock


def _resolve_models(model: str) -> list[str]:
    """Resuelve la lista efectiva de modelos a consultar.

    `"ensemble"` → todos los de `config.CLIMATE_MODELS`. Un nombre
    específico → una lista de un solo elemento.
    """
    if model == "ensemble":
        return list(CLIMATE_MODELS)
    return [model]


def _period_tuple(period: str | tuple[str, str]) -> tuple[str, str]:
    """Acepta `"1991-2020"` (string) o la tupla explícita.

    Devuelve `(start_date, end_date)`.
    """
    if isinstance(period, tuple):
        if len(period) != 2:
            raise ValueError(f"período inválido: {period!r}")
        return period[0], period[1]
    # Formato esperado: "YYYY-YYYY" (e.g. "1991-2020")
    parts = period.split("-")
    if len(parts) != 2:
        raise ValueError(f"período inválido: {period!r}; se esperaba 'YYYY-YYYY' o tupla")
    start_year, end_year = parts
    return f"{start_year}-01-01", f"{end_year}-12-31"


def get_climate_delta(
    lat: float,
    lon: float,
    baseline_period: str | tuple[str, str] = BASELINE_PERIOD,
    future_period: str | tuple[str, str] = FUTURE_PERIOD,
    model: str = "ensemble",
    use_mock: bool = False,
) -> dict[str, Any]:
    """Calcula el delta entre dos períodos y devuelve un `FutureClimate`.

    Si `model="ensemble"`, promedia los modelos de `config.CLIMATE_MODELS`
    y reporta la desviación estándar del `temp_max_delta` como
    `ensemble_spread`.

    Si la API falla o `use_mock=True`, devuelve un `FutureClimate` con
    `source="mock"` derivado del bundle mock de la provincia.
    """
    if use_mock:
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["future"]))

    baseline_dates = _period_tuple(baseline_period)
    future_dates = _period_tuple(future_period)
    models = _resolve_models(model)

    deltas: list[dict[str, float | None]] = []
    failed = False

    for m in models:
        try:
            b_resp = get_climate_period(lat, lon, baseline_dates[0], baseline_dates[1], m)
            f_resp = get_climate_period(lat, lon, future_dates[0], future_dates[1], m)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falla consultando modelo %s: %s", m, exc)
            failed = True
            break
        # Si get_climate_period degradó a mock (red caída), respetamos eso:
        if b_resp.get("_source") == "mock" or f_resp.get("_source") == "mock":
            failed = True
            break
        deltas.append(compute_delta(b_resp, f_resp))

    if failed or not deltas:
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["future"]))

    avg = _average_deltas(deltas)
    # Spread: std del temp_max_delta entre modelos (None si un solo modelo).
    if len(deltas) == 1:
        ensemble_spread: float | None = None
    else:
        tmax_deltas = [d["temp_max_delta"] for d in deltas if d["temp_max_delta"] is not None]
        ensemble_spread = _stdev([float(v) for v in tmax_deltas]) if len(tmax_deltas) >= 2 else None

    return build_future_climate_from_deltas(
        avg,
        source=_SOURCE_API,
        ensemble_spread=ensemble_spread,
        evapotranspiration_norm=None,
    )


def _average_deltas(deltas: list[dict[str, float | None]]) -> dict[str, float | None]:
    """Promedia los campos numéricos de una lista de deltas. None si todos None."""
    out: dict[str, float | None] = {}
    for key in (
        "baseline_temp_max_mean",
        "future_temp_max_mean",
        "temp_max_delta",
        "baseline_precip_sum",
        "future_precip_sum",
        "precip_delta_pct",
    ):
        vals: list[float] = []
        for d in deltas:
            v = d.get(key)
            if v is not None:
                vals.append(float(v))
        out[key] = sum(vals) / len(vals) if vals else None
    return out


def _stdev(values: list[float]) -> float:
    """Desviación estándar poblacional (n en denominador)."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)


# ---------------------------------------------------------------------------
# Helpers de testing
# ---------------------------------------------------------------------------


def clear_cache() -> None:
    """Limpia el cache de requests. Solo para tests."""
    _cached_request.cache_clear()


def cache_info() -> Any:
    """Inspección de cache. Solo para tests."""
    return _cached_request.cache_info()


# Re-exportar la constante del JSON de debug para que tests no tengan que
# adivinar el formato. No se usa en runtime.
__all__ = [
    "get_climate_period",
    "get_climate_delta",
    "clear_cache",
    "cache_info",
]

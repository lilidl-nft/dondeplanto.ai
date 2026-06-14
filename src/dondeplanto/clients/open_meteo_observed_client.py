"""Cliente Open-Meteo Historical Weather (ERA5-Land) - F5 (clima observado).

Acumulados anuales para mostrar el clima actual al usuario. NO se usa
como baseline del delta climático (eso es F4, con la Climate API).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, cast

import requests

from dondeplanto.config import (
    HTTP_TIMEOUT_LONG,
    OPEN_METEO_ARCHIVE,
)
from dondeplanto.mock import get_mock_bundle

logger = logging.getLogger(__name__)

_DAILY_FIELDS: str = (
    "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration"
)


def _one_year_window(today_iso: str | None = None) -> tuple[str, str]:
    """Devuelve (start_date, end_date) del último año completo.

    Para tests se puede pasar `today_iso` explícito (YYYY-MM-DD).
    """
    import datetime as _dt

    today = _dt.date.today() if today_iso is None else _dt.date.fromisoformat(today_iso)
    # "Último año completo" = del 1 de enero del año anterior al 31 de
    # diciembre del año anterior. Eso asegura que el dataset esté cerrado.
    end_year = today.year - 1
    return f"{end_year - 1}-01-01", f"{end_year}-12-31"


@lru_cache(maxsize=128)
def _cached_request(
    lat_q: float,
    lon_q: float,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Cachea la respuesta cruda de la Historical Weather API por coords+período."""
    params: dict[str, str] = {
        "latitude": f"{lat_q:.2f}",
        "longitude": f"{lon_q:.2f}",
        "start_date": start_date,
        "end_date": end_date,
        "daily": _DAILY_FIELDS,
        "timezone": "GMT",
    }
    logger.info(
        "Open-Meteo Archive: lat=%.2f lon=%.2f period=%s..%s",
        lat_q,
        lon_q,
        start_date,
        end_date,
    )
    resp = requests.get(OPEN_METEO_ARCHIVE, params=params, timeout=HTTP_TIMEOUT_LONG)
    resp.raise_for_status()
    return cast(dict[str, Any], resp.json())


def _summarize(response: dict[str, Any]) -> dict[str, Any]:
    """Reduce la respuesta de archive a ObservedClimate (spec 2.3)."""
    daily = response.get("daily") or {}
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    precip = daily.get("precipitation_sum") or []
    et = daily.get("et0_fao_evapotranspiration") or []

    def _mean(xs: list[float | None]) -> float | None:
        clean = [float(v) for v in xs if v is not None]
        if not clean:
            return None
        return sum(clean) / len(clean)

    def _sum(xs: list[float | None]) -> float | None:
        clean = [float(v) for v in xs if v is not None]
        if not clean:
            return None
        return float(sum(clean))

    return {
        "obs_temp_max_mean": _mean(tmax),
        "obs_temp_min_mean": _mean(tmin),
        "obs_precip_sum_annual": _sum(precip),
        "obs_evapotranspiration_annual": _sum(et),
        "source": "open_meteo_archive",
    }


def get_observed_climate(
    lat: float,
    lon: float,
    use_mock: bool = False,
    today_iso: str | None = None,
) -> dict[str, Any]:
    """Devuelve ObservedClimate (spec 2.3) desde Historical Weather o mock.

    Args:
        lat, lon: coordenadas (WGS84).
        use_mock: si True, devuelve mock con `source="mock"` sin tocar red.
        today_iso: `"YYYY-MM-DD"` para anclar el "último año completo" (útil
            en tests deterministas).
    """
    if use_mock:
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["observed"]))

    lat_q = round(float(lat), 2)
    lon_q = round(float(lon), 2)
    start, end = _one_year_window(today_iso)
    try:
        payload = _cached_request(lat_q, lon_q, start, end)
    except Exception as exc:  # noqa: BLE001 — degradación controlada
        logger.warning(
            "Open-Meteo Archive: fallo (%.2f, %.2f, %s..%s): %s; cayendo a mock",
            lat_q,
            lon_q,
            start,
            end,
            exc,
        )
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["observed"]))

    return _summarize(payload)


def clear_cache() -> None:
    """Limpia el cache. Solo para tests."""
    _cached_request.cache_clear()


def cache_info() -> Any:
    """Inspección de cache. Solo para tests."""
    return _cached_request.cache_info()


__all__ = ["get_observed_climate", "clear_cache", "cache_info"]

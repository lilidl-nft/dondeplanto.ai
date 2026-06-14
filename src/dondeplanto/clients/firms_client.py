"""Cliente FIRMS (Fire Information for Resource Management System) - F5.

Consulta `config.FIRMS_BASE` con la `FIRMS_MAP_KEY` del entorno para
obtener detecciones de focos activos / anomalías térmicas. Es **historial
de fuego**, NO un modelo de peligrosidad (la app lo aclara en la UI).

Si la key falta, `use_mock=True`, o cualquier error de red, cae a mock.
"""

from __future__ import annotations

import logging
import os
from typing import Any, cast

import requests

from dondeplanto.config import (
    DEFAULT_FIRE_DAYS,
    DEFAULT_FIRE_RADIUS_KM,
    FIRMS_BASE,
    HTTP_TIMEOUT_MEDIUM,
)
from dondeplanto.features.fire_features import fires_to_features
from dondeplanto.mock import get_mock_bundle

logger = logging.getLogger(__name__)

_FIRMS_MAP_KEY_ENV: str = "FIRMS_MAP_KEY"


def _km_to_deg_lat(radius_km: float) -> float:
    """Convierte km a grados de latitud (1° ≈ 111 km)."""
    return radius_km / 111.0


def _km_to_deg_lon(radius_km: float, lat: float) -> float:
    """Convierte km a grados de longitud a la latitud dada (corrección cos)."""
    import math

    cos_lat = max(0.1, math.cos(math.radians(lat)))
    return radius_km / (111.0 * cos_lat)


def _build_firms_url(lat: float, lon: float, radius_km: float, days: int) -> str | None:
    """Construye la URL de FIRMS con bbox. Devuelve None si no hay key."""
    key = os.environ.get(_FIRMS_MAP_KEY_ENV)
    if not key:
        return None
    dlat = _km_to_deg_lat(radius_km)
    dlon = _km_to_deg_lon(radius_km, lat)
    # FIRMS /api/area usa bbox: min_lon,min_lat,max_lon,max_lat
    bbox = f"{lon - dlon:.4f},{lat - dlat:.4f},{lon + dlon:.4f},{lat + dlat:.4f}"
    return f"{FIRMS_BASE}/csv/{key}/MODIS_NRT/{bbox}/{days}"


def _parse_firms_csv(text: str) -> list[dict[str, Any]]:
    """Parsea la respuesta CSV de FIRMS a una lista de dicts.

    FIRMS devuelve CSV con columnas: latitude, longitude, acq_date, ...
    """
    import csv
    from io import StringIO

    reader = csv.DictReader(StringIO(text))
    out: list[dict[str, Any]] = []
    for row in reader:
        # Normalizamos nombres a los que espera fires_to_features.
        lat = row.get("latitude") or row.get("lat")
        lon = row.get("longitude") or row.get("lon")
        acq_date = row.get("acq_date") or row.get("acq_datetime")
        if lat is None or lon is None or acq_date is None:
            continue
        try:
            out.append(
                {
                    "lat": float(lat),
                    "lon": float(lon),
                    "acq_date": str(acq_date),
                },
            )
        except (TypeError, ValueError):
            continue
    return out


def get_fire_activity(
    lat: float,
    lon: float,
    radius_km: float = DEFAULT_FIRE_RADIUS_KM,
    days: int = DEFAULT_FIRE_DAYS,
    use_mock: bool = False,
) -> dict[str, Any]:
    """Devuelve FireFeatures (spec 2.5) desde FIRMS o mock.

    Si `use_mock=True`, no hay `FIRMS_MAP_KEY` en el entorno, o cualquier
    error de red, cae al bundle mock de la provincia con `source="mock"`.
    """
    if use_mock:
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["fire"]))

    url = _build_firms_url(lat, lon, radius_km, days)
    if url is None:
        logger.info(
            "FIRMS_MAP_KEY no configurada; cayendo a mock para (%.2f, %.2f)",
            lat,
            lon,
        )
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["fire"]))

    try:
        resp = requests.get(url, timeout=HTTP_TIMEOUT_MEDIUM)
        resp.raise_for_status()
        raw_fires = _parse_firms_csv(resp.text)
    except Exception as exc:  # noqa: BLE001 — degradación controlada
        logger.warning(
            "FIRMS: fallo de red para (%.2f, %.2f): %s; cayendo a mock",
            lat,
            lon,
            exc,
        )
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["fire"]))

    return fires_to_features(raw_fires, lat, lon, radius_km, source="firms")

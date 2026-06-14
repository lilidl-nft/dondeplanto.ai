"""Cliente Overpass / OpenStreetMap - F5 (logística y cursos de agua).

Consulta `config.OVERPASS` con una query Overpass-QL para obtener
caminos y cursos de agua en un radio. Como Overpass se cae seguido,
el fallback mock es **obligatorio** (lo dice el spec).
"""

from __future__ import annotations

import logging
from typing import Any, cast

import requests

from dondeplanto.config import DEFAULT_LOGISTICS_RADIUS_M, HTTP_TIMEOUT_MEDIUM, OVERPASS
from dondeplanto.mock import get_mock_bundle

logger = logging.getLogger(__name__)


def _build_query(lat: float, lon: float, radius_m: int) -> str:
    """Overpass-QL: ways de highway y waterway dentro del radio."""
    return (
        f"[out:json];"
        f'way(around:{radius_m},{lat},{lon})["highway"];'
        f"out tags;"
        f'way(around:{radius_m},{lat},{lon})["waterway"];'
        f"out tags;"
    )


def _is_primary(highway: str | None) -> bool:
    """Devuelve True si el highway es 'primary' o superior."""
    if not highway:
        return False
    return highway in {
        "primary",
        "primary_link",
        "trunk",
        "trunk_link",
        "motorway",
        "motorway_link",
    }


def _parse_overpass(payload: dict[str, Any]) -> dict[str, int]:
    """Reduce la respuesta de Overpass a contadores simples."""
    elements = payload.get("elements") or []
    road_count = 0
    primary_count = 0
    water_count = 0
    for el in elements:
        tags = el.get("tags") or {}
        if "highway" in tags:
            road_count += 1
            if _is_primary(tags.get("highway")):
                primary_count += 1
        if "waterway" in tags:
            water_count += 1
    return {
        "road_count": road_count,
        "primary_road_count": primary_count,
        "waterway_count": water_count,
    }


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def _raw_to_features(
    parsed: dict[str, int],
    *,
    source: str,
    road_norm: float = 30.0,
    water_norm: float = 10.0,
) -> dict[str, Any]:
    """Convierte contadores crudos a LogisticsFeatures con normalización."""
    accessibility = _clamp(
        (parsed["road_count"] * 0.6 + parsed["primary_road_count"] * 0.4) / road_norm,
    )
    water_access = _clamp(parsed["waterway_count"] / water_norm)
    return {
        "road_count_5km": parsed["road_count"],
        "primary_road_count_10km": parsed["primary_road_count"],
        "waterway_count_5km": parsed["waterway_count"],
        "accessibility_score": accessibility,
        "water_access_score": water_access,
        "source": source,
    }


def get_logistics(
    lat: float,
    lon: float,
    radius_m: int = DEFAULT_LOGISTICS_RADIUS_M,
    use_mock: bool = False,
) -> dict[str, Any]:
    """Devuelve LogisticsFeatures (spec 2.6) desde Overpass o mock.

    Si `use_mock=True` o cualquier error de red/JSON/parseo, cae al
    bundle mock de la provincia con `source="mock"`.
    """
    if use_mock:
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["logistics"]))

    query = _build_query(lat, lon, radius_m)
    try:
        resp = requests.post(OVERPASS, data={"data": query}, timeout=HTTP_TIMEOUT_MEDIUM)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001 — degradación controlada
        logger.warning(
            "Overpass: fallo de red/parseo para (%.2f, %.2f): %s; cayendo a mock",
            lat,
            lon,
            exc,
        )
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["logistics"]))

    try:
        parsed = _parse_overpass(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Overpass: respuesta malformada (%s); cayendo a mock", exc)
        bundle = get_mock_bundle(lat, lon)
        return cast(dict[str, Any], dict(bundle["logistics"]))

    return _raw_to_features(parsed, source="overpass")


__all__ = ["get_logistics"]

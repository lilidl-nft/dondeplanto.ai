"""Orquestador: arma un `FeatureBundle` para una ubicación.

F2 implementa solo la parte de suelo (INTA local) con fallback al módulo
`mock` para el resto. Las features de clima observado, clima futuro,
fuego y logística quedan como TODO con `NotImplementedError("F5")` o se
completan con mock cuando `use_mock=True`, para que la app pueda correr
end-to-end sin red.

`data_quality` se compone a partir de los `source` de cada bloque:
  - `"all_mock"`     → todos los bloques son mock.
  - `"all_real"`     → todos vienen de fuentes reales.
  - `"partial_mock"` → mezcla.
"""

from __future__ import annotations

import logging
from typing import Any

from dondeplanto.clients.inta_local_client import get_soil_aptitude
from dondeplanto.config import PROVINCE_REGION, province_for_point

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers de orquestación
# ---------------------------------------------------------------------------


def _compose_data_quality(sources: list[str]) -> str:
    """Compone `data_quality` a partir de los `source` de cada bloque."""
    has_real = any(s != "mock" for s in sources)
    has_mock = any(s == "mock" for s in sources)
    if has_real and has_mock:
        return "partial_mock"
    if has_real and not has_mock:
        return "all_real"
    return "all_mock"


def _resolve_region(lat: float, lon: float) -> str:
    """Resuelve región a partir de la provincia del punto."""
    province = province_for_point(lat, lon)
    if province is None:
        return "Desconocida"
    return PROVINCE_REGION.get(province, "Desconocida")


def _build_soil(lat: float, lon: float, use_mock: bool) -> dict[str, Any]:
    """SoilFeatures: cliente INTA local o mock."""
    return get_soil_aptitude(lat, lon, use_mock=use_mock)


def _build_observed(lat: float, lon: float, use_mock: bool) -> dict[str, Any]:
    """ObservedClimate. F5: cliente Open-Meteo Archive con fallback a mock."""
    from dondeplanto.clients.open_meteo_observed_client import get_observed_climate

    return get_observed_climate(lat, lon, use_mock=use_mock)


def _build_future(lat: float, lon: float, use_mock: bool) -> dict[str, Any]:
    """FutureClimate. F4: cliente Open-Meteo Climate con fallback a mock."""
    # Import local para evitar import circular
    from dondeplanto.clients.open_meteo_climate_client import get_climate_delta

    return get_climate_delta(lat, lon, use_mock=use_mock)


def _build_fire(lat: float, lon: float, use_mock: bool) -> dict[str, Any]:
    """FireFeatures. F5: cliente FIRMS con fallback a mock (sin key -> mock)."""
    from dondeplanto.clients.firms_client import get_fire_activity

    return get_fire_activity(lat, lon, use_mock=use_mock)


def _build_logistics(lat: float, lon: float, use_mock: bool) -> dict[str, Any]:
    """LogisticsFeatures. F5: cliente Overpass con fallback a mock obligatorio."""
    from dondeplanto.clients.overpass_client import get_logistics

    return get_logistics(lat, lon, use_mock=use_mock)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def build_features(location: dict[str, Any], use_mock: bool = False) -> dict[str, Any]:
    """Arma el FeatureBundle para `location` orquestando los clientes.

    Args:
        location: dict con al menos `lat` y `lon`. Sigue la sección 7.1 del
            spec. Otros campos (`climate_model`, `baseline_period`,
            `future_period`) se completan con defaults si faltan.
        use_mock: si True, fuerza fallback mock para los bloques que aún
            no tienen cliente real (clima, fuego, logística).

    Returns:
        FeatureBundle (sección 2.7 del spec) con `data_quality` compuesto.
    """
    lat = float(location["lat"])
    lon = float(location["lon"])

    full_location: dict[str, Any] = {
        "lat": lat,
        "lon": lon,
        "climate_model": location.get("climate_model", "ensemble"),
        "baseline_period": location.get("baseline_period", "1991-2020"),
        "future_period": location.get("future_period", "2041-2060"),
    }

    soil = _build_soil(lat, lon, use_mock)
    observed = _build_observed(lat, lon, use_mock)
    future = _build_future(lat, lon, use_mock)
    fire = _build_fire(lat, lon, use_mock)
    logistics = _build_logistics(lat, lon, use_mock)

    sources = [
        soil["source"],
        observed["source"],
        future["source"],
        fire["source"],
        logistics["source"],
    ]
    bundle: dict[str, Any] = {
        "location": full_location,
        "soil": soil,
        "observed": observed,
        "future": future,
        "fire": fire,
        "logistics": logistics,
        "region": _resolve_region(lat, lon),
        "data_quality": _compose_data_quality(sources),
    }
    return bundle

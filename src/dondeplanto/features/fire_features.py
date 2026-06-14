"""Funciones puras: lista cruda de focos FIRMS -> FireFeatures (spec 2.5)."""

from __future__ import annotations

import math
from typing import Any

_EARTH_RADIUS_KM: float = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia geodésica entre dos puntos en km.

    Usa la fórmula de Haversine sobre la esfera. Suficiente para las
    distancias chicas que maneja FIRMS (< 100 km).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return _EARTH_RADIUS_KM * c


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def fires_to_features(
    raw_fires: list[dict[str, Any]],
    center_lat: float,
    center_lon: float,
    radius_km: float,
    *,
    now_ts: float | None = None,
    source: str = "firms",
) -> dict[str, Any]:
    """Reduce la lista cruda de focos FIRMS al contrato FireFeatures.

    Args:
        raw_fires: lista de dicts con keys `lat`, `lon` y `acq_date` (ISO)
            o `acq_datetime`. Cualquier item sin esos campos se ignora.
        center_lat, center_lon: punto central del radio.
        radius_km: radio de búsqueda.
        now_ts: timestamp epoch (segundos) para "ahora". Si None, todos los
            focos se cuentan como históricos (>= 365d). En tests se puede
            fijar un valor determinístico.
        source: `"firms"` o `"mock"` para propagar al output.

    Returns:
        FireFeatures (spec 2.5). `fire_activity_score` es un proxy simple
        basado en la cuenta de focos, NO un modelo de riesgo.
    """
    import datetime as _dt

    if now_ts is None:
        # Si no se pasa reloj, todos cuentan como históricos (>= 365d).
        # Para producción el cliente FIRMS pasa el ts actual.
        now = _dt.datetime.now(tz=_dt.UTC)
    else:
        now = _dt.datetime.fromtimestamp(now_ts, tz=_dt.UTC)

    count_30d = 0
    count_365d = 0
    nearest_km: float | None = None

    for fire in raw_fires:
        lat = fire.get("lat")
        lon = fire.get("lon")
        date_str = fire.get("acq_date") or fire.get("acq_datetime")
        if lat is None or lon is None or date_str is None:
            continue
        d_km = haversine_km(center_lat, center_lon, float(lat), float(lon))
        if d_km > radius_km:
            continue
        try:
            if isinstance(date_str, str) and len(date_str) >= 10:
                fire_dt = _dt.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                continue
        except (TypeError, ValueError):
            continue
        if fire_dt.tzinfo is None:
            fire_dt = fire_dt.replace(tzinfo=_dt.UTC)

        age_days = (now - fire_dt).days
        if age_days <= 365:
            count_365d += 1
        if age_days <= 30:
            count_30d += 1
        if nearest_km is None or d_km < nearest_km:
            nearest_km = d_km

    # Proxy simple de actividad reciente: pondera 30d más fuerte que 365d.
    # 50 focos en 30d → score ~ 1.0; ~17 en 365d → ~ 1.0 también.
    score = _clamp((count_30d * 0.7 + count_365d * 0.3) / 50.0)

    return {
        "fire_count_30d": count_30d,
        "fire_count_365d": count_365d,
        "distance_to_nearest_fire_km": nearest_km,
        "fire_activity_score": score,
        "source": source,
    }

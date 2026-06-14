"""Mock de datos para que la app corra end-to-end sin red ni INTA real.

Cada función devuelve un FeatureBundle plausible para la coordenada dada.
Los datos NO son reales: están marcados con `source=\"mock\"` y se propagan
al campo `data_quality` del bundle.
"""

from __future__ import annotations

from typing import Any

from dondeplanto.config import DEMO_LOCATIONS, PROVINCE_REGION, province_for_point


def _soil_mock(province: str | None) -> dict[str, Any]:
    """Devuelve SoilFeatures plausibles por provincia."""
    if province == "corrientes":
        return {
            "soil_series": "Corrientes-litoral-A",
            "soil_capability_class": "IIIs",
            "soil_productivity_index": 62.0,
            "soil_drainage_class": "bien drenado",
            "soil_forestry_aptitude": "Alta",
            "soil_aptitude_score": 0.85,
            "waterlogging_risk": 0.10,
            "inta_coverage": True,
            "source": "mock",
        }
    if province == "misiones":
        return {
            "soil_series": "Misiones-rojo-profundo",
            "soil_capability_class": "IIs",
            "soil_productivity_index": 75.0,
            "soil_drainage_class": "bien drenado",
            "soil_forestry_aptitude": "Alta",
            "soil_aptitude_score": 0.92,
            "waterlogging_risk": 0.10,
            "inta_coverage": True,
            "source": "mock",
        }
    if province == "entre_rios":
        return {
            "soil_series": "EntreRios-vertisol-plano",
            "soil_capability_class": "IVw",
            "soil_productivity_index": 45.0,
            "soil_drainage_class": "imperfectamente drenado",
            "soil_forestry_aptitude": "Media",
            "soil_aptitude_score": 0.55,
            "waterlogging_risk": 0.60,
            "inta_coverage": True,
            "source": "mock",
        }
    # fallback fuera de cobertura
    return {
        "soil_series": None,
        "soil_capability_class": None,
        "soil_productivity_index": None,
        "soil_drainage_class": "desconocido",
        "soil_forestry_aptitude": "desconocida",
        "soil_aptitude_score": 0.40,
        "waterlogging_risk": 0.40,
        "inta_coverage": False,
        "source": "mock",
    }


def _observed_mock(province: str | None) -> dict[str, Any]:
    if province == "corrientes":
        return {
            "obs_temp_max_mean": 27.8,
            "obs_temp_min_mean": 16.4,
            "obs_precip_sum_annual": 1380.0,
            "obs_evapotranspiration_annual": 1010.0,
            "source": "mock",
        }
    if province == "misiones":
        return {
            "obs_temp_max_mean": 27.2,
            "obs_temp_min_mean": 17.0,
            "obs_precip_sum_annual": 1820.0,
            "obs_evapotranspiration_annual": 980.0,
            "source": "mock",
        }
    if province == "entre_rios":
        return {
            "obs_temp_max_mean": 25.4,
            "obs_temp_min_mean": 14.1,
            "obs_precip_sum_annual": 1180.0,
            "obs_evapotranspiration_annual": 940.0,
            "source": "mock",
        }
    return {
        "obs_temp_max_mean": 25.0,
        "obs_temp_min_mean": 14.0,
        "obs_precip_sum_annual": 1100.0,
        "obs_evapotranspiration_annual": 950.0,
        "source": "mock",
    }


def _future_mock(province: str | None) -> dict[str, Any]:
    """Delta 2041-2060 vs 1991-2020 (mismo modelo, ensemble)."""
    if province == "corrientes":
        return {
            "baseline_temp_max_mean": 27.8,
            "future_temp_max_mean": 29.4,
            "temp_max_delta": 1.6,
            "baseline_precip_sum": 1380.0,
            "future_precip_sum": 1290.0,
            "precip_delta_pct": -6.5,
            "water_stress_future": 0.46,
            "ensemble_spread": 0.4,
            "source": "mock",
        }
    if province == "misiones":
        return {
            "baseline_temp_max_mean": 27.2,
            "future_temp_max_mean": 28.7,
            "temp_max_delta": 1.5,
            "baseline_precip_sum": 1820.0,
            "future_precip_sum": 1740.0,
            "precip_delta_pct": -4.4,
            "water_stress_future": 0.40,
            "ensemble_spread": 0.3,
            "source": "mock",
        }
    if province == "entre_rios":
        return {
            "baseline_temp_max_mean": 25.4,
            "future_temp_max_mean": 27.2,
            "temp_max_delta": 1.8,
            "baseline_precip_sum": 1180.0,
            "future_precip_sum": 1075.0,
            "precip_delta_pct": -8.9,
            "water_stress_future": 0.56,
            "ensemble_spread": 0.5,
            "source": "mock",
        }
    return {
        "baseline_temp_max_mean": 25.0,
        "future_temp_max_mean": 27.0,
        "temp_max_delta": 2.0,
        "baseline_precip_sum": 1100.0,
        "future_precip_sum": 1000.0,
        "precip_delta_pct": -9.1,
        "water_stress_future": 0.58,
        "ensemble_spread": 0.5,
        "source": "mock",
    }


def _fire_mock(province: str | None) -> dict[str, Any]:
    if province == "corrientes":
        return {
            "fire_count_30d": 4,
            "fire_count_365d": 22,
            "distance_to_nearest_fire_km": 9.2,
            "fire_activity_score": 0.52,
            "source": "mock",
        }
    if province == "misiones":
        return {
            "fire_count_30d": 2,
            "fire_count_365d": 11,
            "distance_to_nearest_fire_km": 14.6,
            "fire_activity_score": 0.30,
            "source": "mock",
        }
    if province == "entre_rios":
        return {
            "fire_count_30d": 1,
            "fire_count_365d": 6,
            "distance_to_nearest_fire_km": 21.0,
            "fire_activity_score": 0.18,
            "source": "mock",
        }
    return {
        "fire_count_30d": 0,
        "fire_count_365d": 0,
        "distance_to_nearest_fire_km": None,
        "fire_activity_score": 0.0,
        "source": "mock",
    }


def _logistics_mock(province: str | None) -> dict[str, Any]:
    if province == "corrientes":
        return {
            "road_count_5km": 14,
            "primary_road_count_10km": 2,
            "waterway_count_5km": 3,
            "accessibility_score": 0.72,
            "water_access_score": 0.55,
            "source": "mock",
        }
    if province == "misiones":
        return {
            "road_count_5km": 9,
            "primary_road_count_10km": 1,
            "waterway_count_5km": 4,
            "accessibility_score": 0.58,
            "water_access_score": 0.65,
            "source": "mock",
        }
    if province == "entre_rios":
        return {
            "road_count_5km": 18,
            "primary_road_count_10km": 3,
            "waterway_count_5km": 5,
            "accessibility_score": 0.80,
            "water_access_score": 0.70,
            "source": "mock",
        }
    return {
        "road_count_5km": 0,
        "primary_road_count_10km": 0,
        "waterway_count_5km": 0,
        "accessibility_score": 0.30,
        "water_access_score": 0.30,
        "source": "mock",
    }


def _compose_data_quality(sources: list[str]) -> str:
    """Compone data_quality a partir de los source de cada bloque."""
    has_real = any(s != "mock" for s in sources)
    has_mock = any(s == "mock" for s in sources)
    if has_real and has_mock:
        return "partial_mock"
    if has_real and not has_mock:
        return "all_real"
    return "all_mock"


def get_mock_bundle(lat: float, lon: float) -> dict[str, Any]:
    """Devuelve un FeatureBundle plausible para (lat, lon) sin tocar red."""
    province = province_for_point(lat, lon)
    region = PROVINCE_REGION.get(province or "", "Desconocida")

    soil = _soil_mock(province)
    obs = _observed_mock(province)
    fut = _future_mock(province)
    fire = _fire_mock(province)
    logi = _logistics_mock(province)

    location = {
        "lat": lat,
        "lon": lon,
        "climate_model": "ensemble",
        "baseline_period": "1991-2020",
        "future_period": "2041-2060",
    }

    return {
        "location": location,
        "soil": soil,
        "observed": obs,
        "future": fut,
        "fire": fire,
        "logistics": logi,
        "region": region,
        "data_quality": _compose_data_quality(
            [soil["source"], obs["source"], fut["source"], fire["source"], logi["source"]],
        ),
    }


def get_all_demo_bundles() -> dict[str, dict[str, Any]]:
    """Devuelve un bundle por cada demo location. Útil para F1."""
    return {name: get_mock_bundle(lat, lon) for name, (lat, lon) in DEMO_LOCATIONS.items()}

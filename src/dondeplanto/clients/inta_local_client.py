"""Cliente INTA local: point-in-polygon offline sobre GeoPackage provincial.

Carga el GeoPackage de la provincia que contiene el punto (por bbox usando
`config.province_for_point` y `config.gpkg_path_for_province`), busca el
polígono y mapea los atributos al contrato `SoilFeatures` (sección 2.2
del build spec) mediante `features.soil_features.raw_to_soil_features`.

Si el punto cae fuera de cobertura (sin provincia o sin polígono que lo
contenga) marca `inta_coverage=False` y cae al módulo `mock`.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import geopandas as gpd
from shapely.geometry import Point

from dondeplanto.config import gpkg_path_for_province, province_for_point
from dondeplanto.features.soil_features import raw_to_soil_features
from dondeplanto.mock import get_mock_bundle

logger = logging.getLogger(__name__)

# CRS esperado para los GeoPackages provinciales.
_EXPECTED_CRS: str = "EPSG:4326"


@lru_cache(maxsize=8)
def _load_province_gpkg(province: str) -> gpd.GeoDataFrame:
    """Carga (y cachea) el GeoPackage de una provincia.

    Se cachea a nivel de módulo porque la lectura es costosa y los archivos
    no cambian durante una corrida. El `lru_cache` evita releer cuando hay
    varias consultas seguidas en la misma provincia.
    """
    path = gpkg_path_for_province(province)
    logger.info("Cargando GeoPackage INTA: %s", path)
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        # Asumimos WGS84 si el archivo no trae CRS declarado.
        gdf = gdf.set_crs(_EXPECTED_CRS)
    elif str(gdf.crs).upper() != _EXPECTED_CRS:
        gdf = gdf.to_crs(_EXPECTED_CRS)
    return gdf


def _fallback_soil(lat: float, lon: float) -> dict[str, Any]:
    """Devuelve un SoilFeatures mock para (lat, lon)."""
    bundle = get_mock_bundle(lat, lon)
    return dict(bundle["soil"])


def get_soil_aptitude(lat: float, lon: float, use_mock: bool = False) -> dict[str, Any]:
    """Devuelve SoilFeatures para (lat, lon) desde el cache local de INTA.

    Comportamiento:
      - Si `use_mock=True` o la coord cae fuera de cobertura, devuelve
        SoilFeatures mock (`source="mock"`, `inta_coverage=False` si
        está fuera).
      - Si la coord cae dentro del bbox de una provincia demo, hace
        point-in-polygon sobre el GeoPackage correspondiente.
      - Si la provincia no está en el bbox o el punto no toca ningún
        polígono, marca `inta_coverage=False` y cae a mock.

    Nunca lanza excepciones hacia arriba: cualquier error de I/O o geometría
    degrada a mock y se loguea como warning.
    """
    if use_mock:
        return _fallback_soil(lat, lon)

    province = province_for_point(lat, lon)
    if province is None:
        logger.info("Coordenada (%.4f, %.4f) fuera de cobertura INTA demo", lat, lon)
        return _fallback_soil(lat, lon)

    try:
        gdf = _load_province_gpkg(province)
    except FileNotFoundError:
        logger.warning("GeoPackage ausente para provincia %s; cayendo a mock", province)
        return _fallback_soil(lat, lon)
    except Exception as exc:  # noqa: BLE001 — degradación controlada a mock
        logger.warning("Error leyendo GeoPackage %s: %s; cayendo a mock", province, exc)
        return _fallback_soil(lat, lon)

    try:
        point = Point(lon, lat)  # shapely: (x=lon, y=lat)
        matches = gdf[gdf.geometry.intersects(point)]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error en point-in-polygon para (%.4f, %.4f): %s", lat, lon, exc)
        return _fallback_soil(lat, lon)

    if matches.empty:
        logger.info(
            "Punto (%.4f, %.4f) en bbox de %s pero sin polígono; cayendo a mock",
            lat,
            lon,
            province,
        )
        return _fallback_soil(lat, lon)

    # Tomamos el primer polígono que intersecta. En el dataset mock la
    # grilla no se superpone, así que el match es único. Si en datos
    # reales apareciera superposición, documentar la política acá.
    row = matches.iloc[0].drop("geometry").to_dict()
    features = raw_to_soil_features(row, source="inta_local", inta_coverage=True)
    return features

"""Tests smoke de F1: config + mock data + GeoPackages generados."""

from __future__ import annotations

import geopandas as gpd
import pytest

from dondeplanto.config import (
    CLIMATE_MODELS,
    DEMO_LOCATIONS,
    PROVINCE_BBOX,
    province_for_point,
)
from dondeplanto.mock import get_all_demo_bundles, get_mock_bundle
from dondeplanto.mock.generate_inta_mock import SCHEMA_COLUMNS


def test_config_province_bboxes_are_valid() -> None:
    """Cada bbox tiene lat_min < lat_max y lon_min < lon_max."""
    for name, (lat_min, lat_max, lon_min, lon_max) in PROVINCE_BBOX.items():
        assert lat_min < lat_max, f"{name}: lat_min >= lat_max"
        assert lon_min < lon_max, f"{name}: lon_min >= lon_max"
        assert -90 <= lat_min <= 90
        assert -90 <= lat_max <= 90
        assert -180 <= lon_min <= 180
        assert -180 <= lon_max <= 180


def test_config_demos_are_within_their_province_bbox() -> None:
    """Cada demo location cae dentro del bbox de su provincia."""
    for name, (lat, lon) in DEMO_LOCATIONS.items():
        province = province_for_point(lat, lon)
        assert province is not None, f"{name} no cae en ninguna provincia"
        lat_min, lat_max, lon_min, lon_max = PROVINCE_BBOX[province]
        assert lat_min <= lat <= lat_max
        assert lon_min <= lon <= lon_max


def test_config_climate_models_not_empty() -> None:
    assert len(CLIMATE_MODELS) >= 2
    for m in CLIMATE_MODELS:
        assert isinstance(m, str)
        assert m  # no vacío


def test_province_for_point_outside_coverage() -> None:
    """Una coord en la cordillera no cae en ninguna provincia demo."""
    assert province_for_point(-32.0, -69.0) is None


@pytest.mark.parametrize("name", list(DEMO_LOCATIONS.keys()))
def test_mock_bundle_for_demo_has_all_blocks(name: str) -> None:
    """Cada demo devuelve bundle completo con todos los bloques requeridos."""
    lat, lon = DEMO_LOCATIONS[name]
    bundle = get_mock_bundle(lat, lon)

    for key in (
        "location",
        "soil",
        "observed",
        "future",
        "fire",
        "logistics",
        "region",
        "data_quality",
    ):
        assert key in bundle, f"falta {key} en bundle de {name}"

    assert bundle["location"]["lat"] == lat
    assert bundle["location"]["lon"] == lon
    assert bundle["soil"]["inta_coverage"] is True
    assert bundle["soil"]["source"] == "mock"
    assert bundle["future"]["temp_max_delta"] > 0
    assert bundle["data_quality"] in {"all_mock", "partial_mock", "all_real"}


def test_get_all_demo_bundles_returns_all_three() -> None:
    bundles = get_all_demo_bundles()
    assert set(bundles.keys()) == set(DEMO_LOCATIONS.keys())
    assert len(bundles) == 3


def test_mock_bundle_outside_coverage_marks_uncovered() -> None:
    """Una coord fuera de las 3 provincias devuelve inta_coverage=False."""
    bundle = get_mock_bundle(-32.0, -69.0)  # Mendoza
    assert bundle["soil"]["inta_coverage"] is False
    assert bundle["region"] == "Desconocida"


def test_inta_gpkg_files_exist_and_have_schema() -> None:
    """Los GeoPackages mock commiteados existen y respetan el schema."""
    from dondeplanto.config import gpkg_path_for_province

    for province in PROVINCE_BBOX:
        path = gpkg_path_for_province(province)
        if not path.exists():
            pytest.skip(
                f"{path} no existe; corré `uv run python -m dondeplanto.mock.generate_inta_mock`"
            )
        gdf = gpd.read_file(path)
        assert len(gdf) > 0
        for col in SCHEMA_COLUMNS:
            assert col in gdf.columns, f"falta columna {col} en {path.name}"
        assert gdf.crs is not None


def test_gpkg_path_for_province_raises_on_unknown() -> None:
    from dondeplanto.config import gpkg_path_for_province

    with pytest.raises(ValueError, match="provincia desconocida"):
        gpkg_path_for_province("mendoza")

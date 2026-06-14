"""Configuración central: endpoints, radios, períodos, modelos, bboxes de provincias.

Toda constante compartida vive acá. No contiene lógica. Si un módulo necesita
algo, lo importa de acá (no redeclarar).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
INTA_DATA_DIR: Final[Path] = DATA_DIR / "inta"
SPECIES_PROFILES_PATH: Final[Path] = DATA_DIR / "species_profiles.yaml"
MOCK_LOCATIONS_PATH: Final[Path] = DATA_DIR / "mock_locations.json"
INTA_README_PATH: Final[Path] = INTA_DATA_DIR / "README_inta_data.md"

# ---------------------------------------------------------------------------
# Endpoints externos
# ---------------------------------------------------------------------------

OPEN_METEO_CLIMATE: Final[str] = "https://climate-api.open-meteo.com/v1/climate"
OPEN_METEO_FORECAST: Final[str] = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE: Final[str] = "https://archive-api.open-meteo.com/v1/archive"
OVERPASS: Final[str] = "https://overpass-api.de/api/interpreter"
FIRMS_BASE: Final[str] = "https://firms.modaps.eosdis.nasa.gov/api/area"
GEOINTA_WFS: Final[str] = "https://geointa.inta.gob.ar/geoserver/wfs"

# ---------------------------------------------------------------------------
# Períodos climáticos
# ---------------------------------------------------------------------------

BASELINE_PERIOD: Final[tuple[str, str]] = ("1991-01-01", "2020-12-31")
FUTURE_PERIOD: Final[tuple[str, str]] = ("2041-01-01", "2060-12-31")

# Modelos climáticos (CMIP6 / HighResMIP, Open-Meteo Climate API).
# Antes de 2050 la API no separa escenarios; estos modelos están aproximadamente
# en RCP8.5 y muestran la incertidumbre vía ensemble.
CLIMATE_MODELS: Final[tuple[str, ...]] = (
    "CMCC_CM2_VHR4",
    "MRI_AGCM3_2_S",
    "EC_Earth3P_HR",
    "MPI_ESM1_2_XR",
)

# Radios por defecto para clientes geográficos.
DEFAULT_FIRE_RADIUS_KM: Final[int] = 25
DEFAULT_FIRE_DAYS: Final[int] = 365
DEFAULT_LOGISTICS_RADIUS_M: Final[int] = 5000

# Timeouts HTTP (segundos).
HTTP_TIMEOUT_SHORT: Final[int] = 10
HTTP_TIMEOUT_MEDIUM: Final[int] = 30
HTTP_TIMEOUT_LONG: Final[int] = 60

# ---------------------------------------------------------------------------
# Bounding boxes (lat_min, lat_max, lon_min, lon_max) de provincias demo
# ---------------------------------------------------------------------------

PROVINCE_BBOX: Final[dict[str, tuple[float, float, float, float]]] = {
    "corrientes": (-30.75, -27.20, -59.80, -55.60),
    "entre_rios": (-34.05, -30.10, -60.80, -57.80),
    "misiones": (-28.20, -25.50, -56.10, -53.60),
}

# ---------------------------------------------------------------------------
# Ubicaciones demo calibradas para mostrar contrastes del modelo de 2 capas
# ---------------------------------------------------------------------------

DEMO_LOCATIONS: Final[dict[str, tuple[float, float]]] = {
    "Corrientes (Santo Tomé)": (-28.55, -56.05),
    "Entre Ríos (Concordia)": (-31.39, -58.02),
    "Misiones (Oberá)": (-27.49, -55.12),
}

# ---------------------------------------------------------------------------
# Regiones (para mostrar al usuario)
# ---------------------------------------------------------------------------

PROVINCE_REGION: Final[dict[str, str]] = {
    "corrientes": "NEA / Litoral",
    "entre_rios": "NEA / Litoral",
    "misiones": "NEA / Litoral",
}


def province_for_point(lat: float, lon: float) -> str | None:
    """Devuelve la clave de provincia que contiene (lat, lon) o None si cae fuera.

    Sirve para elegir qué GeoPackage cargar en `inta_local_client`.
    """
    for name, (lat_min, lat_max, lon_min, lon_max) in PROVINCE_BBOX.items():
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    return None


def gpkg_path_for_province(province: str) -> Path:
    """Devuelve la ruta al GeoPackage de INTA para una provincia."""
    if province not in PROVINCE_BBOX:
        raise ValueError(f"provincia desconocida: {province!r}")
    return INTA_DATA_DIR / f"{province}_suelos.gpkg"

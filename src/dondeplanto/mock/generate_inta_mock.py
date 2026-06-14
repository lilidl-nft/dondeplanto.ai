"""Genera GeoPackages mock para que la app corra end-to-end sin descarga INTA.

Para cada provincia demo crea un grid de N×N polígonos sobre su bbox con
atributos sintéticos plausibles. Si F2 reemplaza estos GeoPackages con
los reales, la app sigue funcionando porque respeta el mismo schema.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

from dondeplanto.config import INTA_DATA_DIR, PROVINCE_BBOX

# Schema de columnas que `inta_local_client` espera (ver docs/inta_integration.md).
SCHEMA_COLUMNS: list[str] = [
    "soil_series",
    "soil_capability_class",
    "soil_productivity_index",
    "soil_drainage_class",
    "soil_forestry_aptitude",
    "soil_aptitude_score",
    "waterlogging_risk",
    "source",
]

DRAINAGE_CLASSES: list[str] = [
    "excesivamente drenado",
    "bien drenado",
    "moderadamente bien drenado",
    "imperfectamente drenado",
    "pobremente drenado",
]

FORESTRY_APTITUDES: list[str] = ["Alta", "Media", "Baja", "Marginal"]


def _drainage_to_risk(drainage: str) -> float:
    """Mapea clase de drenaje a waterlogging_risk (tabla 5.4 del spec)."""
    return {
        "excesivamente drenado": 0.10,
        "bien drenado": 0.10,
        "moderadamente bien drenado": 0.30,
        "imperfectamente drenado": 0.60,
        "pobremente drenado": 0.85,
    }.get(drainage, 0.40)


def _aptitude_to_score(apt: str) -> float:
    """Mapea soil_forestry_aptitude a soil_aptitude_score."""
    return {
        "Alta": 0.85,
        "Media": 0.60,
        "Baja": 0.35,
        "Marginal": 0.15,
    }.get(apt, 0.40)


def _build_grid(province: str, n: int, seed: int) -> gpd.GeoDataFrame:
    """Construye un grid de N×N polígonos sobre el bbox de la provincia."""
    lat_min, lat_max, lon_min, lon_max = PROVINCE_BBOX[province]
    rng = np.random.default_rng(seed)

    lat_step = (lat_max - lat_min) / n
    lon_step = (lon_max - lon_min) / n

    rows: list[dict[str, object]] = []
    geoms: list[Polygon] = []

    for i in range(n):
        for j in range(n):
            lat0 = lat_min + i * lat_step
            lat1 = lat0 + lat_step
            lon0 = lon_min + j * lon_step
            lon1 = lon0 + lon_step
            geoms.append(Polygon([(lon0, lat0), (lon1, lat0), (lon1, lat1), (lon0, lat1)]))

            # Atributos sintéticos con distribución creíble.
            drainage = DRAINAGE_CLASSES[rng.integers(0, len(DRAINAGE_CLASSES))]
            # Sesgo: en Misiones predominan los bien drenados; en Entre Ríos los
            # imperfectos (Vertisoles); Corrientes queda intermedio.
            if province == "misiones" and rng.random() < 0.7:
                drainage = "bien drenado"
            elif province == "entre_rios" and rng.random() < 0.6:
                drainage = "imperfectamente drenado"
            elif province == "corrientes" and rng.random() < 0.5:
                drainage = "bien drenado"

            apt = FORESTRY_APTITUDES[rng.integers(0, len(FORESTRY_APTITUDES))]
            if province == "misiones" and rng.random() < 0.7:
                apt = "Alta"
            if province == "entre_rios" and rng.random() < 0.6:
                apt = rng.choice(["Media", "Baja"])

            productivity = float(rng.uniform(20, 95))
            capability = rng.choice(["IIs", "IIIs", "IVs", "IVw", "Vw"])
            series = f"{province}-synth-{i:02d}-{j:02d}"

            rows.append(
                {
                    "soil_series": series,
                    "soil_capability_class": capability,
                    "soil_productivity_index": round(productivity, 1),
                    "soil_drainage_class": drainage,
                    "soil_forestry_aptitude": apt,
                    "soil_aptitude_score": _aptitude_to_score(apt),
                    "waterlogging_risk": _drainage_to_risk(drainage),
                    "source": "inta_local",
                },
            )

    gdf = gpd.GeoDataFrame(rows, geometry=geoms, crs="EPSG:4326")
    return gdf


def generate_all(n: int = 8, seed: int = 42, output_dir: Path | None = None) -> list[Path]:
    """Genera los GeoPackages mock para todas las provincias demo.

    Returns la lista de paths creados.
    """
    out = output_dir or INTA_DATA_DIR
    out.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    for idx, province in enumerate(PROVINCE_BBOX):
        gdf = _build_grid(province, n=n, seed=seed + idx)
        path = out / f"{province}_suelos.gpkg"
        gdf.to_file(path, driver="GPKG", layer="suelos")
        created.append(path)
        print(f"  ✓ {path.name}: {len(gdf)} polígonos")
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera GeoPackages mock de INTA.")
    parser.add_argument("--n", type=int, default=8, help="Resolución de grilla (NxN)")
    parser.add_argument("--seed", type=int, default=42, help="Seed aleatoria")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Directorio de salida (default: data/inta/)",
    )
    args = parser.parse_args()

    print(f"Generando GeoPackages mock (n={args.n}, seed={args.seed})...")
    created = generate_all(n=args.n, seed=args.seed, output_dir=args.out)
    print(f"\n{len(created)} archivos creados en {created[0].parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

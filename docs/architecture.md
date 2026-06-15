# Architecture

dondeplanto.ai es una app Streamlit + FastAPI con arquitectura en capas. La separación
de responsabilidades es estricta: cada capa tiene un solo rol y los contratos de datos
están fijos (ver `../spec/seccion 2.md` o el build spec sección 2).

```
Streamlit UI  (:8501)         FastAPI  (:8000)
     ↓                             ↓
  build_features → recommend → explain → report
     ↓
 clients/  ← INTA local, Open-Meteo, FIRMS, Overpass  (todos con mock)
     ↓
 features/ ← soil, climate, fire, logistics
     ↓
 scoring/  ← membership, site_scoring, species_matching, recommendation
     ↓
 data/     ← species_profiles.yaml, inta/{corrientes,entre_rios,misiones}_suelos.gpkg
```

## Capas

### 1. UI (`app.py` + `src/dondeplanto/api/`)
- **Streamlit** en `:8501` (`uv run streamlit run app.py`).
- **FastAPI** en `:8000` (`uv run uvicorn dondeplanto.api.app:app --port 8000 --reload`).
- Los dos son procesos separados. El frontend de Streamlit consume la API
  vía HTTP si se quiere, pero la implementación actual es local.

### 2. Orquestación (`src/dondeplanto/features/feature_builder.py`)
- `build_features(location, use_mock=False) -> FeatureBundle`
- Compone los 5 bloques del FeatureBundle (soil, observed, future, fire, logistics).
- Componer `data_quality` a partir de los `source` de cada bloque.

### 3. Clientes (`src/dondeplanto/clients/`)
Cada cliente tiene la misma firma `get_xxx(lat, lon, use_mock=False) -> dict`:

| Cliente | Endpoint | Fallback |
|---|---|---|
| `inta_local_client` | `data/inta/<prov>_suelos.gpkg` | mock si fuera de cobertura |
| `inta_wfs_client` | `config.GEOINTA_WFS` | `None` ante error (caller degrada) |
| `open_meteo_climate_client` | `config.OPEN_METEO_CLIMATE` | mock ante timeout/error |
| `open_meteo_observed_client` | `config.OPEN_METEO_ARCHIVE` | mock ante timeout/error |
| `firms_client` | `config.FIRMS_BASE` (requiere key) | mock si no hay key o error |
| `overpass_client` | `config.OVERPASS` | mock obligatorio (Overpass se cae) |

Mock-first: cualquier excepción → mock con `source="mock"`. La app nunca se rompe
por una fuente caída.

### 4. Features (`src/dondeplanto/features/`)
Funciones puras (sin I/O) que reducen respuestas crudas a los contratos:
- `soil_features.py`: drainage → waterlogging_risk, forestry_aptitude → soil_aptitude_score.
- `climate_features.py`: anual-iza responses, calcula deltas, water_stress_future.
- `fire_features.py`: haversine + cuenta de focos, score proxy.
- (logistics está embebido en el cliente `overpass_client`).

### 5. Scoring (`src/dondeplanto/scoring/`)
Funciones puras que implementan el modelo de dos capas (spec sección 5):
- `membership.py`: trapezoidal puro.
- `site_scoring.py`: water_stress_future, environmental_risk, site_aptitude.
- `species_matching.py`: species_climate_fit, species_fit_future (con drought_tolerance).
- `recommendation.py`: rank_species, recommend.
- `species_profiles.py`: load_profiles() con lru_cache.

### 6. Explicación (`src/dondeplanto/explanation/`)
- `explainer.py`: texto determinístico en español.
- `report_generator.py`: reporte Markdown descargable.

### 7. Data (`data/`)
- `species_profiles.yaml`: 3 especies comerciales con rangos trapezoidales.
- `inta/{corrientes,entre_rios,misiones}_suelos.gpkg`: GeoPackages precargados
  (mock en F1, reemplazables con WFS real en F+ según sección 10 del spec).
- `mock_locations.json`: metadata de las 3 demos.

## Contratos de datos (spec sección 2)

Cada capa produce/consume los siguientes diccionarios. Las **keys son fijas** y
son la interfaz entre módulos:

- `LocationInput`: lat, lon, climate_model, baseline_period, future_period
- `SoilFeatures`: soil_series, soil_capability_class, soil_productivity_index, soil_drainage_class, soil_forestry_aptitude, soil_aptitude_score, waterlogging_risk, inta_coverage, source
- `ObservedClimate`: obs_temp_max_mean, obs_temp_min_mean, obs_precip_sum_annual, obs_evapotranspiration_annual, source
- `FutureClimate`: baseline_temp_max_mean, future_temp_max_mean, temp_max_delta, baseline_precip_sum, future_precip_sum, precip_delta_pct, water_stress_future, ensemble_spread, source
- `FireFeatures`: fire_count_30d, fire_count_365d, distance_to_nearest_fire_km, fire_activity_score, source
- `LogisticsFeatures`: road_count_5km, primary_road_count_10km, waterway_count_5km, accessibility_score, water_access_score, source
- `FeatureBundle`: location + 5 bloques + region + data_quality
- `SpeciesScore`: species, site_aptitude_present, site_aptitude_future, species_fit_present, species_fit_future, score_present, score_future, delta_aptitud, label
- `RecommendationResult`: ranking, top_species, explanation, feature_bundle

## Convenciones

- **Type hints obligatorios** en funciones públicas.
- **Mock-first**: cada cliente tiene `use_mock: bool = False` por defecto.
- **Sin red en tests**: HTTP se mockea con `monkeypatch` sobre `requests.get/post`.
- **Coverage ≥ 80%** con branch.
- **ruff + mypy strict** en CI antes de mergear.
- **Conventional Commits** sin `Co-Authored-By`.

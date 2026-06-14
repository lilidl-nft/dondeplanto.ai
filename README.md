# dondeplanto.ai

> IA para decidir **dónde plantar hoy** pensando en el clima de **mañana**.

App que combina la **aptitud forestal del suelo** desarrollada por INTA (capa base, presente) con **proyecciones de cambio climático** (modificador temporal, futuro) para recomendar especies forestales resilientes, mostrando aptitud **hoy vs 2050** en provincias con buena cobertura INTA (NEA / Litoral).

## Features

- 🌍 **Selección de ubicación** — manual (lat/lon) o demo calibrada (Corrientes, Entre Ríos, Misiones).
- 🗺️ **Mapa interactivo** (pydeck via `st.pydeck_chart`) con punto, polígonos INTA, caminos y focos de fuego.
- 🧪 **Scoring de dos capas** — aptitud del sitio (suelo INTA − riesgo ambiental + accesibilidad) × match especie-sitio (clima actual/futuro vs tolerancias).
- 📊 **Ranking present/future/Δ** — el corazón de la app: visibiliza el corrimiento de aptitud por especie.
- 📝 **Explicación determinística en español** + reporte Markdown descargable.
- 🔌 **API FastAPI** (`POST /api/report`) para integración externa.
- 🛡️ **Mock-first** — todas las fuentes externas (INTA, Open-Meteo, FIRMS, Overpass) tienen fallback mock. La app nunca se rompe por una fuente caída.
- ✅ **CI estricto** — ruff + mypy strict + pytest con coverage ≥80%.

## Stack

- Python 3.12, [uv](https://docs.astral.sh/uv/)
- [Streamlit](https://streamlit.io/) (UI) + [pydeck](https://deckgl.readthedocs.io/) (mapa via `st.pydeck_chart`)
- [FastAPI](https://fastapi.tiangolo.com/) (API)
- [geopandas](https://geopandas.org/) + [shapely](https://shapely.readthedocs.io/) (point-in-polygon)
- [pytest](https://docs.pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) + [ruff](https://docs.astral.sh/ruff/) + [mypy](https://mypy.readthedocs.io/)

## Cómo correr local

```bash
# 1. Clonar
git clone https://github.com/lilidl-nft/dondeplanto.ai.git
cd dondeplanto.ai

# 2. Instalar deps
uv sync --all-extras

# 3. Generar GeoPackages mock (solo la primera vez; ya vienen commiteados)
uv run python -m dondeplanto.mock.generate_inta_mock

# 4. Levantar Streamlit
uv run streamlit run app.py
# → http://localhost:8501

# 5. (Opcional) Levantar la API en otra terminal
uv run uvicorn dondeplanto.api.app:app --port 8000 --reload
# → http://localhost:8000/docs
```

## Cómo correr los tests

```bash
uv run pytest
```

Ver `pyproject.toml [tool.pytest.ini_options]` para configuración (coverage ≥80%, branch coverage).

## Arquitectura

```
Streamlit UI  (:8501)         FastAPI  (:8000)
     ↓                             ↓
 build_features → recommend → explain → report (markdown/json)
     ↓
 clients/  ← INTA local, Open-Meteo, FIRMS, Overpass  (todos con mock)
     ↓
 features/ ← soil_features, climate_features, fire_features, logistics_features
     ↓
 scoring/  ← membership, site_scoring, species_matching, recommendation
     ↓
 data/     ← species_profiles.yaml, inta/{corrientes,entre_rios,misiones}_suelos.gpkg
```

## Fuentes de datos

- **INTA / GeoINTA** — cartas de suelo y aptitud forestal de Corrientes, Entre Ríos, Misiones. Cache local como GeoPackage + point-in-polygon offline.
- **Open-Meteo Climate API** — delta climático 1991-2020 vs 2041-2060 (mismo modelo).
- **Open-Meteo Historical / Forecast** — clima actual observado (ERA5-Land).
- **NASA FIRMS** — actividad de fuego reciente (no "riesgo"). Mock si falta la `FIRMS_MAP_KEY`.
- **Overpass / OSM** — caminos y cursos de agua. Mock obligatorio.

Ver `docs/data_sources.md` y `docs/inta_integration.md` (próximamente) para detalle.

## Limitaciones

- Cobertura INTA despareja: el MVP se limita a provincias con buena cobertura (NEA / Litoral).
- FIRMS es actividad histórica, no un modelo de peligrosidad.
- Proyección climática ≈ RCP8.5: la Climate API de alta resolución no separa escenarios antes de 2050.
- Sin validación de campo: las recomendaciones son orientativas.
- Perfiles de especie simplificados: tres especies comerciales; sin nativas en MVP.
- Cache estático de INTA: las capas reflejan la fecha de descarga.

## Licencia

Apache 2.0 — ver [LICENSE](LICENSE).

## Contributors

- Liliana Di Lanzo ([@lilidl-nft](https://github.com/lilidl-nft))

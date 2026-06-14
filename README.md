# dondeplanto.ai

> IA para decidir **dónde plantar hoy** pensando en el clima de **mañana**.

App que combina la **aptitud forestal del suelo** desarrollada por INTA (capa base, presente) con **proyecciones de cambio climático** (modificador temporal, futuro) para recomendar especies forestales resilientes, mostrando aptitud **hoy vs 2050** en provincias con buena cobertura INTA (NEA / Litoral).

![demo](docs/img/demo.png)
<!-- Reemplazar con captura real después del primer deploy -->

## Features

- 🌍 **Selección de ubicación** — manual (lat/lon) o demo calibrada (Corrientes, Entre Ríos, Misiones).
- 🗺️ **Mapa interactivo** (pydeck via `st.pydeck_chart`) con punto seleccionado.
- 🧪 **Scoring de dos capas** — aptitud del sitio (suelo INTA − riesgo ambiental + accesibilidad) × match especie-sitio (clima actual/futuro vs tolerancias).
- 📊 **Ranking present/future/Δ** — el corazón de la app: visibiliza el corrimiento de aptitud por especie.
- 💬 **Explicación determinística en español** — sin LLM, 2-3 párrafos.
- 📥 **Reporte Markdown descargable** + endpoint API `POST /api/report` para integración.
- 🔌 **API FastAPI** en `:8000` con OpenAPI auto-generado.
- 🛡️ **Mock-first** — todas las fuentes externas (INTA, Open-Meteo, FIRMS, Overpass) tienen fallback mock. La app nunca se rompe por una fuente caída.
- 📊 **Cobertura de tests 90%**, ruff + mypy strict, CI con GitHub Actions.

## Stack

- Python 3.12, [uv](https://docs.astral.sh/uv/)
- [Streamlit](https://streamlit.io/) (UI en `:8501`) + [pydeck](https://deckgl.readthedocs.io/) (mapa)
- [FastAPI](https://fastapi.tiangolo.com/) (API en `:8000`)
- [geopandas](https://geopandas.org/) + [shapely](https://shapely.readthedocs.io/) (point-in-polygon)
- [Open-Meteo](https://open-meteo.com/) Climate + Historical Weather
- [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (opcional, con MAP_KEY)
- [Overpass / OpenStreetMap](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [pytest](https://docs.pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) + [ruff](https://docs.astral.sh/ruff/) + [mypy](https://mypy.readthedocs.io/)

## Cómo correr local

```bash
# 1. Clonar
git clone https://github.com/lilidl-nft/dondeplanto.ai.git
cd dondeplanto.ai

# 2. Instalar deps
uv sync --all-extras

# 3. (Solo la primera vez) Generar GeoPackages mock
uv run python -m dondeplanto.mock.generate_inta_mock

# 4. Levantar Streamlit
uv run streamlit run app.py
# → http://localhost:8501

# 5. (Opcional) Levantar la API en otra terminal
uv run uvicorn dondeplanto.api.app:app --port 8000 --reload
# → http://localhost:8000/docs (OpenAPI interactivo)
```

## Cómo correr los tests

```bash
uv run pytest
```

Ver `pyproject.toml [tool.pytest.ini_options]` para configuración (coverage
≥80% con branch, sin red en tests).

## Arquitectura

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

Detalles en [`docs/architecture.md`](docs/architecture.md).

## Documentación

- [`docs/architecture.md`](docs/architecture.md) — arquitectura en capas y contratos de datos.
- [`docs/data_sources.md`](docs/data_sources.md) — INTA, Open-Meteo, FIRMS, Overpass.
- [`docs/inta_integration.md`](docs/inta_integration.md) — cómo descargar y mapear cartas INTA reales.
- [`docs/scoring_methodology.md`](docs/scoring_methodology.md) — fórmulas, pesos y umbrales.
- [`docs/limitations.md`](docs/limitations.md) — qué NO cubre el MVP.
- [`docs/demo_script.md`](docs/demo_script.md) — guía paso a paso de las 3 demos.

## Fuentes de datos

- **INTA / GeoINTA** — cartas de suelo y aptitud forestal de Corrientes, Entre Ríos, Misiones. Cache local como GeoPackage + point-in-polygon offline.
- **Open-Meteo Climate API** — delta climático 1991-2020 vs 2041-2060 (mismo modelo).
- **Open-Meteo Historical / Forecast** — clima actual observado (ERA5-Land).
- **NASA FIRMS** — actividad de fuego reciente (no "riesgo"). Mock si falta la `FIRMS_MAP_KEY`.
- **Overpass / OSM** — caminos y cursos de agua. Mock obligatorio (Overpass se cae).

Ver [`docs/data_sources.md`](docs/data_sources.md) para detalle.

## Limitaciones

- Cobertura INTA despareja: el MVP se limita a provincias con buena cobertura (NEA / Litoral).
- FIRMS es actividad histórica, no un modelo de peligrosidad.
- Proyección climática ≈ RCP8.5: la Climate API de alta resolución no separa escenarios antes de 2050.
- Sin validación de campo: las recomendaciones son orientativas.
- Perfiles de especie simplificados: tres especies comerciales; sin nativas en MVP.
- Cache estático de INTA: las capas reflejan la fecha de descarga.

Ver [`docs/limitations.md`](docs/limitations.md) completo.

## Licencia

Apache 2.0 — ver [LICENSE](LICENSE).

## Contributors

- Liliana Di Lanzo ([@lilidl-nft](https://github.com/lilidl-nft))

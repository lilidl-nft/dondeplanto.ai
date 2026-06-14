# INTA Integration

Cómo se descargan y mapean las cartas de suelo de INTA al cache local
(`data/inta/<provincia>_suelos.gpkg`).

> **Estado actual (F1):** los GeoPackages son **mock** generados por
> `dondeplanto.mock.generate_inta_mock`. Sirven para correr la app
> end-to-end. La descarga real es una tarea para el humano (sección 10
> del spec), documentada abajo.

## Schema esperado por `inta_local_client`

El cliente espera que cada `*.gpkg` tenga una capa con la geometría y
las columnas del contrato. Si tu GeoPackage real tiene otros nombres
de columna, **adaptá el mapeo en el cliente, no el contrato**.

### Columnas requeridas

| Columna | Tipo | Descripción |
|---|---|---|
| `geometry` | (GeoPackage) | polígono de la unidad cartográfica |
| `soil_series` | str | nombre de la serie de suelo |
| `soil_capability_class` | str | ej. "IIIs" |
| `soil_productivity_index` | float (0..100) | índice de productividad |
| `soil_drainage_class` | str | ver tabla 5.4 |
| `soil_forestry_aptitude` | str | "Alta" / "Media" / "Baja" / "Marginal" |
| `soil_aptitude_score` | float (0..1) | pre-computado (opcional; el cliente lo recalcula) |
| `waterlogging_risk` | float (0..1) | pre-computado (opcional; el cliente lo recalcula) |
| `source` | str | metadata |

### Mapeo desde columnas INTA reales

En la práctica, las cartas INTA usan nombres distintos. Ejemplo de mapeo
para la Carta de Suelos 1:50000 de Corrientes (de uso común):

| INTA real (ejemplo) | Columna esperada |
|---|---|
| `serie` o `SERIE` | `soil_series` |
| `clase_capacidad_uso` o `CapUso` | `soil_capability_class` |
| `IP` (Índice de Productividad) | `soil_productivity_index` |
| `drenaje` o `Drenaj` | `soil_drainage_class` |
| `aptitud_forestal` o `AptFor` | `soil_forestry_aptitude` |
| (computar) | `soil_aptitude_score` |
| (computar) | `waterlogging_risk` |
| (fijo) | `source` = "inta_local" |

`soil_aptitude_score` y `waterlogging_risk` se **derivan** de los
atributos crudos en `features.soil_features`, no se leen directamente
del archivo. Eso permite que el contrato sea estable aunque cambien los
datos.

## Cómo descargar y preparar (humano)

Tarea según sección 10 del spec. Pasos:

1. **Elegir el WFS o el Geoportal INTA.**
   - WFS: `https://geointa.inta.gob.ar/geoserver/wfs` (GeoServer).
   - Geoportal: https://geoportal.inta.gob.ar/

2. **Hacer un GetFeature por provincia** y descargar el GeoJSON o
   shapefile. Ejemplo con `requests`:

   ```python
   import requests
   params = {
       "service": "WFS",
       "version": "1.1.0",
       "request": "GetFeature",
       "typeName": "inta:suelos_corrientes",
       "outputFormat": "json",
       "srsName": "EPSG:4326",
   }
   r = requests.get("https://geointa.inta.gob.ar/geoserver/wfs", params=params, timeout=60)
   r.raise_for_status()
   data = r.json()
   ```

   > **Nota:** el dominio GeoINTA cambió históricamente (.gov.ar ↔ .gob.ar).
   > Si el WFS da 404, probar el otro o el Geoportal.

3. **Convertir a GeoPackage** con `geopandas`:

   ```python
   import geopandas as gpd
   gdf = gpd.read_file("corrientes_suelos.geojson")
   gdf = gdf.to_crs("EPSG:4326")
   gdf.to_file("data/inta/corrientes_suelos.gpkg", driver="GPKG", layer="suelos")
   ```

4. **Renombrar columnas** según el mapeo de arriba.

5. **Validar con tests** que la app sigue funcionando:

   ```bash
   uv run pytest tests/test_inta_local_client.py
   ```

   Si el test falla, es probable que falte mapear una columna o que el
   cliente reciba un valor inesperado. En ese caso, ajustar el mapeo
   en `clients/inta_local_client.py` o agregar lógica de fallback.

6. **Commitear el `.gpkg` al repo** (o no — depende de la política del
   equipo). El `.gitignore` actual excluye `data/inta/*_real.gpkg`
   precisamente para esto.

## Limitación: la cobertura INTA es despareja

Las cartas de suelo de INTA a escala 1:50000 son buenas en
Mesopotamia/Litoral y Pampa. En NOA, Patagonia y Cuyo, la cobertura
es gruesa o nula. Por eso el MVP se limita a las 3 provincias con
buena cobertura: Corrientes, Entre Ríos, Misiones.

Para expandir a otras regiones, hay que:

1. Conseguir las cartas de suelo correspondientes (otra dependencia
   de la tarea humana).
2. Verificar que el schema se pueda mapear al contrato.
3. Agregar el bbox correspondiente a `config.PROVINCE_BBOX`.

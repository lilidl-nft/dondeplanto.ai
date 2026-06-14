# Data Sources

## INTA / GeoINTA — capa base de aptitud

**Rol:** capa base de aptitud presente. INTA desarrolló la cartografía de
suelos y la zonificación de aptitud forestal. La app la usa tal cual está,
con point-in-polygon offline sobre GeoPackage.

**Qué provee:**

- Cartas de Suelo con Clases de Capacidad de Uso e Índice de Productividad.
- Trabajos de aptitud forestal: Mapa de Suelos de Aptitud Forestal de
  Corrientes (INTA EEA Corrientes) y zonificaciones de Entre Ríos.
- Atributos edáficos por unidad cartográfica: clase de drenaje, limitantes
  (hidromorfismo, salinidad, profundidad efectiva), textura.

**Acceso:**

- Servicios OGC de GeoINTA: WMS, WFS (`geointa.inta.gob.ar/geoserver/wfs`).
- Geoportal INTA: descarga de cartas por departamento.

**Estrategia de integración (sección 10 del spec):**

1. Precargar una sola vez las capas de las 3 provincias demo (Corrientes,
   Entre Ríos, Misiones) desde el WFS/Geoportal.
2. Guardarlas como **GeoPackage local** en `data/inta/`.
3. Hacer **point-in-polygon offline** con `geopandas`/`shapely`.
4. Dejar el WFS en vivo como camino secundario, con fallback al cache local.

**Limitación:** la cobertura INTA es despareja (buena en Mesopotamia/Litoral
y Pampa; pobre fuera). El MVP se limita a provincias con buena cobertura.
Cuando una coord cae fuera, la app marca `inta_coverage=false` y cae a mock.

## Open-Meteo Climate API — modificador climático futuro

**Rol:** calcular el corrimiento 1991-2020 → 2041-2060.

**Endpoint:** `https://climate-api.open-meteo.com/v1/climate`

**Metodología:** baseline y futuro tomados de la **misma** API y el **mismo**
modelo (metodología consistente). No usamos el forecast de 16 días como
baseline (eso era ruido, no señal climática).

**Modelos:** CMIP6 / HighResMIP, 4 modelos disponibles en
`config.CLIMATE_MODELS`. Antes de 2050 la API no separa escenarios; los
modelos están aproximadamente en RCP8.5. Por eso **se eliminó el selector
low/medium/high** del plan original: en su lugar, selector de modelo o
ensemble. Mostrar la media del ensemble y su dispersión comunica
honestamente la incertidumbre.

**Variables:** temperatura_2m_max, temperatura_2m_min, precipitation_sum,
diario, 1950-2050, ~10 km de resolución, bias-corregido contra ERA5.

## Open-Meteo Historical / Forecast — clima actual observado

**Rol:** mostrar el clima actual observado al usuario (display), NO baseline
del delta. Eso lo hace la Climate API de F4.

- **Historical Weather (ERA5-Land):** `https://archive-api.open-meteo.com/v1/archive`.
  Acumulados anuales (precipitación, ET0). Último año completo cerrado
  (year-2 → year-1) para garantizar dataset estable.
- **Forecast:** `https://api.open-meteo.com/v1/forecast`. Condiciones de los
  próximos días. Solo display.

## NASA FIRMS — actividad de fuego reciente

**Rol:** historial de detecciones de focos activos / anomalías térmicas
(MODIS/VIIRS). Es **historial/actividad de fuego**, NO un modelo de
peligrosidad. La app debe nombrarlo así para no sobre-afirmar.

**Acceso:** requiere `FIRMS_MAP_KEY` (gratuita en
https://firms.modaps.eosdis.nasa.gov/api/area/). Sin key, mock.

**Variables:** bbox (lat±delta, lon±delta según radius_km), CSV con lat,
lon, acq_date. Reducimos a 30d / 365d / nearest_km / fire_activity_score.

## Overpass / OSM — accesibilidad logística

**Rol:** caminos y cursos de agua cercanos. Indicador de accesibilidad para
implantación y manejo.

**Acceso:** `https://overpass-api.de/api/interpreter` con query Overpass-QL
para ways[highway] y ways[waterway] en radio.

**Limitación crítica:** Overpass se cae/ralentiza seguido. **El fallback
mock es obligatorio** (lo dice el spec), no opcional. La app nunca se
rompe por Overpass caído.

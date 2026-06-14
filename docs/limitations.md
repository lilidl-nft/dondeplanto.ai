# Limitations

El MVP 2 tiene varias limitaciones que la app debe declarar explícitamente
para no sobre-afirmar. Esta lista es la fuente de verdad para la sección
"Limitaciones" del reporte y para los avisos en la UI.

## Cobertura INTA despareja

La cartografía de INTA es **buena en NEA/Litoral y Pampa**, y **pobre o
gruesa** en otras regiones (NOA, Patagonia, Cuyo). El MVP se limita a
las 3 provincias con buena cobertura: Corrientes, Entre Ríos, Misiones.

**Implicación práctica:** la app avisa cuando una coordenada cae fuera
de cobertura con un warning y marca `inta_coverage=false` en el bundle.
El `data_quality` queda en `partial_mock` o `all_mock`.

## FIRMS es actividad, no riesgo

NASA FIRMS provee detecciones de focos activos / anomalías térmicas
(MODIS/VIIRS). Es **historial/actividad reciente**, NO un modelo de
peligrosidad probabilístico. La app debe nombrarlo así para no
sobre-afirmar: en la UI aparece como "fire_activity_score" y en el
reporte como "actividad de fuego reciente".

## Proyección climática ≈ RCP8.5

La Climate API de alta resolución de Open-Meteo (CMIP6 / HighResMIP)
no separa escenarios de emisión antes de 2050. Los modelos están
aproximadamente en RCP8.5. Por eso:

- **No hay selector de escenario de emisión** (no sería honesto ofrecerlo).
- En su lugar, selector de modelo o ensemble. Mostrar la media del
  ensemble y su `ensemble_spread` (desviación estándar del temp_max_delta
  entre modelos) comunica honestamente la incertidumbre.

## Perfiles de especie simplificados

El MVP incluye **tres especies comerciales del NEA**: Eucalyptus dunnii,
Eucalyptus grandis, Pinus taeda. No hay nativas en esta versión. Los
rangos trapezoidales son punto de partida calibrable (documentados como
tales en el YAML y en `scoring_methodology.md`); no son verdades
absolutas — la calibración fina requiere literatura INTA/forestal.

## Sin validación de campo

Las recomendaciones son **orientativas** y no reemplazan un estudio
agronómico de sitio. La app no considera:

- Topografía detallada (pendientes locales, microclima).
- Vientos dominantes y exposición.
- Plagas y enfermedades específicas.
- Historia de uso del suelo (desmonte, ganadería, agrícola).
- Aspectos legales y de tenencia de la tierra.

Para una decisión de plantación real, complementar con un profesional
forestal y un análisis de sitio.

## Cache estático de INTA

Los GeoPackages en `data/inta/` reflejan la fecha de descarga. No hay
actualización automática. Si INTA publica una nueva versión de las
cartas de suelo, hay que re-descargar y re-empaquetar (F+ implementa
el WFS en vivo como `inta_wfs_client.py` para esto).

## Modo mock y `data_quality`

Toda fuente externa (INTA, Open-Meteo, FIRMS, Overpass) tiene fallback
mock. La app nunca se rompe por una fuente caída, pero en ese caso el
`data_quality` lo refleja:

- `all_real`: todos los bloques vinieron de la API real.
- `partial_mock`: algunos bloques cayeron a mock.
- `all_mock`: todos mock (modo demo puro o red caída).

La UI muestra este flag en el footer de cada tab, y el reporte Markdown
lo incluye en la sección "Data quality y limitaciones".

## Versión del MVP

Esta es la versión **MVP 2** (revisión 2). Mejoras planeadas para
versiones futuras (no en MVP):

- **LLM en explicación** (opcional): la versión actual es determinística
  en español; F+ puede usar un LLM para texto más rico.
- **Reporte PDF** (opcional): hoy se descarga Markdown; PDF como mejora.
- **Más especies y nativas**.
- **Selector de horizonte** (2030/2050/2070) cuando la API lo soporte.
- **Optimización logística** (camino más cercano a red vial principal).

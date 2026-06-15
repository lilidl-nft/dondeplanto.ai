# Demo script

Esta página describe cómo correr la app localmente y qué esperar de las
3 demos calibradas. Útil para la primera vez y para validar que el
entorno está bien armado.

## Setup local

```bash
# 1. Clonar
git clone https://github.com/lilidl-nft/dondeplanto.ai.git
cd dondeplanto.ai

# 2. Instalar deps
uv sync --all-extras

# 3. (Solo la primera vez) Generar GeoPackages mock
uv run python -m dondeplanto.mock.generate_inta_mock

# 4. Levantar Streamlit en una terminal
uv run streamlit run app.py
# → http://localhost:8501

# 5. (Opcional) Levantar la API en otra terminal
uv run uvicorn dondeplanto.api.app:app --port 8000 --reload
# → http://localhost:8000/docs (OpenAPI interactivo)
```

## Las 3 demos calibradas

Cada demo muestra un patrón distinto del modelo de dos capas
(aptitud INTA presente + corrimiento climático). La idea es que las
tres juntas cubran el rango de casos que la app debe distinguir.

### Demo 1: Corrientes (Santo Tomé)

```
INTA: aptitud forestal Alta, buen drenaje.
Clima futuro: +1.6 °C, lluvia estable.
Estrés hídrico futuro: moderado.
Resultado: E. dunnii se sostiene mejor que E. grandis a 2050.
Recomendación: Eucalyptus dunnii.
```

**Qué ver en la UI:**
- Tab "Diagnóstico" → `soil_forestry_aptitude: Alta`, drenaje bueno.
- Tab "Ranking" → E. dunnii arriba, E. grandis con Δ negativo
  (pierde aptitud).

### Demo 2: Entre Ríos (Concordia)

```
INTA: aptitud Media, drenaje imperfecto → riesgo de anegamiento.
Clima futuro: +1.8 °C, leve caída de precipitación.
Resultado: la limitante dominante es el drenaje (dato INTA real),
no el clima.
Recomendación: Pinus taeda en posiciones bien drenadas; evitar bajos.
```

**Qué ver en la UI:**
- Tab "Diagnóstico" → `waterlogging_risk > 0.5`.
- Tab "Ranking" → P. taeda gana por mejor drenaje (sobrevive
  imperfecto). E. grandis cae por alta sensibilidad al anegamiento.

### Demo 3: Misiones (Oberá)

```
INTA: aptitud Alta, suelos rojos profundos.
Clima futuro: +1.5 °C, buen régimen de lluvias sostenido.
Actividad de fuego: baja-moderada.
Resultado: aptitud se mantiene alta a 2050.
Recomendación: E. grandis o P. taeda según destino productivo.
```

**Qué ver en la UI:**
- Tab "Diagnóstico" → `soil_aptitude_score` más alto de los 3 demos.
- Tab "Ranking" → E. grandis primero (aprovecha el agua), Δ pequeño
  (clima estable). Bajo estrés hídrico.

## Validación rápida

Después de `uv run pytest`, deberías ver:

```
========= N passed in 0.5s =========
Required test coverage of 80% reached. Total coverage: ~90%
```

Si ves errores:

- **ImportError**: `uv sync` no terminó bien. Repetir.
- **ModuleNotFoundError: geopandas**: `--all-extras` faltó.
- **Tests fallan por red**: los tests mockean HTTP, no debería pasar.
  Si pasa, abrir issue con el log.

## Probando el endpoint API

```bash
# Con la API corriendo en :8000
curl -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d '{"lat": -27.49, "lon": -55.12, "use_mock": true, "format": "markdown"}'
```

Devuelve JSON con el campo `markdown_report` (Markdown completo).
Sin `format: "markdown"`, devuelve JSON sin el reporte (más liviano).

Para integración programática desde otros lenguajes, la doc OpenAPI
auto-generada está en `http://localhost:8000/docs`.

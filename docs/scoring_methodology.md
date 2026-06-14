# Scoring methodology

El modelo de scoring se separa explícitamente en **dos niveles** para
evitar la circularidad que tenía el plan original (mezclar aptitud
del sitio con match especie antes de tiempo).

## Capa A — Aptitud del sitio (independiente de especie)

```
site_aptitude(scenario) =
      soil_aptitude_score        * 0.45
    + (1 - environmental_risk(scenario)) * 0.35
    + accessibility_score        * 0.20
```

`scenario` elige el clima observado (presente) o futuro (proyectado) para
calcular el riesgo ambiental.

### `soil_aptitude_score` (0..1)

Mapeo del `soil_forestry_aptitude` (tabla 5.5):

| Aptitud | Score |
|---|---:|
| Alta | 0.85 |
| Media | 0.60 |
| Baja | 0.35 |
| Marginal | 0.15 |
| desconocida | 0.40 |

Si solo hay `soil_productivity_index` (0..100): `score = clamp(index/100, 0, 1)`.

### `environmental_risk(scenario)` (0..1)

```
environmental_risk = fire_activity_score * 0.35
                   + water_stress        * 0.40
                   + waterlogging_risk   * 0.25
```

- `fire_activity_score`: proxy de actividad reciente (NO riesgo), suma
  ponderada de focos 30d/365d. Ver `features/fire_features.py`.
- `water_stress`: depende del scenario.
  - **present:** `water_stress_present` (proxy de precipitación observada
    modulada por ET/precip ratio). F5+.
  - **future:** `water_stress_future` (fórmula 5.3, con redistribución
    0.57/0.43 si no hay ET).
- `waterlogging_risk`: deriva de la clase de drenaje INTA (tabla 5.4).
  Dato REAL, no inventado.

### `accessibility_score` (0..1)

Viene de Overpass: `(roads * 0.6 + primary_roads * 0.4) / 30`, clamp a [0,1].

## Capa B — Match especie-sitio (por especie)

### Membresía trapezoidal (5.2)

```
membership(x, min, opt_low, opt_high, max):
    if x <= min or x >= max:        return 0.0
    if opt_low <= x <= opt_high:    return 1.0
    if x < opt_low:                 return (x - min) / (opt_low - min)
    else:                           return (max - x) / (max - opt_high)
```

### `species_climate_fit(temp, precip)` (0..1)

```
species_climate_fit = trapezoidal(temp, perfil.temp_*)    * 0.5
                    + trapezoidal(precip, perfil.precip_*) * 0.5
```

Se evalúa con clima **observado** (presente) y clima **proyectado** (futuro).

### Ajuste por `drought_tolerance` (5.5)

```
raw_future = species_climate_fit(future_temp, future_precip)
penalizacion = (present_fit - raw_future) * (1 - drought_tolerance)
species_fit_future = clamp(present_fit - penalizacion, 0, 1)
```

Especies con mayor `drought_tolerance` pierden menos aptitud al pasar al
clima futuro. Implementación "simple" del spec.

## Score final y etiqueta (5.6)

```
score_present = site_aptitude("present") * species_fit_present
score_future  = site_aptitude("future")  * species_fit_future
delta_aptitud = score_future - score_present
```

| score_future | delta | label |
|---|---|---|
| ≥ 0.65 | — | **Recomendada** |
| 0.50..0.65 | — | **Viable** |
| < 0.50 | < -0.15 | **Pierde aptitud a futuro** |
| else | — | **No prioritaria** |

## Justificación de pesos y umbrales

- **Pesos del sitio (0.45/0.35/0.20)**: el suelo es la base (INTA validó
  la aptitud), el riesgo ambiental es modificador (cambia con el clima),
  la accesibilidad es bonus (no define la aptitud).
- **Pesos del riesgo (0.35/0.40/0.25)**: el agua pesa más que el fuego y
  que el anegamiento porque es el factor que más cambia con el clima.
- **Tolerancia 30% / -30%** en water_stress_future: es la sensibilidad
  "moderada" del spec para el delta climático esperado a mitad de siglo.
- **0.65/0.50/0.15** en etiquetas: alineado con uso agronómico
  (Recomendada > 0.65 es plantable sin reparos, Viable con manejo, etc.).

## Variaciones y notas

- `water_stress_present` no está en el spec literalmente (la fórmula 5.3
  es para "future"). Se aproxima a partir de precipitación observada
  modulada por la razón ET/precip. Documentado en `scoring/site_scoring.py`.
- Los perfiles de especie son punto de partida calibrable. Las 3 especies
  comerciales del NEA son las del YAML; F+ puede calibrar con literatura
  INTA/forestal sin tocar el código (leer siempre del YAML, sección 8).

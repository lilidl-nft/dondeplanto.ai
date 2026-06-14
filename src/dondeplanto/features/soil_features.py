"""Funciones puras: atributos crudos INTA → contrato SoilFeatures.

Implementa los mapeos de las tablas 5.4 (drainage → waterlogging_risk) y
5.5 (soil_forestry_aptitude → soil_aptitude_score) del build spec. Si solo
está `soil_productivity_index` se usa `clamp(index/100, 0, 1)`.

Estas funciones son puras (sin I/O, sin red) y se testean sin red.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Tabla 5.4 del spec: drainage_class → waterlogging_risk
# ---------------------------------------------------------------------------

# Cobertura amplia: incluimos variantes que aparecen tanto en datos reales
# de INTA como en los GeoPackages mock generados. Claves normalizadas a
# minúsculas y sin acentos para matching robusto.
DRAINAGE_TO_WATERLOGGING: dict[str, float] = {
    "excesivamente drenado": 0.10,
    "bien drenado": 0.10,
    "moderadamente bien drenado": 0.30,
    "imperfectamente drenado": 0.60,
    "pobremente drenado": 0.85,
    "muy pobremente drenado": 1.00,
    "anegadizo": 1.00,
    "muy pobremente drenado / anegadizo": 1.00,
    "desconocido": 0.40,
    "desconocida": 0.40,
}

# ---------------------------------------------------------------------------
# Tabla 5.5 del spec: soil_forestry_aptitude → soil_aptitude_score
# ---------------------------------------------------------------------------

FORESTRY_APTITUDE_TO_SCORE: dict[str, float] = {
    "alta": 0.85,
    "media": 0.60,
    "baja": 0.35,
    "marginal": 0.15,
    "desconocida": 0.40,
    "desconocido": 0.40,
}


def _normalize(value: str | None) -> str | None:
    """Normaliza string para matching: minúsculas, trim, sin acentos."""
    if value is None:
        return None
    normalized = value.strip().lower()
    # Quitamos acentos comunes (á, é, í, ó, ú) para tolerar variaciones
    # entre la cartografía real y los mocks.
    replacements = str.maketrans({"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"})
    return normalized.translate(replacements)


def drainage_to_waterlogging_risk(drainage_class: str | None) -> float:
    """Mapea `soil_drainage_class` → `waterlogging_risk` (tabla 5.4).

    Devuelve 0.40 (umbral "desconocido") si la clase no está reconocida.
    """
    key = _normalize(drainage_class)
    if key is None:
        return DRAINAGE_TO_WATERLOGGING["desconocido"]
    if key in DRAINAGE_TO_WATERLOGGING:
        return DRAINAGE_TO_WATERLOGGING[key]
    return DRAINAGE_TO_WATERLOGGING["desconocido"]


def forestry_aptitude_to_score(aptitude: str | None) -> float:
    """Mapea `soil_forestry_aptitude` → `soil_aptitude_score` (tabla 5.5).

    Devuelve 0.40 si la aptitud no está reconocida.
    """
    key = _normalize(aptitude)
    if key is None:
        return FORESTRY_APTITUDE_TO_SCORE["desconocida"]
    if key in FORESTRY_APTITUDE_TO_SCORE:
        return FORESTRY_APTITUDE_TO_SCORE[key]
    return FORESTRY_APTITUDE_TO_SCORE["desconocida"]


def productivity_index_to_score(index: float | int | None) -> float:
    """Convierte `soil_productivity_index` (0..100) a score (0..1) clampeado.

    None → 0.40 (umbral "desconocido") consistente con las tablas 5.4/5.5.
    NaN → 0.40 (mismo tratamiento que None, sin propagar indefinido).
    Valores fuera de [0, 100] se clampan al rango válido.
    """
    if index is None:
        return 0.40
    try:
        value = float(index)
    except (TypeError, ValueError):
        return 0.40
    if value != value:  # NaN check (NaN != NaN)
        return 0.40
    return max(0.0, min(1.0, value / 100.0))


def _coerce_str(value: Any) -> str | None:
    """Devuelve el string tal cual o None si está vacío/None."""
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # NaN
        return None
    text = str(value).strip()
    return text if text else None


def _coerce_float(value: Any) -> float | None:
    """Devuelve el float o None si no es convertible."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:  # NaN
        return None
    return result


def raw_to_soil_features(
    raw: dict[str, Any],
    *,
    source: str = "inta_local",
    inta_coverage: bool = True,
) -> dict[str, Any]:
    """Transforma la fila cruda de un GeoPackage INTA al contrato SoilFeatures.

    Aplica en este orden de prioridad (lo más informativo gana):
      1. `soil_forestry_aptitude` explícita → `soil_aptitude_score`
         (tabla 5.5)
      2. Si falta, `soil_productivity_index` → clamp(index/100, 0, 1)
         (override aunque también haya aptitude, si esa es None/Unknown)
      3. `soil_drainage_class` → `waterlogging_risk` (tabla 5.4)

    Conserva los metadatos crudos para diagnóstico y fija `source` y
    `inta_coverage` según lo que diga el caller.
    """
    aptitude = _coerce_str(raw.get("soil_forestry_aptitude"))
    drainage = _coerce_str(raw.get("soil_drainage_class"))
    productivity = _coerce_float(raw.get("soil_productivity_index"))

    # Resolución del score: si la aptitude es "desconocida"/vacía y hay
    # productivity_index válido, usamos el índice (sección 4.5 del spec).
    aptitude_key = _normalize(aptitude)
    if aptitude_key is None or aptitude_key in {"desconocida", "desconocido"}:
        score = productivity_index_to_score(productivity)
    else:
        score = forestry_aptitude_to_score(aptitude)

    return {
        "soil_series": _coerce_str(raw.get("soil_series")),
        "soil_capability_class": _coerce_str(raw.get("soil_capability_class")),
        "soil_productivity_index": productivity,
        "soil_drainage_class": drainage if drainage is not None else "desconocido",
        "soil_forestry_aptitude": aptitude if aptitude is not None else "desconocida",
        "soil_aptitude_score": score,
        "waterlogging_risk": drainage_to_waterlogging_risk(drainage),
        "inta_coverage": bool(inta_coverage),
        "source": source,
    }

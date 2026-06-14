"""Explicación determinística en español para una recomendación (spec 4.14).

Toma un `RecommendationResult` (de `scoring.recommendation`) y devuelve un
string natural que menciona: aptitud INTA, delta climático, especie top y
por qué, y el corrimiento de la peor especie. Sin LLM.
"""

from __future__ import annotations

from typing import Any

# Umbrales orientativos para el lenguaje cualitativo (no son del spec formal,
# solo afectan la prosa, no el scoring).
_DRYNESS_LOW: float = 0.20
_DRYNESS_MID: float = 0.45
_DRYNESS_HIGH: float = 0.70

_APTITUDE_LOW: float = 0.40
_APTITUDE_MID: float = 0.65


def _aptitud_label(score: float) -> str:
    if score >= _APTITUDE_MID:
        return "alta"
    if score >= _APTITUDE_LOW:
        return "moderada"
    return "baja"


def _dryness_label(stress: float) -> str:
    if stress <= _DRYNESS_LOW:
        return "bajo"
    if stress <= _DRYNESS_MID:
        return "moderado"
    if stress <= _DRYNESS_HIGH:
        return "alto"
    return "muy alto"


def _drainage_label(waterlog: float) -> str:
    if waterlog <= 0.20:
        return "buen drenaje"
    if waterlog <= 0.40:
        return "drenaje moderado"
    if waterlog <= 0.70:
        return "riesgo de anegamiento"
    return "alto riesgo de anegamiento"


def _delta_str(delta: float | None, unit: str) -> str:
    """Formatea un delta con signo y unidad. None → 'no disponible'."""
    if delta is None:
        return f"no disponible ({unit})"
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f} {unit}"


def _format_pct(p: float | None) -> str:
    if p is None:
        return "no disponible"
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.1f} %"


def explain(recommendation: dict[str, Any]) -> str:
    """Devuelve una explicación en español (1-3 párrafos) del resultado.

    El texto es determinístico: mismas entradas → mismo string. No usa LLM.
    """
    bundle = recommendation.get("feature_bundle") or {}
    ranking: list[dict[str, Any]] = recommendation.get("ranking") or []
    if not ranking:
        return (
            "No se pudo generar una recomendación: el ranking está vacío. "
            "Verificá que `data/species_profiles.yaml` esté disponible y que "
            "el bundle tenga todos los bloques (soil, observed, future, fire, logistics)."
        )

    top = ranking[0]
    worst = ranking[-1] if len(ranking) > 1 else None
    top_name = top["species"]
    top_score = top["score_future"]
    top_label = top["label"]
    top_delta = top["delta_aptitud"]

    soil = bundle.get("soil") or {}
    fut = bundle.get("future") or {}
    obs = bundle.get("observed") or {}
    region = bundle.get("region", "la región")
    data_quality = bundle.get("data_quality", "desconocida")

    # ----- Párrafo 1: contexto del sitio y aptitud INTA -----
    p1_parts: list[str] = []
    p1_parts.append(
        f"Según la cartografía de suelos de INTA, esta ubicación en {region} "
        f"presenta aptitud forestal {_aptitud_label(float(soil.get('soil_aptitude_score', 0)))}"
        f" (drenaje: {_drainage_label(float(soil.get('waterlogging_risk', 0)))})."
        if soil.get("inta_coverage")
        else f"Esta ubicación está fuera de la cobertura INTA demo "
        f"({region}); los datos de suelo son mock y deben interpretarse con cautela."
    )
    if obs.get("obs_precip_sum_annual") is not None:
        p1_parts.append(
            f"El clima actual observado muestra {float(obs['obs_precip_sum_annual']):.0f} mm/año "
            f"de precipitación y temperaturas medias de {float(obs['obs_temp_max_mean']):.1f} °C "
            f"en máximas y {float(obs['obs_temp_min_mean']):.1f} °C en mínimas."
        )
    p1 = " ".join(p1_parts)

    # ----- Párrafo 2: delta climático y top species -----
    p2_parts: list[str] = []
    p2_parts.append(
        f"Las proyecciones 2041-2060 indican un corrimiento de {_delta_str(fut.get('temp_max_delta'), '°C')} "
        f"en temperatura máxima y {_format_pct(fut.get('precip_delta_pct'))} en precipitación, "
        f"con un estrés hídrico futuro {_dryness_label(float(fut.get('water_stress_future', 0)))}."
    )
    p2_parts.append(
        f"Bajo ese escenario, la especie mejor posicionada es **{top_name}** "
        f"(score futuro {top_score:.2f}, etiqueta: {top_label}"
    )
    if top_delta is not None:
        if top_delta < -0.10:
            p2_parts.append(
                f", con un corrimiento de {top_delta:+.2f} que indica pérdida de aptitud"
            )
        elif top_delta > 0.10:
            p2_parts.append(f", con un corrimiento de {top_delta:+.2f} que indica mejora")
    p2_parts.append(").")
    p2 = " ".join(p2_parts)

    # ----- Párrafo 3 (opcional): la peor especie y contexto de calidad -----
    p3: str = ""
    if worst is not None and worst["species"] != top_name:
        worst_name = worst["species"]
        worst_label = worst["label"]
        worst_delta = worst["delta_aptitud"]
        delta_text = f" (corrimiento {worst_delta:+.2f})" if worst_delta is not None else ""
        p3 = (
            f"En el otro extremo, {worst_name} queda como {worst_label}{delta_text}, "
            f"mostrando que el corrimiento climático no es neutro entre especies comerciales."
        )
        if data_quality != "all_real":
            p3 += f" Nota: data_quality={data_quality}; algunos bloques son mock."

    paragraphs = [p1, p2]
    if p3:
        paragraphs.append(p3)
    return "\n\n".join(paragraphs)


__all__ = ["explain"]

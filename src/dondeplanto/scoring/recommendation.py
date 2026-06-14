"""Recommendation engine: combina las dos capas en un ranking (spec 5.6).

Funciones puras, determinísticas, sin I/O. Calculan `score_present`,
`score_future` y `delta_aptitud` por especie, asignan la etiqueta y
ordenan el ranking por `score_future` descendente.
"""

from __future__ import annotations

import logging
from typing import Any

from dondeplanto.scoring.site_scoring import site_aptitude
from dondeplanto.scoring.species_matching import species_climate_fit, species_fit_future

logger = logging.getLogger(__name__)

# Umbrales de la etiqueta (regla 5.6).
_THRESHOLD_RECOMENDADA: float = 0.65
_THRESHOLD_VIABLE: float = 0.50
_THRESHOLD_PIERDE_DELTA: float = -0.15


def _label_for(score_future: float, delta: float) -> str:
    """Asigna etiqueta según la regla 5.6.

    Prioridad:
      1. `score_future >= 0.65`  → "Recomendada"
      2. `0.50 <= score_future < 0.65`  → "Viable"
      3. `score_future < 0.50 and delta < -0.15`  → "Pierde aptitud a futuro"
      4. else → "No prioritaria"
    """
    if score_future >= _THRESHOLD_RECOMENDADA:
        return "Recomendada"
    if score_future >= _THRESHOLD_VIABLE:
        return "Viable"
    if delta < _THRESHOLD_PIERDE_DELTA:
        return "Pierde aptitud a futuro"
    return "No prioritaria"


def _score_species(
    species: str,
    profile: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Calcula todos los campos del `SpeciesScore` (sección 2.9) para una especie."""
    site_present = site_aptitude(bundle, "present")
    site_future = site_aptitude(bundle, "future")

    obs = bundle["observed"]
    obs_temp = float(obs["obs_temp_max_mean"])
    obs_precip = float(obs["obs_precip_sum_annual"])

    fit_present = species_climate_fit(profile, obs_temp, obs_precip)
    fit_future = species_fit_future(profile, bundle["future"], fit_present)

    score_present = site_present * fit_present
    score_future = site_future * fit_future
    delta = score_future - score_present

    return {
        "species": species,
        "site_aptitude_present": site_present,
        "site_aptitude_future": site_future,
        "species_fit_present": fit_present,
        "species_fit_future": fit_future,
        "score_present": score_present,
        "score_future": score_future,
        "delta_aptitud": delta,
        "label": _label_for(score_future, delta),
    }


def rank_species(
    bundle: dict[str, Any], profiles: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Calcula el `SpeciesScore` de cada especie y ordena por `score_future` desc.

    Args:
        bundle: FeatureBundle completo.
        profiles: dict nombre → perfil (salida de `species_profiles.load_profiles`).

    Returns:
        Lista de `SpeciesScore` ordenada por `score_future` descendente.
    """
    scored: list[dict[str, Any]] = []
    for name, profile in profiles.items():
        scored.append(_score_species(name, profile, bundle))
    # Orden estable: primero score_future desc, después score_present desc
    # (para mantener determinismo si dos especies empatan en score_future).
    scored.sort(key=lambda s: (s["score_future"], s["score_present"]), reverse=True)
    return scored


def recommend(bundle: dict[str, Any], profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Devuelve un `RecommendationResult` (sección 2.10) sin `explanation`.

    La explicación se agrega en F6 con `explainer.py`. Acá se devuelve
    `explanation=""` para respetar el contrato.

    Args:
        bundle: FeatureBundle completo.
        profiles: dict nombre → perfil.

    Returns:
        `RecommendationResult` con `ranking`, `top_species`, `explanation`
        y `feature_bundle`.
    """
    ranking = rank_species(bundle, profiles)
    top_species = ranking[0]["species"] if ranking else ""
    return {
        "ranking": ranking,
        "top_species": top_species,
        "explanation": "",
        "feature_bundle": bundle,
    }

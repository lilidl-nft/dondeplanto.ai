"""Cargador de perfiles de especie (sección 2.8 del spec).

Lee `data/species_profiles.yaml` y devuelve un dict nombre → perfil. Es
la única vía para acceder a los parámetros trapezoidales de cada especie:
NO hardcodear en código (sección 8 del spec).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from dondeplanto.config import SPECIES_PROFILES_PATH

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_profiles(path: Path = SPECIES_PROFILES_PATH) -> dict[str, dict[str, Any]]:
    """Carga y cachea los perfiles de especie desde el YAML.

    Args:
        path: ruta al YAML (default: `data/species_profiles.yaml`).

    Returns:
        Dict con nombre de especie como key y sus parámetros trapezoidales
        (`temp_min_c`, `temp_opt_low_c`, …, `fire_sensitivity`) como value.
        Si el archivo falta o es inválido, devuelve `{}` y loggea error
        (la app sigue corriendo, pero el ranking estará vacío).
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        logger.error("No se pudo cargar species_profiles.yaml: %s", exc)
        return {}

    if not isinstance(raw, dict):
        logger.error("species_profiles.yaml mal formado: raíz no es mapping")
        return {}
    return {str(name): dict(profile) for name, profile in raw.items() if isinstance(profile, dict)}

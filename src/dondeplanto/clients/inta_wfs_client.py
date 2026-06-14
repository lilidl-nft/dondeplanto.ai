"""Cliente INTA WFS (secundario): stub preparado para F2.

Hace un GET GetFeature a `config.GEOINTA_WFS` con timeout corto. En
cualquier error (timeout, HTTP no-2xx, JSON inválido, schema inesperado)
devuelve `None` y loguea un warning. El caller debe caer a
`inta_local_client` cuando reciba `None`.

F2 no prioriza la conexión real: dejamos el cliente documentado y con
un try/except general para que el resto del sistema pueda importarlo y
desarrollar la integración de a poco en una fase posterior, sin
romper la app por servicios caídos de GeoINTA.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from dondeplanto.config import GEOINTA_WFS, HTTP_TIMEOUT_SHORT

logger = logging.getLogger(__name__)

# TypeName por defecto del WFS de GeoINTA para cartas de suelo. Si el
# servidor expone otro nombre de layer, parametrizar desde config en F+.
# Documentado como constante acá para no propagar la ambigüedad a config
# mientras la integración real no esté activa.
_DEFAULT_TYPENAME: str = "inta:suelos"


def get_soil_aptitude_wfs(lat: float, lon: float) -> dict[str, Any] | None:
    """Consulta GeoINTA WFS por punto. Devuelve `None` en cualquier error.

    Esta función NUNCA lanza excepciones hacia arriba. Es deliberadamente
    tolerante: si la red está caída, el WFS responde con error, o el
    schema no es el esperado, el caller cae a `inta_local_client`.

    Args:
        lat: latitud en WGS84.
        lon: longitud en WGS84.

    Returns:
        SoilFeatures dict (mismo contrato que `inta_local_client`) o `None`
        si la fuente no se pudo consultar.
    """
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": _DEFAULT_TYPENAME,
        "outputFormat": "json",
        "srsName": "EPSG:4326",
        "bbox": f"{lon - 0.001},{lat - 0.001},{lon + 0.001},{lat + 0.001},EPSG:4326",
    }
    try:
        response = requests.get(GEOINTA_WFS, params=params, timeout=HTTP_TIMEOUT_SHORT)
        response.raise_for_status()
    except requests.Timeout:
        logger.warning("Timeout consultando GeoINTA WFS para (%.4f, %.4f)", lat, lon)
        return None
    except requests.RequestException as exc:
        logger.warning("Error HTTP consultando GeoINTA WFS: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — degradación controlada
        logger.warning("Error inesperado consultando GeoINTA WFS: %s", exc)
        return None

    # Mapeo WFS → contrato. F2: no implementado (dejamos el stub). Si en
    # una fase posterior se quiere activar la integración real, validar
    # aquí el schema de la respuesta y mapear columnas.
    logger.info("WFS de GeoINTA devolvió respuesta; el mapeo a contrato no está implementado aún")
    return None

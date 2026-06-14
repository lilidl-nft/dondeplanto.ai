"""Capa de scoring (F3).

Implementa el núcleo matemático de dondeplanto.ai: combina la aptitud del
sitio (capa A) con el match especie-sitio (capa B) y produce un ranking
con aptitud presente y futura por especie.

Funciones puras, determinísticas, sin I/O, sin red. Mismas entradas →
mismas salidas.
"""

from __future__ import annotations

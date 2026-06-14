"""Clientes de datos externos (INTA, Open-Meteo, FIRMS, Overpass).

Cada cliente expone una función con la firma
    def get_xxx(... use_mock: bool = False) -> dict
y devuelve un dict que cumple el contrato de la sección 2 del build spec.
Si `use_mock=True` o si la llamada real falla, cae al módulo `mock`.
"""

# INTA data

Los GeoPackages `*_suelos.gpkg` en este directorio son **mock** generados por `dondeplanto.mock.generate_inta_mock`. Servirán para correr la app end-to-end sin red durante F1.

## Cómo regenerar los mocks

```bash
uv run python -m dondeplanto.mock.generate_inta_mock
```

Parámetros útiles:
- `--n 12` — resolución del grid (NxN polígonos por provincia)
- `--seed 42` — seed aleatoria para reproducibilidad
- `--out /tmp/foo` — directorio de salida

## Cómo reemplazarlos con datos reales

(F2+. Por ahora pendiente.)

1. Descargar cartas de suelo de Corrientes, Entre Ríos y Misiones desde el WFS de GeoINTA o el Geoportal INTA.
2. Convertir a GeoPackage.
3. Nombrar `corrientes_suelos.gpkg`, `entre_rios_suelos.gpkg`, `misiones_suelos.gpkg`.
4. Verificar que las columnas coincidan con el schema esperado (`docs/inta_integration.md`, próximo).
5. Si las columnas difieren, ajustar el **mapeo** en `src/dondeplanto/clients/inta_local_client.py`, **no** el contrato de `SoilFeatures`.

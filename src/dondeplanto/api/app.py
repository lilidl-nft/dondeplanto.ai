"""API FastAPI para integración externa (spec pregunta 8 opción 2).

Endpoint principal: `POST /api/report`
- Input: `LocationInput` (sección 2.1) + `use_mock: bool = False`
- Output: `RecommendationResult` (JSON) con `markdown_report` y `report`
  (Markdown como string) si se pide `format="markdown"`.

Servidor: uvicorn dondeplanto.api.app:app --port 8000
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from dondeplanto.explanation.explainer import explain
from dondeplanto.explanation.report_generator import generate_markdown_report
from dondeplanto.features.feature_builder import build_features
from dondeplanto.scoring.recommendation import recommend
from dondeplanto.scoring.species_profiles import load_profiles


class ReportRequest(BaseModel):
    """Input del endpoint POST /api/report."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    climate_model: str = "ensemble"
    baseline_period: str = "1991-2020"
    future_period: str = "2041-2060"
    use_mock: bool = False
    format: str = Field(default="json", pattern="^(json|markdown)$")


class ReportResponse(BaseModel):
    """Output del endpoint POST /api/report."""

    location: dict[str, Any]
    region: str
    data_quality: str
    top_species: str
    ranking: list[dict[str, Any]]
    explanation: str
    markdown_report: str | None = None


app = FastAPI(
    title="dondeplanto.ai API",
    description="Recomendación de especies forestales con aptitud presente y futura.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


@app.post("/api/report", response_model=ReportResponse)
def post_report(req: ReportRequest) -> ReportResponse:
    """Genera un reporte de recomendación para una ubicación.

    Levanta 503 si no se puede generar la recomendación (sin perfiles o
    sin bundle). Devuelve 200 con `format="markdown"` para incluir el
    reporte completo en `markdown_report`.
    """
    try:
        bundle = build_features(
            {
                "lat": req.lat,
                "lon": req.lon,
                "climate_model": req.climate_model,
                "baseline_period": req.baseline_period,
                "future_period": req.future_period,
            },
            use_mock=req.use_mock,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=f"Fase pendiente: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"bundle error: {exc}") from exc

    profiles = load_profiles()
    if not profiles:
        raise HTTPException(
            status_code=503,
            detail="No se pudieron cargar los perfiles de especie.",
        )

    rec = recommend(bundle, profiles)
    rec["explanation"] = explain(rec)

    markdown = generate_markdown_report(rec) if req.format == "markdown" else None

    return ReportResponse(
        location=rec["feature_bundle"]["location"],
        region=rec["feature_bundle"]["region"],
        data_quality=rec["feature_bundle"]["data_quality"],
        top_species=rec["top_species"],
        ranking=rec["ranking"],
        explanation=rec["explanation"],
        markdown_report=markdown,
    )


__all__ = ["app", "ReportRequest", "ReportResponse"]

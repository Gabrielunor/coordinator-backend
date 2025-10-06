#!/usr/bin/env python3
"""Main module that exposes the REST API for the coordinator backend."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from coordinator_backend import TileService
from coordinator_backend.services.tiles import build_tile_feature

app = FastAPI(
    title="Coordinator Backend",
    version="0.1.0",
    description=(
        "API responsável por fornecer informações sobre tiles utilizando a curva de Hilbert "
        "no sistema de coordenadas SIRGAS 2000 / Brazil Albers."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tile_service = TileService()


@app.get("/health", tags=["Infra"])
def health_check() -> dict:
    """Simple endpoint used to verify that the service is alive."""
    return {"status": "ok"}


@app.get("/tiles/{level}/{tile_id}", tags=["Tiles"])
def get_tile(level: int, tile_id: str) -> JSONResponse:
    """Return a GeoJSON feature for a tile at a given level and identifier."""
    try:
        tile = tile_service.tile_from_id(level, tile_id)
    except ValueError as exc:  # pragma: no cover - FastAPI handles HTTP translation
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    feature = build_tile_feature(tile)
    return JSONResponse(content=feature)


@app.get("/tiles/lookup", tags=["Tiles"])
def lookup_tile(
    level: int = Query(..., ge=0, description="Nível de resolução desejado"),
    lon: float = Query(..., description="Longitude em WGS84"),
    lat: float = Query(..., description="Latitude em WGS84"),
) -> JSONResponse:
    """Locate the tile covering the provided WGS84 coordinate and return its GeoJSON feature."""
    try:
        tile = tile_service.tile_for_coordinates(level, lon, lat)
    except ValueError as exc:  # pragma: no cover - FastAPI handles HTTP translation
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    feature = build_tile_feature(tile)
    payload = {
        "tile_id": tile.tile_id,
        "feature": feature,
    }
    return JSONResponse(content=payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("script:app", host="0.0.0.0", port=8000, reload=False)

"""Canary API -- FastAPI, serves the pipeline's JSON outputs to the frontend.

Run:  uv run uvicorn api.main:app --reload --port 8000
All data is read from ../outputs/ (produced by `canary`). No external calls.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

OUTPUTS = Path(__file__).resolve().parents[1] / "outputs"

app = FastAPI(title="Canary API", version="0.1.0",
              description="Early-warning signal from NYC 311 complaint data")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _read(name: str):
    p = OUTPUTS / name
    if not p.exists():
        raise HTTPException(404, f"{name} not found -- run the pipeline first")
    return json.loads(p.read_text())


@app.get("/api/health")
def health():
    ready = (OUTPUTS / "zips.json").exists()
    return {"status": "ok" if ready else "no-data", "outputs_dir": str(OUTPUTS)}


@app.get("/api/meta")
def meta():
    return _read("meta.json")


@app.get("/api/findings")
def findings():
    return _read("findings.json")


@app.get("/api/leadlag")
def leadlag():
    return _read("leadlag.json")


@app.get("/api/zips")
def zips():
    return _read("zips.json")


@app.get("/api/grid")
def grid():
    """Compact per-month volume matrix for all ZIPs (drives the 3D scrubber)."""
    return _read("grid.json")


@app.get("/api/zips/{zip_code}/timeseries")
def timeseries(zip_code: str):
    return _read(f"timeseries/{zip_code}.json")


@app.get("/api/zips/{zip_code}/themes")
def zip_themes(zip_code: str):
    return _read(f"themes/{zip_code}.json")


@app.get("/api/zips/{zip_code}")
def zip_detail(zip_code: str):
    all_zips = _read("zips.json")
    rec = next((z for z in all_zips if z["zip"] == zip_code), None)
    if rec is None:
        raise HTTPException(404, f"ZIP {zip_code} not in dataset")
    return JSONResponse({
        "summary": rec,
        "timeseries": _read(f"timeseries/{zip_code}.json"),
        "themes": _read(f"themes/{zip_code}.json"),
    })

"""Serialise the processed tables into compact JSON for the API / frontend.

Writes to outputs/:
  meta.json              run info + caveats
  zips.json              one record per ZIP (map markers + headline stats)
  leadlag.json           full lead-lag result
  findings.json          headline numbers for the summary panel
  timeseries/<zip>.json  monthly volume / velocity / ZHVI series
  themes/<zip>.json      top + emerging complaint themes
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import CFG, IS_SYNTHETIC, OUTPUTS, PROCESSED


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else round(float(o), 5)
    if isinstance(o, float):
        return None if np.isnan(o) else round(o, 5)
    if pd.isna(o) if np.isscalar(o) else False:
        return None
    return o


def _dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_clean(obj), separators=(",", ":")))


def _dataset_label() -> str:
    marker = PROCESSED.parent / "raw" / "LOCAL_SOURCE"
    if marker.exists():
        first = marker.read_text().splitlines()[0]
        if first.startswith("kaggle:"):
            return f"NYC 311 (Kaggle snapshot: {first[7:]}) + Zillow ZHVI ZIP"
        return "NYC 311 (local export) + Zillow ZHVI ZIP"
    return "NYC 311 Service Requests (Socrata erm2-nwe9) + Zillow ZHVI ZIP"


def run(bundle: dict, leadlag: dict) -> None:
    ts = pd.read_parquet(PROCESSED / "signal_timeseries.parquet")
    summary = pd.read_parquet(PROCESSED / "zip_summary.parquet")
    centroids = pd.read_parquet(PROCESSED / "zip_centroids.parquet")
    themes = pd.read_parquet(PROCESSED / "complaints_themes.parquet")
    mix = pd.read_parquet(PROCESSED / "theme_mix.parquet")
    emerging = pd.read_parquet(PROCESSED / "emerging_themes.parquet")
    zhvi = pd.read_parquet(PROCESSED / "zhvi.parquet").sort_values(["zip", "month"])
    zhvi["zhvi_mom"] = zhvi.groupby("zip")["zhvi"].pct_change() * 100
    theme_meta = json.loads((PROCESSED / "theme_meta.json").read_text())

    per_zip_ll = leadlag.get("per_zip", {})
    summary = summary.merge(centroids, on="zip", how="left")

    # --- zips.json ----------------------------------------------------
    recs = []
    for _, r in summary.iterrows():
        zp = r["zip"]
        ll = per_zip_ll.get(zp, [])
        lead = [x for x in ll if x.get("offset", 0) > 0 and x.get("r") is not None]
        best = min(lead, key=lambda x: x["r"]) if lead else {}
        dom = ts[ts["zip"] == zp].dropna(subset=["dominant_theme"])
        recs.append({
            "zip": zp,
            "borough": (r.get("borough") or "") if isinstance(r.get("borough"), str) else "",
            "lat": r.get("lat"), "lon": r.get("lon"),
            "total_volume": r["total_volume"],
            "latest_velocity": r["latest_velocity"],
            "mean_velocity": r["mean_velocity"],
            "latest_volume_z": r["latest_volume_z"],
            "trend_slope": r["trend_slope"],
            "dominant_theme": (dom["dominant_theme"].iloc[-1] if len(dom) else None),
            "best_offset": best.get("offset"),
            "best_r": best.get("r"),
            "in_top_volume": zp in leadlag.get("top_volume_zips", []),
            "in_top_rising": zp in leadlag.get("top_rising_zips", []),
        })
    recs.sort(key=lambda d: d["total_volume"], reverse=True)
    _dump(OUTPUTS / "zips.json", recs)

    # --- timeseries/<zip>.json --------------------------------------
    for zp, g in ts.groupby("zip"):
        g = g.sort_values("month")
        zz = zhvi[zhvi["zip"] == zp].set_index("month")
        _dump(OUTPUTS / "timeseries" / f"{zp}.json", {
            "zip": zp,
            "months": g["month"].tolist(),
            "volume": g["volume"].astype(int).tolist(),
            "velocity": g["velocity"].tolist(),
            "velocity_3m": g["velocity_3m"].tolist(),
            "volume_z": g["volume_z"].tolist(),
            "dominant_theme": g["dominant_theme"].tolist(),
            "zhvi": [zz["zhvi"].get(m) for m in g["month"]],
            "zhvi_mom": [zz["zhvi_mom"].get(m) for m in g["month"]],
            "leadlag": per_zip_ll.get(zp, []),
        })

    # --- themes/<zip>.json -----------------------------------------
    for zp, g in mix.groupby("zip"):
        top = (g.groupby("theme")["n"].sum().sort_values(ascending=False)
               .head(8))
        tot = int(top.sum()) or 1
        em = emerging[emerging["zip"] == zp]
        _dump(OUTPUTS / "themes" / f"{zp}.json", {
            "zip": zp,
            "top_themes": [
                {"theme": t, "n": int(n), "share": round(int(n) / tot, 4)}
                for t, n in top.items()
            ],
            "emerging": em.drop(columns=["zip"]).to_dict("records"),
        })

    # --- grid.json : compact per-month matrix for the 3D scrubber --
    months = sorted(ts["month"].unique())
    grid_zips: dict[str, dict] = {}
    for zp, g in ts.groupby("zip"):
        g = g.set_index("month").reindex(months)
        grid_zips[zp] = {
            "volume": g["volume"].fillna(0).astype(int).tolist(),
            "volume_z": g["volume_z"].tolist(),
            "velocity": g["velocity"].tolist(),
        }
    _dump(OUTPUTS / "grid.json", {"months": months, "zips": grid_zips})

    # --- leadlag.json + findings.json + meta.json -----------------
    _dump(OUTPUTS / "leadlag.json", leadlag)

    theme_catalog = pd.read_parquet(PROCESSED / "theme_catalog.parquet")
    findings = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_zips": int(summary["zip"].nunique()),
        "window": {"start": CFG.start_month, "end": CFG.end_month,
                   "months": len(CFG.months())},
        "headline": leadlag.get("interpretation", ""),
        "best_pooled_all": leadlag.get("best_pooled_all", {}),
        "best_pooled_rising": leadlag.get("best_pooled_rising", {}),
        "pooled": leadlag.get("pooled", {}),
        "top_volume_zips": leadlag.get("top_volume_zips", []),
        "top_rising_zips": leadlag.get("top_rising_zips", []),
        "top_themes_overall": theme_catalog.head(10).to_dict("records"),
        "embedding_method": theme_meta.get("method"),
    }
    _dump(OUTPUTS / "findings.json", findings)

    _dump(OUTPUTS / "meta.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {"start": CFG.start_month, "end": CFG.end_month},
        "n_zips": int(summary["zip"].nunique()),
        "n_sampled_complaints": int(len(themes)),
        "n_themes": theme_meta.get("k"),
        "embedding_method": theme_meta.get("method"),
        "dataset": ("SYNTHETIC test data (not real)" if IS_SYNTHETIC else
                    _dataset_label()),
        "is_synthetic": IS_SYNTHETIC,
        "caveats": ([
            "*** SYNTHETIC 311 DATA -- numbers here are NOT real findings. ***",
        ] if IS_SYNTHETIC else []) + [
            "Exploratory and correlational -- not causal.",
            "Single city (NYC), single 3-year window.",
            "Complaint text sampled (month-stratified), not the full firehose.",
            "ZHVI is smoothed & seasonally adjusted; ZIP coverage is partial.",
            "Raw ZIP-month volumes are not winsorized; a few outlier spikes exist.",
        ],
    })
    print(f"  export: wrote outputs/ for {len(recs)} ZIPs")

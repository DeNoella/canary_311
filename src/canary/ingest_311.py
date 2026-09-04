"""Pull NYC 311 Service Requests from the Socrata Open Data API (erm2-nwe9).

Two pulls, both free and unauthenticated (an optional app token only raises the
rate limit):

1. ``fetch_monthly_counts`` -- a server-side aggregate of complaint counts per
   (month, ZIP, complaint_type). Tiny payload, gives us *true* complaint volume.
2. ``fetch_sample`` -- a bounded, month-stratified sample of individual
   complaint rows (with descriptor text + lat/lon) used for theme discovery and
   for deriving ZIP centroids.
"""
from __future__ import annotations

import io
import os
import time

import pandas as pd
import requests

from .config import CFG, RAW

# If a raw CSV export of erm2-nwe9 is present we use it instead of the API.
# Point CANARY_311_CSV at a file, or drop one at data/raw/nyc311_export.csv.
LOCAL_CSV = os.environ.get("CANARY_311_CSV", str(RAW / "nyc311_export.csv"))

# scripts/fetch_kaggle_311.py writes this marker + prebuilt counts/sample CSVs.
# When present, we always use those (the multi-GB source can't be re-pulled).
LOCAL_SOURCE = RAW / "LOCAL_SOURCE"

BASE = f"https://{CFG.socrata_domain}/resource/{CFG.socrata_dataset}.csv"
_SESSION = requests.Session()
if CFG.socrata_app_token:
    _SESSION.headers["X-App-Token"] = CFG.socrata_app_token
_SESSION.headers["User-Agent"] = "canary-311-early-warning/0.1 (portfolio project)"

# The month after the analysis window, used as an exclusive upper bound.
def _end_exclusive() -> str:
    y, m = (int(x) for x in CFG.end_month.split("-"))
    m += 1
    if m == 13:
        m, y = 1, y + 1
    return f"{y:04d}-{m:02d}-01T00:00:00"


def _start_inclusive() -> str:
    return f"{CFG.start_month}-01T00:00:00"


def _get(params: dict, tries: int = 4) -> pd.DataFrame:
    last_err: Exception | None = None
    for attempt in range(tries):
        try:
            r = _SESSION.get(BASE, params=params, timeout=120)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return pd.read_csv(io.StringIO(r.text), dtype=str)
        except Exception as e:  # noqa: BLE001 - retry any transient failure
            last_err = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Socrata request failed after {tries} tries: {last_err}")


_COL_ALIASES = {
    "created_date": ["created_date", "Created Date", "created date"],
    "complaint_type": ["complaint_type", "Complaint Type"],
    "descriptor": ["descriptor", "Descriptor"],
    "incident_zip": ["incident_zip", "Incident Zip", "zip", "ZIP"],
    "borough": ["borough", "Borough"],
    "latitude": ["latitude", "Latitude"],
    "longitude": ["longitude", "Longitude"],
    "unique_key": ["unique_key", "Unique Key"],
}


def _normalise_export(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c.lower().strip(): c for c in df.columns}
    ren = {}
    for canon, aliases in _COL_ALIASES.items():
        for a in aliases:
            if a.lower() in lower:
                ren[lower[a.lower()]] = canon
                break
    df = df.rename(columns=ren)
    keep = [c for c in _COL_ALIASES if c in df.columns]
    df = df[keep].copy()
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df = df.dropna(subset=["created_date"])
    df["month"] = df["created_date"].dt.strftime("%Y-%m")
    df = df[df["month"].isin(CFG.months())]
    return df


def _local_export() -> pd.DataFrame | None:
    from pathlib import Path

    p = Path(LOCAL_CSV)
    if not p.exists():
        return None
    print(f"  using local 311 export: {p} ({p.stat().st_size/1e6:.0f} MB)")
    df = pd.read_csv(p, dtype=str, low_memory=False)
    return _normalise_export(df)


def fetch_monthly_counts(force: bool = False) -> pd.DataFrame:
    """True monthly complaint counts per ZIP and complaint type."""
    out = RAW / "nyc311_monthly_counts.csv"
    if out.exists() and (not force or LOCAL_SOURCE.exists()):
        return pd.read_csv(out, dtype={"incident_zip": str})

    local = _local_export()
    if local is not None:
        g = (
            local.groupby(["month", "incident_zip", "complaint_type"])
            .size()
            .reset_index(name="n")
        )
        g.to_csv(out, index=False)
        print(f"  counts (from export): {len(g):,} rows -> {out}")
        return g

    where = (
        f"created_date >= '{_start_inclusive()}' "
        f"AND created_date < '{_end_exclusive()}' "
        "AND incident_zip IS NOT NULL"
    )
    select = (
        "date_trunc_ym(created_date) AS month, incident_zip, "
        "complaint_type, count(1) AS n"
    )
    frames: list[pd.DataFrame] = []
    offset, page = 0, 50_000
    while True:
        chunk = _get(
            {
                "$select": select,
                "$where": where,
                "$group": "month, incident_zip, complaint_type",
                "$order": "month, incident_zip, complaint_type",
                "$limit": page,
                "$offset": offset,
            }
        )
        if chunk.empty:
            break
        frames.append(chunk)
        print(f"  counts: +{len(chunk):,} rows (offset {offset:,})")
        if len(chunk) < page:
            break
        offset += page

    df = pd.concat(frames, ignore_index=True)
    df["month"] = pd.to_datetime(df["month"]).dt.strftime("%Y-%m")
    df["n"] = pd.to_numeric(df["n"], errors="coerce").fillna(0).astype(int)
    df.to_csv(out, index=False)
    print(f"  counts: wrote {len(df):,} rows -> {out}")
    return df


def fetch_sample(force: bool = False) -> pd.DataFrame:
    """Month-stratified sample of individual complaints for theme discovery."""
    out = RAW / "nyc311_sample.csv"
    if out.exists() and (not force or LOCAL_SOURCE.exists()):
        return pd.read_csv(out, dtype={"incident_zip": str})

    local = _local_export()
    if local is not None:
        local = local[local["descriptor"].astype(str).str.len() > 0]
        parts = []
        per_month = max(1000, CFG.sample_max_rows // len(CFG.months()))
        for _, grp in local.groupby("month"):
            parts.append(grp.sample(min(len(grp), per_month), random_state=42))
        df = pd.concat(parts, ignore_index=True)
        if len(df) > CFG.sample_max_rows:
            df = df.sample(CFG.sample_max_rows, random_state=42).reset_index(drop=True)
        df.to_csv(out, index=False)
        print(f"  sample (from export): {len(df):,} rows -> {out}")
        return df

    cols = (
        "unique_key, created_date, complaint_type, descriptor, "
        "incident_zip, borough, latitude, longitude"
    )
    per_month = min(CFG.sample_rows_per_month,
                    max(1000, CFG.sample_max_rows // len(CFG.months())))
    frames: list[pd.DataFrame] = []
    for month in CFG.months():
        y, m = (int(x) for x in month.split("-"))
        nm_y, nm_m = (y, m + 1) if m < 12 else (y + 1, 1)
        where = (
            f"created_date >= '{y:04d}-{m:02d}-01T00:00:00' "
            f"AND created_date < '{nm_y:04d}-{nm_m:02d}-01T00:00:00' "
            "AND incident_zip IS NOT NULL AND descriptor IS NOT NULL"
        )
        chunk = _get(
            {
                "$select": cols,
                "$where": where,
                # deterministic ordering by key ~ pseudo-random wrt date/geo
                "$order": "unique_key",
                "$limit": per_month,
            }
        )
        chunk["month"] = month
        frames.append(chunk)
        print(f"  sample {month}: {len(chunk):,} rows")
        if len(frames) % 6 == 0:
            time.sleep(1)

    df = pd.concat(frames, ignore_index=True)
    if len(df) > CFG.sample_max_rows:
        df = df.sample(CFG.sample_max_rows, random_state=42).reset_index(drop=True)
    df.to_csv(out, index=False)
    print(f"  sample: wrote {len(df):,} rows -> {out}")
    return df


if __name__ == "__main__":
    fetch_monthly_counts()
    fetch_sample()

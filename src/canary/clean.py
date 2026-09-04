"""Clean and align the 311 and Zillow pulls.

Outputs (to data/processed/):
  - complaints_counts.parquet : month, zip, complaint_type, n   (true volume)
  - complaints_sample.parquet : one row per sampled complaint + text field
  - zhvi.parquet              : month, zip, zhvi
  - zip_centroids.parquet     : zip, lat, lon, borough
  - shared_zips.json          : ZIPs present in BOTH datasets
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import CFG, NYC_ZIP_MAX, NYC_ZIP_MIN, PROCESSED


def _std_zip(s: pd.Series) -> pd.Series:
    z = s.astype(str).str.extract(r"(\d+)")[0].str[:5].str.zfill(5)
    zi = pd.to_numeric(z, errors="coerce")
    z = z.where((zi >= NYC_ZIP_MIN) & (zi <= NYC_ZIP_MAX))
    return z


def _in_window(month: pd.Series) -> pd.Series:
    return month.isin(CFG.months())


def clean_counts(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["zip"] = _std_zip(df["incident_zip"])
    df["month"] = pd.to_datetime(df["month"], errors="coerce").dt.strftime("%Y-%m")
    df["complaint_type"] = df["complaint_type"].astype(str).str.strip()
    df["n"] = pd.to_numeric(df["n"], errors="coerce")
    df = df.dropna(subset=["zip", "month", "n"])
    df = df[_in_window(df["month"])]
    df = (
        df.groupby(["month", "zip", "complaint_type"], as_index=False)["n"]
        .sum()
    )
    df["n"] = df["n"].astype(int)
    return df


def clean_sample(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["zip"] = _std_zip(df["incident_zip"])
    df["month"] = df["month"].astype(str)
    if "created_date" in df:
        cd = pd.to_datetime(df["created_date"], errors="coerce")
        df["month"] = df["month"].where(df["month"].str.match(r"\d{4}-\d{2}"),
                                        cd.dt.strftime("%Y-%m"))
    for c in ("complaint_type", "descriptor", "borough"):
        df[c] = df.get(c, "").astype(str).str.strip()
    df["lat"] = pd.to_numeric(df.get("latitude"), errors="coerce")
    df["lon"] = pd.to_numeric(df.get("longitude"), errors="coerce")
    df = df.dropna(subset=["zip", "month"])
    df = df[_in_window(df["month"])]
    df = df[df["descriptor"].str.len() > 0]
    key = "unique_key" if "unique_key" in df else None
    if key:
        df = df.drop_duplicates(subset=[key])
    else:
        df = df.drop_duplicates(subset=["zip", "month", "complaint_type", "descriptor"])
    df["text"] = (df["complaint_type"] + " — " + df["descriptor"]).str.strip(" —")
    df["borough"] = (
        df["borough"].replace({"nan": "", "Unspecified": ""}).str.title()
    )
    return df.reset_index(drop=True)


def clean_zhvi(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["zip"] = _std_zip(df["zip"])
    df["month"] = df["month"].astype(str)
    df["zhvi"] = pd.to_numeric(df["zhvi"], errors="coerce")
    df = df.dropna(subset=["zip", "month", "zhvi"])
    df = df.drop_duplicates(subset=["zip", "month"]).sort_values(["zip", "month"])
    return df.reset_index(drop=True)


def zip_centroids(sample: pd.DataFrame) -> pd.DataFrame:
    g = sample.dropna(subset=["lat", "lon"])
    g = g[(g["lat"].between(40.4, 41.0)) & (g["lon"].between(-74.3, -73.6))]
    cen = (
        g.groupby("zip")
        .agg(lat=("lat", "median"), lon=("lon", "median"),
             borough=("borough", lambda s: s.replace("", np.nan).mode(dropna=True).iloc[0]
                      if s.replace("", np.nan).notna().any() else ""))
        .reset_index()
    )
    return cen


def run(counts_raw: pd.DataFrame, sample_raw: pd.DataFrame,
        zhvi_raw: pd.DataFrame) -> dict:
    counts = clean_counts(counts_raw)
    sample = clean_sample(sample_raw)
    zhvi = clean_zhvi(zhvi_raw)

    shared = sorted(
        set(counts["zip"]) & set(zhvi["zip"]) & set(sample["zip"])
    )
    counts = counts[counts["zip"].isin(shared)]
    sample = sample[sample["zip"].isin(shared)]
    zhvi = zhvi[zhvi["zip"].isin(shared)]
    centroids = zip_centroids(sample)
    centroids = centroids[centroids["zip"].isin(shared)]

    counts.to_parquet(PROCESSED / "complaints_counts.parquet", index=False)
    sample.to_parquet(PROCESSED / "complaints_sample.parquet", index=False)
    zhvi.to_parquet(PROCESSED / "zhvi.parquet", index=False)
    centroids.to_parquet(PROCESSED / "zip_centroids.parquet", index=False)
    (PROCESSED / "shared_zips.json").write_text(json.dumps(shared, indent=2))

    print(f"  clean: {len(shared)} shared ZIPs | "
          f"{len(counts):,} count rows | {len(sample):,} sample rows | "
          f"{len(zhvi):,} zhvi rows")
    return {
        "shared_zips": shared,
        "counts": counts,
        "sample": sample,
        "zhvi": zhvi,
        "centroids": centroids,
    }

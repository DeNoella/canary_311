"""Build the per-ZIP monthly complaint signal.

For every (zip, month):
  volume      -- true total complaints (from the aggregate counts pull)
  velocity    -- month-over-month % change in volume
  velocity_3m -- 3-month smoothed velocity
  volume_z    -- z-score of volume vs the trailing 12-month mean/std
                 ("complaint pressure")
  dominant_theme + theme_mix -- from the sampled/clustered complaints

Also derives, per ZIP:
  total_volume, mean_velocity, latest_velocity, trend_slope (OLS slope of the
  last 12 months of volume, normalised), and the emerging themes (themes whose
  recent share materially exceeds their prior share).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

from .config import CFG, PROCESSED


def _full_grid(zips: list[str]) -> pd.MultiIndex:
    return pd.MultiIndex.from_product([zips, CFG.months()], names=["zip", "month"])


def volume_signal(counts: pd.DataFrame) -> pd.DataFrame:
    zips = sorted(counts["zip"].unique())
    vol = (
        counts.groupby(["zip", "month"])["n"].sum()
        .reindex(_full_grid(zips), fill_value=0)
        .rename("volume")
        .reset_index()
        .sort_values(["zip", "month"])
    )
    g = vol.groupby("zip", group_keys=False)
    vol["velocity"] = g["volume"].apply(lambda s: s.pct_change() * 100)
    vol["velocity_3m"] = g["velocity"].apply(
        lambda s: s.rolling(3, min_periods=1).mean()
    )
    roll = g["volume"].apply(
        lambda s: s.shift(1).rolling(12, min_periods=6).agg(["mean", "std"])
    )
    vol["volume_z"] = (vol["volume"] - roll["mean"]) / roll["std"].replace(0, np.nan)
    vol[["velocity", "velocity_3m", "volume_z"]] = (
        vol[["velocity", "velocity_3m", "volume_z"]]
        .replace([np.inf, -np.inf], np.nan)
        .round(4)
    )
    return vol


def theme_mix(themes: pd.DataFrame) -> pd.DataFrame:
    mix = (
        themes.groupby(["zip", "month", "theme"]).size()
        .rename("n").reset_index()
    )
    tot = mix.groupby(["zip", "month"])["n"].transform("sum")
    mix["share"] = (mix["n"] / tot).round(4)
    dominant = (
        mix.sort_values("n", ascending=False)
        .drop_duplicates(["zip", "month"])
        .rename(columns={"theme": "dominant_theme"})[
            ["zip", "month", "dominant_theme"]
        ]
    )
    return mix, dominant


def emerging_themes(themes: pd.DataFrame, recent_m: int = 3,
                    prior_m: int = 12) -> pd.DataFrame:
    months = CFG.months()
    recent = set(months[-recent_m:])
    prior = set(months[-(recent_m + prior_m):-recent_m])
    rows = []
    for zp, grp in themes.groupby("zip"):
        r = grp[grp["month"].isin(recent)]
        p = grp[grp["month"].isin(prior)]
        if len(r) < 15 or len(p) < 30:
            continue
        r_share = r["theme"].value_counts(normalize=True)
        p_share = p["theme"].value_counts(normalize=True)
        for theme, rs in r_share.items():
            ps = float(p_share.get(theme, 0.0))
            lift = rs / ps if ps > 0 else np.inf
            if rs >= 0.08 and (lift >= 1.5 or ps == 0):
                rows.append({
                    "zip": zp, "theme": theme,
                    "recent_share": round(float(rs), 4),
                    "prior_share": round(ps, 4),
                    "lift": round(float(lift), 2) if np.isfinite(lift) else None,
                    "recent_n": int(r["theme"].eq(theme).sum()),
                })
    return pd.DataFrame(rows).sort_values(
        ["zip", "recent_share"], ascending=[True, False]
    )


def per_zip_summary(vol: pd.DataFrame) -> pd.DataFrame:
    months = CFG.months()
    last12 = months[-12:]
    out = []
    for zp, g in vol.groupby("zip"):
        g = g.set_index("month").reindex(months)
        v = g["volume"].fillna(0).to_numpy(dtype=float)
        recent = g.loc[last12, "volume"].fillna(0).to_numpy(dtype=float)
        x = np.arange(len(recent))
        slope = stats.linregress(x, recent).slope if recent.any() else 0.0
        denom = recent.mean() or 1.0
        out.append({
            "zip": zp,
            "total_volume": int(v.sum()),
            "mean_velocity": round(float(np.nanmean(g["velocity"].to_numpy())), 3),
            "latest_velocity": round(float(g["velocity"].dropna().iloc[-1])
                                     if g["velocity"].notna().any() else 0.0, 3),
            "latest_volume_z": round(float(g["volume_z"].dropna().iloc[-1])
                                     if g["volume_z"].notna().any() else 0.0, 3),
            "trend_slope": round(float(slope / denom), 5),
        })
    return pd.DataFrame(out)


def run(counts: pd.DataFrame, themes: pd.DataFrame) -> dict:
    vol = volume_signal(counts)
    mix, dominant = theme_mix(themes)
    vol = vol.merge(dominant, on=["zip", "month"], how="left")
    summary = per_zip_summary(vol)
    emerging = emerging_themes(themes)

    vol.to_parquet(PROCESSED / "signal_timeseries.parquet", index=False)
    mix.to_parquet(PROCESSED / "theme_mix.parquet", index=False)
    summary.to_parquet(PROCESSED / "zip_summary.parquet", index=False)
    emerging.to_parquet(PROCESSED / "emerging_themes.parquet", index=False)
    (PROCESSED / "signal_meta.json").write_text(json.dumps({
        "n_zips": int(vol["zip"].nunique()),
        "months": CFG.months(),
    }, indent=2))
    print(f"  signals: {vol['zip'].nunique()} ZIPs x {len(CFG.months())} months; "
          f"{len(emerging)} emerging-theme rows")
    return {"timeseries": vol, "mix": mix, "summary": summary, "emerging": emerging}

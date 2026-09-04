"""Lead-lag analysis: does the complaint signal move *before* home values?

For each ZIP we align two monthly series:
  X = complaint signal at month T   (volume_z by default; velocity_3m optional)
  Y = ZHVI month-over-month % change at month T + offset

and compute Pearson r (+ p-value, + n overlapping points) for
offset in {0, 3, 6, 12}. A negative r at a positive offset means "a rise in
complaints now is followed by a fall in home-value growth later" -- i.e. the
complaint signal leads decline.

Reported for:
  - the top N ZIPs by total complaint volume
  - the top N ZIPs by sharpest complaint increase (trend_slope)
  - a pooled estimate stacking all shared ZIPs
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

from .config import CFG, PROCESSED


def _zhvi_mom(zhvi: pd.DataFrame) -> pd.DataFrame:
    z = zhvi.sort_values(["zip", "month"]).copy()
    z["zhvi_mom"] = z.groupby("zip")["zhvi"].pct_change() * 100
    return z


def _series(sig: pd.DataFrame, zmom: pd.DataFrame, zp: str, col: str):
    a = (sig[sig["zip"] == zp].set_index("month")[col])
    b = (zmom[zmom["zip"] == zp].set_index("month")["zhvi_mom"])
    idx = sorted(set(a.index) | set(b.index))
    return a.reindex(idx), b.reindex(idx)


def _corr_at(a: pd.Series, b: pd.Series, offset: int):
    # shift Y back by `offset` months so X_T aligns with Y_{T+offset}
    b_shift = b.shift(-offset)
    df = pd.concat([a, b_shift], axis=1, keys=["x", "y"]).dropna()
    if len(df) < CFG.min_months_for_corr:
        return {"offset": offset, "r": None, "p": None, "n": int(len(df))}
    r, p = stats.pearsonr(df["x"], df["y"])
    return {"offset": offset, "r": round(float(r), 4),
            "p": round(float(p), 4), "n": int(len(df))}


def _pooled(sig: pd.DataFrame, zmom: pd.DataFrame, zips: list[str],
            col: str, offset: int):
    xs, ys = [], []
    for zp in zips:
        a, b = _series(sig, zmom, zp, col)
        b_shift = b.shift(-offset)
        df = pd.concat([a, b_shift], axis=1, keys=["x", "y"]).dropna()
        if len(df) >= 6:
            xs.append(stats.zscore(df["x"]) if df["x"].std() else df["x"] * 0)
            ys.append(df["y"].to_numpy())
    if not xs:
        return {"offset": offset, "r": None, "p": None, "n": 0}
    X = np.concatenate([np.asarray(v) for v in xs])
    Y = np.concatenate(ys)
    r, p = stats.pearsonr(X, Y)
    return {"offset": offset, "r": round(float(r), 4),
            "p": round(float(p), 4), "n": int(len(X))}


def run(signal_ts: pd.DataFrame, summary: pd.DataFrame,
        zhvi: pd.DataFrame, signal_col: str = "volume_z") -> dict:
    zmom = _zhvi_mom(zhvi)
    shared = sorted(set(signal_ts["zip"]) & set(zmom["zip"]))
    summary = summary[summary["zip"].isin(shared)]

    top_volume = (
        summary.sort_values("total_volume", ascending=False)
        .head(CFG.top_n_zips)["zip"].tolist()
    )
    top_rising = (
        summary.sort_values("trend_slope", ascending=False)
        .head(CFG.top_n_zips)["zip"].tolist()
    )
    focus = list(dict.fromkeys(top_volume + top_rising))

    per_zip: dict[str, list[dict]] = {}
    for zp in focus:
        a, b = _series(signal_ts, zmom, zp, signal_col)
        per_zip[zp] = [_corr_at(a, b, off) for off in CFG.leadlag_offsets]

    pooled = {
        "all_shared": [_pooled(signal_ts, zmom, shared, signal_col, off)
                       for off in CFG.leadlag_offsets],
        "top_volume": [_pooled(signal_ts, zmom, top_volume, signal_col, off)
                       for off in CFG.leadlag_offsets],
        "top_rising": [_pooled(signal_ts, zmom, top_rising, signal_col, off)
                       for off in CFG.leadlag_offsets],
    }

    def _best(rows: list[dict]) -> dict:
        valid = [r for r in rows if r["r"] is not None]
        if not valid:
            return {}
        # "leads decline" = most negative r among positive offsets
        lead = [r for r in valid if r["offset"] > 0]
        pick = min(lead or valid, key=lambda r: r["r"])
        return pick

    result = {
        "signal_col": signal_col,
        "offsets": list(CFG.leadlag_offsets),
        "top_volume_zips": top_volume,
        "top_rising_zips": top_rising,
        "per_zip": per_zip,
        "pooled": pooled,
        "best_pooled_all": _best(pooled["all_shared"]),
        "best_pooled_rising": _best(pooled["top_rising"]),
        "interpretation": _interpret(pooled),
    }
    (PROCESSED / "leadlag.json").write_text(json.dumps(result, indent=2))
    print(f"  leadlag: focus ZIPs {focus}")
    print(f"  leadlag: pooled(all) = {pooled['all_shared']}")
    return result


def _interpret(pooled: dict) -> str:
    rows = [r for r in pooled["all_shared"] if r["r"] is not None]
    if not rows:
        return "Insufficient overlapping data to assess a lead-lag relationship."
    at0 = next((r for r in rows if r["offset"] == 0), None)
    lead = [r for r in rows if r["offset"] > 0]
    if not lead:
        return "No positive-offset correlations could be computed."
    best = min(lead, key=lambda r: r["r"])
    str0 = abs(at0["r"]) if at0 else 0.0
    verb = "leads" if abs(best["r"]) > str0 + 0.03 and best["r"] < 0 else (
        "shows no clear lead over" if abs(best["r"]) < 0.1 else "moves with")
    sign = "negatively" if best["r"] < 0 else "positively"
    msg = (
        f"Pooled across all analysed neighborhoods, the complaint signal {verb} "
        f"home-value growth: the strongest forward correlation is r={best['r']} at "
        f"a {best['offset']}-month offset ({sign} associated), vs "
        f"r={at0['r'] if at0 else 'n/a'} at offset 0. "
    )
    # Call out the "sharpest rise" subgroup if it shows a clearer forward signal.
    rise = [r for r in pooled.get("top_rising", []) if r["r"] is not None and r["offset"] > 0]
    if rise:
        rbest = min(rise, key=lambda r: r["r"])
        if rbest["r"] < -0.2:
            msg += (
                f"In the subset of neighborhoods with the sharpest complaint "
                f"increases, the relationship is stronger — r={rbest['r']} at "
                f"{rbest['offset']} months (p={rbest['p']}, n={rbest['n']}) — a "
                f"tentative lead exactly where the hypothesis predicts one, but on "
                f"a small sample. "
            )
    msg += "This is an exploratory, correlational result — not causal."
    return msg

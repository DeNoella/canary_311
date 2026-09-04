"""Download Zillow Home Value Index (ZHVI), ZIP-code level.

Free public CSV from Zillow Research. Wide format: one row per ZIP, one column
per month. We keep NYC ZIPs and melt to long (zip, month, zhvi).
"""
from __future__ import annotations

import io

import pandas as pd
import requests

from .config import CFG, NYC_ZIP_MAX, NYC_ZIP_MIN, RAW

# Fallback URLs in case the primary smoothed+SA series is unavailable.
_URLS = [
    CFG.zhvi_url,
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_month.csv",
]


def _download() -> pd.DataFrame:
    last_err: Exception | None = None
    for url in _URLS:
        try:
            r = requests.get(url, timeout=180,
                             headers={"User-Agent": "canary/0.1"})
            r.raise_for_status()
            return pd.read_csv(io.StringIO(r.text))
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"Could not download ZHVI CSV: {last_err}")


def fetch_zhvi(force: bool = False) -> pd.DataFrame:
    out = RAW / "zillow_zhvi_nyc.csv"
    if out.exists() and not force:
        return pd.read_csv(out, dtype={"zip": str})

    raw = _download().copy()
    RAW.joinpath("zillow_zhvi_raw.csv").write_text(raw.to_csv(index=False))

    id_cols = [c for c in raw.columns if not c[:4].isdigit()]
    month_cols = [c for c in raw.columns if c[:4].isdigit()]

    zip_col = "RegionName" if "RegionName" in raw.columns else id_cols[0]
    raw["zip"] = (
        raw[zip_col].astype(str).str.extract(r"(\d+)")[0].str.zfill(5)
    )
    # Restrict to NYC by ZIP range (works even if City/Metro labels vary).
    zi = pd.to_numeric(raw["zip"], errors="coerce")
    nyc = raw[(zi >= NYC_ZIP_MIN) & (zi <= NYC_ZIP_MAX)].copy()

    long = nyc.melt(
        id_vars=["zip"], value_vars=month_cols,
        var_name="date", value_name="zhvi",
    )
    long["month"] = pd.to_datetime(long["date"]).dt.strftime("%Y-%m")
    long["zhvi"] = pd.to_numeric(long["zhvi"], errors="coerce")
    long = long.dropna(subset=["zhvi"])
    # Keep a small buffer before the window so we can compute a lagged MoM.
    keep = set(CFG.months())
    y, m = (int(x) for x in CFG.start_month.split("-"))
    for _ in range(13):  # add 13 months of lead-in
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        keep.add(f"{y:04d}-{m:02d}")
    long = long[long["month"].isin(keep)]
    long = long[["zip", "month", "zhvi"]].sort_values(["zip", "month"])
    long.to_csv(out, index=False)
    print(f"  zhvi: wrote {len(long):,} rows across {long['zip'].nunique()} ZIPs -> {out}")
    return long


if __name__ == "__main__":
    fetch_zhvi()

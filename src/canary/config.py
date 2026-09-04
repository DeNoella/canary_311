"""Central configuration: paths, date ranges, and tunable parameters.

Everything here is overridable via environment variables so the pipeline can be
run at different scales without editing code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
CACHE = ROOT / "cache"
OUTPUTS = ROOT / "outputs"

for _p in (RAW, PROCESSED, CACHE, OUTPUTS):
    _p.mkdir(parents=True, exist_ok=True)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    # --- Analysis window -------------------------------------------------
    # 3 full years of monthly data ending the month before "now".
    start_month: str = _env_str("CANARY_START", "2022-09")
    end_month: str = _env_str("CANARY_END", "2025-08")

    # --- NYC 311 (Socrata dataset erm2-nwe9) --------------------------
    socrata_domain: str = "data.cityofnewyork.us"
    socrata_dataset: str = "erm2-nwe9"
    socrata_app_token: str = _env_str("SOCRATA_APP_TOKEN", "")
    # Bounded sample of individual complaints used for theme discovery.
    sample_rows_per_month: int = _env_int("CANARY_SAMPLE_PER_MONTH", 4000)
    sample_max_rows: int = _env_int("CANARY_SAMPLE_MAX", 150_000)

    # --- Zillow ZHVI (ZIP level, smoothed, seasonally adjusted) --------
    zhvi_url: str = _env_str(
        "CANARY_ZHVI_URL",
        "https://files.zillowstatic.com/research/public_csvs/zhvi/"
        "Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    )

    # --- Theme clustering --------------------------------------------------
    n_themes: int = _env_int("CANARY_N_THEMES", 14)
    embed_model: str = _env_str("CANARY_EMBED_MODEL", "all-MiniLM-L6-v2")

    # --- Signals / lead-lag --------------------------------------------
    leadlag_offsets: tuple[int, ...] = (0, 3, 6, 12)
    top_n_zips: int = _env_int("CANARY_TOP_N", 5)
    min_months_for_corr: int = 12
    # A ZIP must have at least this many total sampled complaints to get themes.
    min_zip_complaints: int = 150

    def months(self) -> list[str]:
        """Inclusive list of 'YYYY-MM' strings across the analysis window."""
        y, m = (int(x) for x in self.start_month.split("-"))
        ey, em = (int(x) for x in self.end_month.split("-"))
        out: list[str] = []
        while (y, m) <= (ey, em):
            out.append(f"{y:04d}-{m:02d}")
            m += 1
            if m == 13:
                m, y = 1, y + 1
        return out


CFG = Config()

# NYC ZIP codes broadly fall in these ranges (Bronx/Manhattan 100xx-104xx,
# Staten Island 103xx, Queens 110xx-116xx, Brooklyn 112xx). Used as a coarse
# sanity filter after standardising ZIP strings.
NYC_ZIP_MIN = 10001
NYC_ZIP_MAX = 11697

# True when the pipeline is running on the synthetic test dataset.
IS_SYNTHETIC = (RAW / "SYNTHETIC").exists()

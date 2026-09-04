"""Fetch an NYC 311 dataset from Kaggle and build the pipeline's raw inputs.

Requires a Kaggle API token: ~/.kaggle/access_token  (KGAT_... , CLI >= 1.8)
or a legacy ~/.kaggle/kaggle.json.  See https://www.kaggle.com/settings -> API.

Usage:
    uv run python scripts/fetch_kaggle_311.py --search
    uv run python scripts/fetch_kaggle_311.py --dataset <owner/slug> [--file name.csv]

The source CSV (often many GB, sometimes inside a .zip) is streamed in chunks --
never fully loaded into memory. It produces, directly in data/raw/:

    nyc311_monthly_counts.csv   true monthly counts per (month, zip, type)
    nyc311_sample.csv           month-stratified reservoir sample (~CANARY_SAMPLE_MAX)
    LOCAL_SOURCE                marker so the pipeline skips the (blocked) API

Then just run:  uv run canary --refresh
"""
from __future__ import annotations

import argparse
import io
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from canary.config import CFG, RAW  # noqa: E402

KAGGLE_DIR = RAW / "kaggle"
CHUNK = 400_000
RNG = np.random.default_rng(42)

DEFAULT_QUERIES = ["nyc 311 service requests", "new york 311", "311 service requests"]

# canonical -> possible source header names (matched case-insensitively).
# NYC renamed several 311 columns in 2025 ("Problem (formerly Complaint Type)").
ALIASES = {
    "created_date": ["created date", "created_date", "createddate"],
    "complaint_type": ["complaint type", "complaint_type", "complainttype",
                       "problem (formerly complaint type)", "problem"],
    "descriptor": ["descriptor", "problem detail (formerly descriptor)",
                   "problem detail"],
    "additional_details": ["additional details", "resolution description"],
    "incident_zip": ["incident zip", "incident_zip", "zip", "zipcode", "zip code"],
    "borough": ["borough"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "long"],
    "unique_key": ["unique key", "unique_key", "uniquekey"],
}
REQUIRED = {"created_date", "complaint_type", "descriptor", "incident_zip"}
DATE_FORMATS = ["%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S"]


def _api():
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    return api


def search() -> None:
    api = _api()
    seen: set[str] = set()
    for q in DEFAULT_QUERIES:
        print(f"\n### {q!r}")
        for d in api.dataset_list(search=q, sort_by="hottest"):
            ref = str(d)
            if ref in seen:
                continue
            seen.add(ref)
            print(f"  {ref:55s} size={getattr(d, 'size', '?')} "
                  f"updated={getattr(d, 'lastUpdated', '?')}")
    print("\nThen: --dataset <owner/slug>")


def _source(dataset: str) -> Path:
    """Return a local .csv or .zip for the dataset, downloading if needed."""
    KAGGLE_DIR.mkdir(parents=True, exist_ok=True)
    have = sorted(
        [*KAGGLE_DIR.glob("**/*.csv"), *KAGGLE_DIR.glob("**/*.zip")],
        key=lambda p: p.stat().st_size, reverse=True,
    )
    if have and have[0].stat().st_size > 1_000_000:
        print(f"reusing {have[0].name} ({have[0].stat().st_size / 1e9:.2f} GB)")
        return have[0]
    print(f"downloading {dataset} …")
    _api().dataset_download_files(dataset, path=str(KAGGLE_DIR), quiet=False,
                                 unzip=False)
    have = sorted(
        [*KAGGLE_DIR.glob("**/*.csv"), *KAGGLE_DIR.glob("**/*.zip")],
        key=lambda p: p.stat().st_size, reverse=True,
    )
    if not have:
        sys.exit(f"no csv/zip found under {KAGGLE_DIR}")
    return have[0]


def _open_stream(src: Path, file_hint: str | None):
    """Yield (header_list, row_iterator_factory) for a .csv or .zip source."""
    if src.suffix == ".zip":
        zf = zipfile.ZipFile(src)
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        name = next((n for n in names if file_hint and Path(n).name == file_hint),
                    max(names, key=lambda n: zf.getinfo(n).file_size))
        print(f"streaming {name} from {src.name}")

        def reader(usecols):
            with zf.open(name) as raw:
                yield from pd.read_csv(io.TextIOWrapper(raw, encoding="utf-8",
                                                       errors="replace"),
                                      usecols=usecols, dtype=str, chunksize=CHUNK,
                                      low_memory=False)

        with zf.open(name) as raw:
            header = list(pd.read_csv(io.TextIOWrapper(raw, encoding="utf-8"),
                                      nrows=0).columns)
        return header, reader

    print(f"streaming {src}")

    def reader(usecols):
        yield from pd.read_csv(src, usecols=usecols, dtype=str, chunksize=CHUNK,
                               low_memory=False)

    header = list(pd.read_csv(src, nrows=0).columns)
    return header, reader


def _colmap(header: list[str]) -> dict[str, str]:
    low = {h.lower().strip(): h for h in header}
    out: dict[str, str] = {}
    for canon, opts in ALIASES.items():
        for o in opts:
            if o in low:
                out[canon] = low[o]
                break
    missing = REQUIRED - out.keys()
    if missing:
        sys.exit(f"source CSV missing required columns: {missing}\nheader: {header}")
    return out


def _parse_dates(s: pd.Series) -> pd.Series:
    for fmt in DATE_FORMATS:
        out = pd.to_datetime(s, format=fmt, errors="coerce")
        if out.notna().mean() > 0.7:
            return out
    return pd.to_datetime(s, errors="coerce")


def build(src: Path, file_hint: str | None) -> None:
    header, reader = _open_stream(src, file_hint)
    cmap = _colmap(header)
    usecols = list(cmap.values())
    ren = {v: k for k, v in cmap.items()}
    has_extra = "additional_details" in cmap

    keep_months = set(CFG.months())
    y, m = (int(x) for x in CFG.start_month.split("-"))
    for _ in range(13):
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        keep_months.add(f"{y:04d}-{m:02d}")

    counts: dict[tuple, int] = defaultdict(int)
    per_month_cap = max(1000, CFG.sample_max_rows // len(CFG.months()))
    reservoir: dict[str, list] = defaultdict(list)
    seen_pm: dict[str, int] = defaultdict(int)

    total = kept = 0
    for ci, chunk in enumerate(reader(usecols)):
        chunk = chunk.rename(columns=ren)
        total += len(chunk)
        chunk["month"] = _parse_dates(chunk["created_date"]).dt.strftime("%Y-%m")
        chunk = chunk[chunk["month"].isin(keep_months)]
        if chunk.empty:
            if ci % 10 == 0:
                print(f"  chunk {ci}: read {total:,}, kept {kept:,}")
            continue
        chunk["incident_zip"] = chunk["incident_zip"].astype(str).str.extract(r"(\d{5})")[0]
        chunk = chunk.dropna(subset=["incident_zip", "complaint_type"])
        desc = chunk["descriptor"].fillna("").astype(str)
        if has_extra:
            desc = (desc + " " + chunk["additional_details"].fillna("").astype(str)).str.strip()
        chunk["descriptor"] = desc
        kept += len(chunk)

        inwin = chunk[chunk["month"].isin(CFG.months())]
        for (mo, zp, ct), n in (
            inwin.groupby(["month", "incident_zip", "complaint_type"]).size().items()
        ):
            counts[(mo, zp, ct)] += int(n)

        s = inwin[inwin["descriptor"].str.len() > 0]
        cols = ["month", "incident_zip", "complaint_type", "descriptor", "created_date"]
        cols += [c for c in ("borough", "latitude", "longitude", "unique_key") if c in s.columns]
        for row in s[cols].itertuples(index=False, name="R"):
            mo = row.month
            seen_pm[mo] += 1
            buf = reservoir[mo]
            if len(buf) < per_month_cap:
                buf.append(row)
            elif (j := RNG.integers(0, seen_pm[mo])) < per_month_cap:
                buf[j] = row
        if ci % 10 == 0:
            print(f"  chunk {ci}: read {total:,}, kept {kept:,} in-range")

    cdf = pd.DataFrame(
        [(mo, zp, ct, n) for (mo, zp, ct), n in counts.items()],
        columns=["month", "incident_zip", "complaint_type", "n"],
    ).sort_values(["month", "incident_zip", "complaint_type"])
    cdf.to_csv(RAW / "nyc311_monthly_counts.csv", index=False)
    print(f"\nnyc311_monthly_counts.csv: {len(cdf):,} rows | "
          f"{cdf['month'].min()}..{cdf['month'].max()} | "
          f"{cdf['incident_zip'].nunique()} ZIPs | {int(cdf['n'].sum()):,} complaints")

    sdf = pd.DataFrame([r._asdict() for buf in reservoir.values() for r in buf])
    if len(sdf) > CFG.sample_max_rows:
        sdf = sdf.sample(CFG.sample_max_rows, random_state=42)
    sdf = sdf.rename(columns={"latitude": "latitude", "longitude": "longitude"})
    sdf.to_csv(RAW / "nyc311_sample.csv", index=False)
    print(f"nyc311_sample.csv: {len(sdf):,} rows | {sdf['month'].nunique()} months")

    (RAW / "LOCAL_SOURCE").write_text(
        f"kaggle:{src.name}\nwindow={CFG.start_month}..{CFG.end_month}\n"
        f"source_months={cdf['month'].min()}..{cdf['month'].max()}\n"
    )
    (RAW / "SYNTHETIC").unlink(missing_ok=True)
    (RAW / "nyc311_export.csv").unlink(missing_ok=True)
    print("\nwrote LOCAL_SOURCE.  Next:  uv run canary --refresh")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--dataset")
    ap.add_argument("--file")
    a = ap.parse_args()
    if a.search or not a.dataset:
        search()
        return
    build(_source(a.dataset), a.file)


if __name__ == "__main__":
    main()

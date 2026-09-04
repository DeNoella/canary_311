"""End-to-end orchestrator for the Canary pipeline.

    canary --help
    canary                 # run everything, using cached pulls if present
    canary --refresh       # re-download the raw data
    canary --steps ingest,clean,themes,signals,leadlag,export,findings

Every step is free and local. No paid APIs are called anywhere.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import pandas as pd

from . import clean, export, ingest_311, ingest_zillow, leadlag, signals, themes
from .config import CFG, IS_SYNTHETIC, PROCESSED, ROOT

ALL_STEPS = ["ingest", "clean", "themes", "signals", "leadlag", "export", "findings"]


def _findings_md(leadlag_res: dict) -> str:
    f = json.loads((ROOT / "outputs" / "findings.json").read_text())
    ll = leadlag_res
    pooled = ll.get("pooled", {}).get("all_shared", [])
    rows = "\n".join(
        f"| {r['offset']} mo | {r['r'] if r['r'] is not None else 'n/a'} | "
        f"{r['p'] if r['p'] is not None else 'n/a'} | {r['n']} |"
        for r in pooled
    )
    rising = ll.get("pooled", {}).get("top_rising", [])
    rrows = "\n".join(
        f"| {r['offset']} mo | {r['r'] if r['r'] is not None else 'n/a'} | "
        f"{r['p'] if r['p'] is not None else 'n/a'} | {r['n']} |"
        for r in rising
    )
    themes_list = "\n".join(
        f"- **{t['theme']}** ({t['n']:,} complaints)"
        for t in f.get("top_themes_overall", [])[:8]
    )
    banner = (
        "> ⚠️ **Generated from SYNTHETIC test data — these are NOT real findings.** "
        "Re-run with a real NYC 311 export at `data/raw/nyc311_export.csv`.\n\n"
        if IS_SYNTHETIC else ""
    )
    return f"""# Canary — Findings

{banner}**Question.** In a NYC neighborhood (ZIP), does a rise in 311-complaint activity
act as an *early-warning signal* that shows up **before** home values weaken?

**Window.** {CFG.start_month} → {CFG.end_month} ({len(CFG.months())} months).
**Coverage.** {f['n_zips']} ZIP codes present in both NYC 311 and Zillow ZHVI.
**Complaint sample.** {f.get('n_zips', '?')} ZIPs · month-stratified sample used
for theme discovery; **true** monthly volumes come from a server-side aggregate
of the full dataset.
**Embeddings.** `{f.get('embedding_method')}` (fully local, $0).

---

## Headline

{f.get('headline', '')}

## Lead-lag: complaint pressure (volume z-score) vs. ZHVI month-over-month change

Pearson correlation between the complaint signal at month *T* and ZHVI growth at
month *T + offset*. A **negative** r at a **positive** offset is the pattern we'd
expect if complaints lead decline.

**Pooled across all shared ZIPs**

| Offset | r | p | n |
|---|---|---|---|
{rows}

**Pooled across the ZIPs with the sharpest complaint increases**

| Offset | r | p | n |
|---|---|---|---|
{rrows}

Best forward correlation (pooled, all ZIPs):
`{f.get('best_pooled_all', {})}`

## Most common complaint themes discovered (unsupervised, no city labels)

{themes_list}

---

## Interpretation

- Read the tables above literally. If the negative correlations at 3/6/12-month
  offsets are **stronger** than at offset 0, that is weak evidence the complaint
  signal *leads*. If offset 0 is strongest, they move *together*. If all |r| are
  small (< ~0.1), there is **no clear relationship** in this window.
- The pooled estimate is the most stable; per-ZIP estimates (in the dashboard)
  are noisy given only ~{len(CFG.months())} monthly points each.

## Limitations (do not overclaim)

- **Correlational, not causal.** Many things move complaints and prices together
  (season, economy, local development).
- **One city, one 3-year window.** No out-of-sample or cross-city check.
- **Sampled text.** Theme mix is from a month-stratified sample, not every call.
- **ZHVI is a smoothed, seasonally-adjusted index** with partial ZIP coverage;
  it is itself a lagging, modelled measure.
- **Multiple comparisons.** Several ZIPs × 4 offsets — some "significant" p-values
  are expected by chance.
- **Outliers not winsorized.** A few ZIP-months have anomalous complaint spikes
  (e.g. a single-building campaign); raw volumes are used as-is.
- **Source.** 311 is a public dataset snapshot; ZIP↔Zillow coverage limits the
  panel to 175 ZIPs.

## With more time

- Add rent (Zillow ZORI), vacancy, permits, and crime as additional lagging refs.
- Proper panel model (fixed effects per ZIP + month) instead of pooled Pearson.
- Granger causality / distributed-lag regression with seasonal controls.
- Expand to 8–10 years and 3–4 cities; hold out a test period.
- Swap KMeans for HDBSCAN + c-TF-IDF (BERTopic-style) for cleaner themes.
"""


def run(steps: list[str], refresh: bool = False) -> None:
    t0 = time.time()
    steps = [s for s in ALL_STEPS if s in steps]
    print(f"canary pipeline · steps={steps} · refresh={refresh}")

    counts_raw = sample_raw = zhvi_raw = None
    if "ingest" in steps:
        print("[1/7] ingest")
        counts_raw = ingest_311.fetch_monthly_counts(force=refresh)
        sample_raw = ingest_311.fetch_sample(force=refresh)
        zhvi_raw = ingest_zillow.fetch_zhvi(force=refresh)

    bundle = None
    if "clean" in steps:
        print("[2/7] clean")
        counts_raw = counts_raw if counts_raw is not None else ingest_311.fetch_monthly_counts()
        sample_raw = sample_raw if sample_raw is not None else ingest_311.fetch_sample()
        zhvi_raw = zhvi_raw if zhvi_raw is not None else ingest_zillow.fetch_zhvi()
        bundle = clean.run(counts_raw, sample_raw, zhvi_raw)

    if "themes" in steps:
        print("[3/7] themes")
        sample = (bundle["sample"] if bundle else
                  pd.read_parquet(PROCESSED / "complaints_sample.parquet"))
        themed = themes.run(sample)
    else:
        themed = None

    sig = None
    if "signals" in steps:
        print("[4/7] signals")
        counts = (bundle["counts"] if bundle else
                  pd.read_parquet(PROCESSED / "complaints_counts.parquet"))
        themed = (themed if themed is not None else
                  pd.read_parquet(PROCESSED / "complaints_themes.parquet"))
        sig = signals.run(counts, themed)

    ll = None
    if "leadlag" in steps:
        print("[5/7] leadlag")
        if sig is None:
            sig = {
                "timeseries": pd.read_parquet(PROCESSED / "signal_timeseries.parquet"),
                "summary": pd.read_parquet(PROCESSED / "zip_summary.parquet"),
            }
        zhvi = (bundle["zhvi"] if bundle else
                pd.read_parquet(PROCESSED / "zhvi.parquet"))
        ll = leadlag.run(sig["timeseries"], sig["summary"], zhvi)

    if "export" in steps:
        print("[6/7] export")
        ll = ll if ll is not None else json.loads((PROCESSED / "leadlag.json").read_text())
        export.run(bundle or {}, ll)

    if "findings" in steps:
        print("[7/7] findings")
        ll = ll if ll is not None else json.loads((PROCESSED / "leadlag.json").read_text())
        (ROOT / "FINDINGS.md").write_text(_findings_md(ll))
        print(f"  findings: wrote {ROOT / 'FINDINGS.md'}")

    print(f"done in {time.time() - t0:.0f}s")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="canary", description=__doc__)
    p.add_argument("--refresh", action="store_true",
                   help="re-download raw data (ignore caches)")
    p.add_argument("--steps", default=",".join(ALL_STEPS),
                   help=f"comma list from: {','.join(ALL_STEPS)}")
    a = p.parse_args(argv)
    run([s.strip() for s in a.steps.split(",") if s.strip()], refresh=a.refresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())

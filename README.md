# Canary

**An early-warning signal for neighborhood decline from NYC 311 complaint data.**

Canary tests a simple hypothesis: **when residents start complaining more — and
about different things — does that show up *before* home values weaken?** It
ingests NYC 311 service requests and Zillow's Home Value Index (ZHVI) at the ZIP
level, discovers complaint *themes* with a fully local NLP model, builds a
monthly "complaint pressure" signal per neighborhood, and cross-correlates that
signal against home-value growth at 0/3/6/12-month offsets.

The result is an interactive **3D dashboard**: a live map of NYC where each ZIP is
an animated bar (height = complaint volume, colour = complaint pressure), a month
scrubber to watch the city change over three years, and a per-ZIP panel with the
complaint-vs-home-value chart, the lead-lag table, and the emerging complaint
themes.

> **Honesty note:** this is an **exploratory, correlational** portfolio project,
> not a causal model and not a forecast. See [`FINDINGS.md`](FINDINGS.md) for what
> the data actually shows and the limitations.

**New here?** [`HOW_TO_RUN.md`](HOW_TO_RUN.md) is a plain-language, step-by-step
guide. The dashboard itself also has a **Home** page and a **How it works** page
explaining the project, methods, technologies, and data sources in simple terms.

---

## Architecture

```
NYC 311  ─┐                      ┌─  outputs/*.json  ──►  FastAPI  ──►  React + Three.js
          ├─►  canary pipeline  ─┤                        (api/)         (frontend/)
Zillow  ──┘   (src/canary/)      └─  data/processed/*.parquet
```

| Layer | Stack | What it does |
|---|---|---|
| **Pipeline** | Python 3.12, pandas, scikit-learn, scipy | ingest → clean → theme clustering → signal series → lead-lag → JSON export |
| **NLP** | `sentence-transformers` (`all-MiniLM-L6-v2`), **local**, with a scikit-learn TF-IDF+SVD fallback | unsupervised complaint themes, TF-IDF auto-labels |
| **API** | FastAPI + Uvicorn | serves the pipeline's JSON outputs |
| **Frontend** | React 18, Vite, TypeScript, `@react-three/fiber` + `drei` (Three.js) | animated 3D city, month scrubber, per-ZIP detail panel |

**Cost: $0.** Only free public data (NYC Open Data, Zillow Research) and free,
local, open-source tools. No paid APIs are called anywhere in the pipeline.

---

## Setup

### Prerequisites
- **[uv](https://docs.astral.sh/uv/)** (`curl -LsSf https://astral.sh/uv/install.sh | sh`) — manages Python 3.12 + deps
- **Node 18+** and npm — for the frontend

### Install

```bash
git clone <this repo> canary && cd canary

# Python pipeline + API (uv provisions Python 3.12 automatically)
uv sync                     # core pipeline + API
uv sync --extra embeddings  # + sentence-transformers (optional; TF-IDF fallback otherwise)

# Frontend
cd frontend && npm install && cd ..
```

---

## Getting the data

### Zillow ZHVI
Downloaded automatically by the pipeline from Zillow Research (public CSV, no auth).

### NYC 311

The pipeline can get 311 three ways; it picks the first that applies:

1. **`data/raw/LOCAL_SOURCE` marker present** → uses the prebuilt
   `nyc311_monthly_counts.csv` + `nyc311_sample.csv` (written by the Kaggle
   script below). This is what the shipped analysis uses.
2. **`data/raw/nyc311_export.csv` present** → a raw NYC Open Data CSV export;
   columns are matched case-insensitively (handles the 2025 "Problem (formerly
   Complaint Type)" rename).
3. **otherwise** → the Socrata API (`data.cityofnewyork.us`, `erm2-nwe9`): a
   server-side aggregate for true monthly volumes + a month-stratified ~150k-row
   sample for themes.

> ⚠️ The Socrata API (option 3) is **WAF-blocked from some networks/hosts**
> (every request returns HTTP 403). If that's you, use the Kaggle path.

#### Kaggle path (used for the shipped results)

```bash
uv sync --extra kaggle

# Kaggle API token — kaggle.com/settings → "API tokens" → generate (KGAT_…):
mkdir -p ~/.kaggle && echo "KGAT_xxx" > ~/.kaggle/access_token && chmod 600 ~/.kaggle/access_token
# (or a legacy kaggle.json in ~/.kaggle/)

uv run python scripts/fetch_kaggle_311.py --search                    # list candidates
uv run python scripts/fetch_kaggle_311.py --dataset pearsejim01/nyc-311-requests
uv run canary --refresh
```

The dataset's single CSV (~12 GB) is **streamed in chunks** — never fully loaded
— to produce the counts + sample CSVs and the `LOCAL_SOURCE` marker. The script
prints the file's month coverage; if it doesn't span the default
**2022-09 → 2025-08** window, set `CANARY_START` / `CANARY_END` and re-run.

#### No data / offline — synthetic

```bash
uv run python scripts/make_synthetic_311.py   # writes a fake data/raw/nyc311_export.csv
uv run canary
```
Every output is stamped **SYNTHETIC** so it can't be mistaken for real findings.
Delete `data/raw/SYNTHETIC` (and `nyc311_export.csv`) to switch back.

---

## Run

```bash
# 1. Build everything (uses caches; --refresh to re-pull raw data)
uv run canary

#    or run individual steps:
uv run canary --steps ingest,clean,themes,signals,leadlag,export,findings

# 2. Start the API
uv run uvicorn api.main:app --port 8000

# 3. Start the dashboard (separate terminal)
cd frontend && npm run dev        # http://localhost:5173  (proxies /api to :8000)
```

## Deploy (static, no backend)

The dashboard runs with **no backend** by baking the pipeline's JSON output into
the site. `npm run dev` / `npm run build` first run `scripts/sync-data.mjs`,
which copies `outputs/` → `frontend/public/data/` (a snapshot of that folder is
committed so deploys work without running the pipeline). In a production build
the app reads `/data/*.json` directly; set `VITE_API_BASE` only if you want it to
talk to a live FastAPI instance instead.

**Vercel:** import the repo — the root [`vercel.json`](vercel.json) already sets
build command `cd frontend && npm ci && npm run build` and output
`frontend/dist`, so no dashboard settings are needed. To refresh the deployed
data: re-run `uv run canary`, then `cd frontend && npm run sync-data`, commit
`frontend/public/data/`, and push.

Any static host works: `cd frontend && npm run build` and serve `frontend/dist/`.

### Configuration (env vars)

| Var | Default | Meaning |
|---|---|---|
| `CANARY_START` / `CANARY_END` | `2022-09` / `2025-08` | analysis window (`YYYY-MM`) |
| `CANARY_SAMPLE_MAX` | `150000` | max sampled complaint rows for theming |
| `CANARY_N_THEMES` | `14` | KMeans clusters |
| `SOCRATA_APP_TOKEN` | — | optional, raises Socrata rate limit (free) |
| `CANARY_311_CSV` | `data/raw/nyc311_export.csv` | path to a manual 311 export |
| `CANARY_ZHVI_URL` | Zillow ZHVI ZIP CSV | override the ZHVI source |

---

## Project layout

```
src/canary/         pipeline package
  ingest_311.py     Socrata pull (aggregate counts + stratified sample) or local CSV
  ingest_zillow.py  ZHVI download + reshape to long
  clean.py          ZIP/date standardisation, align to shared ZIPs
  themes.py         local embeddings → KMeans → TF-IDF labels
  signals.py        monthly volume / velocity / pressure z-score / theme mix
  leadlag.py        Pearson r vs ZHVI MoM at offsets 0/3/6/12 (+ pooled)
  export.py         write outputs/*.json
  pipeline.py       CLI orchestrator (`canary`)
api/main.py         FastAPI, serves outputs/
frontend/           React + Three.js dashboard
scripts/            fetch_kaggle_311.py (streamed loader) + make_synthetic_311.py
data/raw|processed  raw pulls / cleaned parquet (gitignored)
outputs/            JSON consumed by the API/frontend (gitignored)
FINDINGS.md         1-page written summary (regenerated by the pipeline)
```

---

## Findings (summary)

The full write-up is in [`FINDINGS.md`](FINDINGS.md), regenerated on every run.

On the shipped data (NYC, 2022-09 → 2025-08, 175 ZIPs, ~9.9M complaints), the
pooled correlation between complaint pressure and ZHVI month-over-month growth is
**weak but significant and negative**, and strongest at **0–3 months**
(r ≈ −0.09, p < 0.001) — i.e. roughly *contemporaneous*, not a clear lead. The
one place a lead-shaped signal appears is the **subset of ZIPs with the sharpest
complaint increases**, where r ≈ −0.27 at a 6-month offset (p ≈ 0.003, n = 116) —
suggestive but a small sample. Net: **not a validated early-warning signal on
this window**, but a hypothesis worth pursuing with a proper panel model and a
longer horizon. Per-ZIP estimates in the dashboard are noisy (~36 points each).
(Synthetic runs carry a warning banner.)

## What I'd do with more time

- Add rent (Zillow ZORI), residential vacancy, building permits, and crime as
  additional lagging references instead of home value alone.
- Replace pooled Pearson with a proper panel model (ZIP + month fixed effects)
  and a distributed-lag / Granger-causality specification with seasonal controls.
- Extend to 8–10 years and 3–4 cities, with a held-out test period.
- Swap KMeans for HDBSCAN + class-based TF-IDF (BERTopic-style) for cleaner,
  more interpretable emerging themes, and track theme *trajectories* per ZIP.
- Geometry-accurate choropleth (ZCTA shapefiles) instead of sampled centroids.

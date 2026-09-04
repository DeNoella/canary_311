# How to run Canary

Two ways in. Pick the one that matches you.

---

## A. "I just want to look at it"

You need two things running at once: the **data service** (serves the numbers)
and the **website** (shows them). Open two terminal windows.

**Terminal 1 — data service**

```bash
cd ~/Desktop/labs/canary
export PATH="$HOME/.local/bin:$PATH"
make api
```

Wait until it says `Application startup complete`.

**Terminal 2 — website**

```bash
cd ~/Desktop/labs/canary
make dev
```

It will print a line like `Local: http://localhost:5173/`.
**Open that link in your browser.** You'll land on the home page; click
**"Explore the map"** for the 3D view.

To stop: press `Ctrl + C` in each terminal.

> On the machine this was built on, everything is already installed and the data
> is already downloaded — section A is all you need.

---

## B. "I'm setting it up from scratch on a new computer"

### 1. Install the two prerequisites

- **uv** (runs the Python side):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Node.js 18 or newer** (runs the website): https://nodejs.org

### 2. Get the code

```bash
git clone https://github.com/DeNoella/canary_311.git canary
cd canary
export PATH="$HOME/.local/bin:$PATH"
```

### 3. Install everything

```bash
uv sync --extra embeddings --extra kaggle    # Python side
cd frontend && npm install && cd ..           # website side
```

### 4. Get the data

The city's own data website blocks automated downloads from some networks, so
Canary reads NYC 311 from a public **Kaggle** copy of the same official dataset.

1. Make a free account at https://www.kaggle.com
2. Go to **kaggle.com/settings → API tokens → generate a token** (starts with `KGAT_`)
3. Save it:
   ```bash
   mkdir -p ~/.kaggle
   echo "KGAT_your_token_here" > ~/.kaggle/access_token
   chmod 600 ~/.kaggle/access_token
   ```
4. Download and prepare the data (this streams a ~12 GB file — it can take
   10–20 minutes; it never loads the whole thing into memory):
   ```bash
   uv run python scripts/fetch_kaggle_311.py --dataset pearsejim01/nyc-311-requests
   ```

*No Kaggle account and just want to see it work?*
`uv run python scripts/make_synthetic_311.py` makes fake stand-in data instead
(every screen is clearly stamped **SYNTHETIC**).

### 5. Run the analysis

```bash
uv run canary --refresh
```

This downloads the Zillow home-value data, finds the complaint themes, builds the
signals, runs the comparison, and writes `FINDINGS.md`. Takes about 1–2 minutes.

### 6. Look at it

Same as **section A** above: `make api` in one terminal, `make dev` in another,
open the `localhost` link.

---

## What each command does

| Command | What it does |
|---|---|
| `uv run canary` | Re-runs the analysis using already-downloaded data (~1 min) |
| `uv run canary --refresh` | Same, but also re-downloads Zillow data first |
| `make api` | Starts the data service on port 8000 |
| `make dev` | Starts the website on port 5173 (development mode) |
| `make build` | Builds a static version of the website into `frontend/dist/` |
| `make synthetic` | Generates fake test data so you can run offline |
| `make check` | Runs the whole analysis + builds the website, as a sanity check |

## If something goes wrong

- **Website loads but the map is empty / "needs the data service running"** —
  the data service (`make api`) isn't running, or you haven't run
  `uv run canary` yet.
- **`uv: command not found`** — run `export PATH="$HOME/.local/bin:$PATH"` (or
  reopen the terminal).
- **`fetch_kaggle_311.py` says "401" or "403"** — the Kaggle token isn't set up.
  Re-check step 4. Expire and regenerate the token if needed.
- **The map takes a few seconds to appear** — that's normal; the 3D view builds
  itself the first time you open it.

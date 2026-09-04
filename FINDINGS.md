# Canary — Findings

**Question.** In a NYC neighborhood (ZIP), does a rise in 311-complaint activity
act as an *early-warning signal* that shows up **before** home values weaken?

**Window.** 2022-09 → 2025-08 (36 months).
**Coverage.** 175 ZIP codes present in both NYC 311 and Zillow ZHVI.
**Complaint sample.** 175 ZIPs · month-stratified sample used
for theme discovery; **true** monthly volumes come from a server-side aggregate
of the full dataset.
**Embeddings.** `sentence-transformers/all-MiniLM-L6-v2` (fully local, $0).

---

## Headline

Pooled across all shared ZIPs, the complaint signal shows no clear lead over home-value growth: the strongest forward correlation is r=-0.0837 at a 3-month offset (negatively associated), vs r=-0.0875 at offset 0. In the subset of ZIPs with the sharpest complaint increases, the relationship is stronger at r=-0.2716 at 6 months (p=0.0032, n=116) -- a tentative lead exactly where the hypothesis predicts one, but on a small sample. This is an exploratory, correlational result -- not causal.

## Lead-lag: complaint pressure (volume z-score) vs. ZHVI month-over-month change

Pearson correlation between the complaint signal at month *T* and ZHVI growth at
month *T + offset*. A **negative** r at a **positive** offset is the pattern we'd
expect if complaints lead decline.

**Pooled across all shared ZIPs**

| Offset | r | p | n |
|---|---|---|---|
| 0 mo | -0.0875 | 0.0 | 5233 |
| 3 mo | -0.0837 | 0.0 | 4714 |
| 6 mo | -0.0582 | 0.0002 | 4194 |
| 12 mo | -0.0089 | 0.6183 | 3146 |

**Pooled across the ZIPs with the sharpest complaint increases**

| Offset | r | p | n |
|---|---|---|---|
| 0 mo | -0.0248 | 0.7661 | 146 |
| 3 mo | -0.1693 | 0.0533 | 131 |
| 6 mo | -0.2716 | 0.0032 | 116 |
| 12 mo | 0.1687 | 0.1204 | 86 |

Best forward correlation (pooled, all ZIPs):
`{'offset': 3, 'r': -0.0837, 'p': 0.0, 'n': 4714}`

## Most common complaint themes discovered (unsupervised, no city labels)

- **sidewalk / sign / parking** (43,299 complaints)
- **noise / loud / helicopter** (33,955 complaints)
- **water / plumbing / sewer** (22,853 complaints)
- **trash / disposal / waste** (11,348 complaints)
- **tree / lost property / broken** (9,028 complaints)
- **quality / air / paint** (6,627 complaints)
- **smoking / electric / gas** (6,282 complaints)
- **animal / abuse / rodent** (6,166 complaints)

---

## Interpretation

- Read the tables above literally. If the negative correlations at 3/6/12-month
  offsets are **stronger** than at offset 0, that is weak evidence the complaint
  signal *leads*. If offset 0 is strongest, they move *together*. If all |r| are
  small (< ~0.1), there is **no clear relationship** in this window.
- The pooled estimate is the most stable; per-ZIP estimates (in the dashboard)
  are noisy given only ~36 monthly points each.

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

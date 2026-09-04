"""Generate a synthetic NYC-311-shaped CSV for offline pipeline testing.

This is NOT real data. It exists so the full pipeline + dashboard can be run
and demoed with zero network access. It writes:

    data/raw/nyc311_export.csv   (same column shape as a real Open Data export)
    data/raw/SYNTHETIC           (sentinel; makes the pipeline stamp a warning)

Run:  uv run python scripts/make_synthetic_311.py
Then: uv run canary
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from canary.config import CFG, RAW

RNG = np.random.default_rng(7)

# ~30 real NYC ZIPs with approximate centroids and a borough.
ZIPS = [
    ("10001", "MANHATTAN", 40.7506, -73.9971), ("10002", "MANHATTAN", 40.7157, -73.9862),
    ("10009", "MANHATTAN", 40.7264, -73.9786), ("10025", "MANHATTAN", 40.7987, -73.9666),
    ("10031", "MANHATTAN", 40.8235, -73.9500), ("10453", "BRONX", 40.8525, -73.9126),
    ("10456", "BRONX", 40.8300, -73.9083), ("10457", "BRONX", 40.8471, -73.8993),
    ("10458", "BRONX", 40.8624, -73.8890), ("10467", "BRONX", 40.8749, -73.8698),
    ("11201", "BROOKLYN", 40.6939, -73.9903), ("11205", "BROOKLYN", 40.6942, -73.9663),
    ("11206", "BROOKLYN", 40.7020, -73.9430), ("11207", "BROOKLYN", 40.6702, -73.8940),
    ("11212", "BROOKLYN", 40.6628, -73.9134), ("11216", "BROOKLYN", 40.6807, -73.9494),
    ("11221", "BROOKLYN", 40.6915, -73.9277), ("11233", "BROOKLYN", 40.6787, -73.9199),
    ("11237", "BROOKLYN", 40.7040, -73.9214), ("11385", "QUEENS", 40.7009, -73.8882),
    ("11101", "QUEENS", 40.7440, -73.9370), ("11103", "QUEENS", 40.7628, -73.9130),
    ("11106", "QUEENS", 40.7616, -73.9319), ("11368", "QUEENS", 40.7498, -73.8524),
    ("11373", "QUEENS", 40.7385, -73.8785), ("11432", "QUEENS", 40.7148, -73.7930),
    ("10301", "STATEN ISLAND", 40.6321, -74.0938), ("10304", "STATEN ISLAND", 40.6091, -74.0900),
    ("10314", "STATEN ISLAND", 40.6009, -74.1642), ("10467b", "BRONX", 40.8800, -73.8790),
]
ZIPS = [z for z in ZIPS if z[0].isdigit()]

# (complaint_type, [descriptors...]) — realistic pairs for theme clustering.
CATALOG = [
    ("Noise - Residential", ["Loud Music/Party", "Banging/Pounding", "Loud Talking"]),
    ("Noise - Street/Sidewalk", ["Loud Music/Party", "Loud Talking", "Car/Truck Music"]),
    ("HEAT/HOT WATER", ["ENTIRE BUILDING", "APARTMENT ONLY"]),
    ("UNSANITARY CONDITION", ["PESTS", "MOLD", "GARBAGE/RECYCLING STORAGE"]),
    ("PAINT/PLASTER", ["CEILING", "WALL"]),
    ("Illegal Parking", ["Blocked Hydrant", "Blocked Sidewalk", "Double Parked Blocking Traffic"]),
    ("Blocked Driveway", ["No Access", "Partial Access"]),
    ("Street Condition", ["Pothole", "Rough, Pitted or Cracked Roads", "Failed Street Repair"]),
    ("Water System", ["Hydrant Leaking", "No Water", "Water Quality Poor"]),
    ("Rodent", ["Rat Sighting", "Mouse Sighting", "Conditions Attracting Rodents"]),
    ("Sanitation Condition", ["Dirty Conditions", "Missed Collection", "Overflowing Litter Baskets"]),
    ("Homeless Person Assistance", ["People/Encampment on Street", "Person in Distress"]),
    ("Graffiti", ["Exterior Building", "Public Property"]),
    ("Sidewalk Condition", ["Cracked", "Trip Hazard", "Flag Raised/Uneven"]),
]


def main() -> None:
    months = CFG.months()
    n_m = len(months)
    # A few ZIPs get an upward complaint trend ("declining" neighborhoods).
    declining = set(RNG.choice([z[0] for z in ZIPS], size=6, replace=False))

    rows = []
    key = 1
    for zi, (zp, boro, lat, lon) in enumerate(ZIPS):
        base = RNG.integers(70, 220)
        trend = RNG.uniform(1.6, 3.2) if zp in declining else RNG.uniform(-0.4, 0.6)
        theme_drift = RNG.random() < 0.6  # some ZIPs shift theme mix over time
        for mi, month in enumerate(months):
            seasonal = 1 + 0.18 * np.sin(2 * np.pi * (mi % 12) / 12)
            level = max(15, (base + trend * mi) * seasonal * RNG.uniform(0.85, 1.15))
            count = int(level)
            # theme weights: drift toward "UNSANITARY/HEAT/Rodent" late for declining
            w = np.ones(len(CATALOG))
            if theme_drift:
                late = mi / n_m
                for idx, (ct, _) in enumerate(CATALOG):
                    if ct in ("HEAT/HOT WATER", "UNSANITARY CONDITION", "Rodent",
                              "Homeless Person Assistance"):
                        w[idx] += 2.5 * late * (2 if zp in declining else 1)
            w = w / w.sum()
            picks = RNG.choice(len(CATALOG), size=count, p=w)
            for p in picks:
                ct, descs = CATALOG[p]
                d = RNG.choice(descs)
                day = RNG.integers(1, 28)
                rows.append((
                    f"{month}-{day:02d}T{RNG.integers(0,23):02d}:00:00.000",
                    ct, d, zp, boro,
                    round(lat + RNG.normal(0, 0.004), 6),
                    round(lon + RNG.normal(0, 0.004), 6),
                    key,
                ))
                key += 1

    df = pd.DataFrame(rows, columns=[
        "Created Date", "Complaint Type", "Descriptor", "Incident Zip",
        "Borough", "Latitude", "Longitude", "Unique Key",
    ])
    df = df.sample(frac=1, random_state=1).reset_index(drop=True)
    out = RAW / "nyc311_export.csv"
    df.to_csv(out, index=False)
    (RAW / "SYNTHETIC").write_text("synthetic data generated by scripts/make_synthetic_311.py\n")
    print(f"wrote {len(df):,} rows -> {out}")
    print(f"declining ZIPs (upward complaint trend): {sorted(declining)}")


if __name__ == "__main__":
    main()

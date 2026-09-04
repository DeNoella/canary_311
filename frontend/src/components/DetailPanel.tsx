import { useEffect, useState } from "react";
import { api } from "../api";
import type { TimeSeries, ZipRecord, ZipThemes } from "../types";
import { TimeSeriesChart } from "./TimeSeriesChart";
import { LeadLagPanel } from "./LeadLagPanel";
import { ThemesTable } from "./ThemesTable";

interface Props {
  zip: string;
  record: ZipRecord;
  onClose: () => void;
}

export function DetailPanel({ zip, record, onClose }: Props) {
  const [ts, setTs] = useState<TimeSeries | null>(null);
  const [themes, setThemes] = useState<ZipThemes | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setTs(null);
    setThemes(null);
    setErr(null);
    api.timeseries(zip).then(setTs).catch((e) => setErr(String(e)));
    api.themes(zip).then(setThemes).catch(() => void 0);
  }, [zip]);

  const best = ts?.leadlag
    ?.filter((r) => r.offset > 0 && r.r != null)
    .sort((a, b) => (a.r ?? 0) - (b.r ?? 0))[0];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ marginTop: 0 }}>
          ZIP {zip} <span className="muted">{record.borough}</span>
        </h2>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "1px solid var(--border)",
            color: "var(--text-dim)",
            borderRadius: 6,
            cursor: "pointer",
            padding: "2px 8px",
          }}
        >
          ✕ back to findings
        </button>
      </div>

      <div>
        {record.in_top_volume && <span className="badge volume">top volume</span>}
        {record.in_top_rising && <span className="badge rising">sharp rise</span>}
      </div>

      <div className="card kpi" style={{ marginTop: 12 }}>
        <div>
          <div className="v">{record.total_volume.toLocaleString()}</div>
          <div className="l">total complaints</div>
        </div>
        <div>
          <div className="v">{record.latest_velocity.toFixed(0)}%</div>
          <div className="l">latest MoM velocity</div>
        </div>
        <div>
          <div className="v">{record.latest_volume_z.toFixed(2)}</div>
          <div className="l">complaint pressure (z)</div>
        </div>
      </div>

      <h2>Complaint volume vs. home values (ZHVI)</h2>
      {err && <p className="muted">Couldn't load series ({err}).</p>}
      {ts ? (
        <>
          <div className="card">
            <TimeSeriesChart ts={ts} offset={best?.offset ?? null} />
            <p className="muted" style={{ fontSize: 11, margin: "6px 0 0" }}>
              {best
                ? `Shaded: the ${best.offset}-month window where a complaint move is
                   compared against the later ZHVI move (strongest forward r =
                   ${best.r?.toFixed(3)}).`
                : "Not enough overlapping months for a forward correlation here."}
            </p>
          </div>

          <h2>Lead-lag: complaint pressure → ZHVI growth</h2>
          <div className="card">
            <LeadLagPanel rows={ts.leadlag} />
            <p className="muted" style={{ fontSize: 11, margin: "8px 0 0" }}>
              Negative r at a positive offset ⇒ a complaint rise now is followed
              by weaker home-value growth later. Per-ZIP estimates are noisy —
              read the pooled result in the findings view as the headline.
            </p>
          </div>
        </>
      ) : (
        !err && <p className="muted">Loading series…</p>
      )}

      <h2>Top complaint themes (unsupervised)</h2>
      {themes ? (
        <ThemesTable themes={themes} />
      ) : (
        <p className="muted">Loading themes…</p>
      )}
    </div>
  );
}

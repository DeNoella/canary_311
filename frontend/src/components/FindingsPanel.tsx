import type { Findings, Meta, ZipRecord } from "../types";

interface Props {
  findings: Findings | null;
  meta: Meta | null;
  zips: ZipRecord[];
  onPick: (zip: string) => void;
}

export function FindingsPanel({ findings, meta, zips, onPick }: Props) {
  const rising = [...zips]
    .sort((a, b) => b.trend_slope - a.trend_slope)
    .slice(0, 6);
  const pooled = findings?.pooled?.all_shared ?? [];

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Findings</h2>
      <div className="card">
        <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5 }}>
          {findings?.headline ?? "Run the pipeline to generate findings."}
        </p>
      </div>

      {pooled.length > 0 && (
        <>
          <h2>Pooled lead-lag (all shared ZIPs)</h2>
          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>Offset</th>
                  <th className="num">r</th>
                  <th className="num">p</th>
                  <th className="num">n</th>
                </tr>
              </thead>
              <tbody>
                {pooled.map((r) => (
                  <tr key={r.offset}>
                    <td>{r.offset} mo</td>
                    <td className="num">{r.r == null ? "—" : r.r.toFixed(3)}</td>
                    <td className="num">{r.p == null ? "—" : r.p.toFixed(3)}</td>
                    <td className="num">{r.n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted" style={{ fontSize: 11, marginBottom: 0 }}>
              Complaint pressure at month T vs. ZHVI month-over-month change at
              T+offset. Exploratory & correlational — not causal.
            </p>
          </div>
        </>
      )}

      <h2>Sharpest complaint increases — click to inspect</h2>
      <div className="card" style={{ padding: 4 }}>
        <table>
          <thead>
            <tr>
              <th>ZIP</th>
              <th>Borough</th>
              <th className="num">Trend</th>
              <th className="num">Pressure</th>
            </tr>
          </thead>
          <tbody>
            {rising.map((z) => (
              <tr
                key={z.zip}
                style={{ cursor: "pointer" }}
                onClick={() => onPick(z.zip)}
              >
                <td>{z.zip}</td>
                <td className="muted">{z.borough}</td>
                <td className="num">{(z.trend_slope * 100).toFixed(1)}%/mo</td>
                <td className="num">{z.latest_volume_z.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {findings?.top_themes_overall?.length ? (
        <>
          <h2>Most common discovered themes</h2>
          <div className="card">
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, lineHeight: 1.7 }}>
              {findings.top_themes_overall.slice(0, 8).map((t) => (
                <li key={t.theme_id}>
                  {t.theme} <span className="muted">· {t.n.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      ) : null}

      <h2>About</h2>
      <div className="card">
        <p className="muted" style={{ fontSize: 12, margin: 0, lineHeight: 1.6 }}>
          {meta?.dataset}
          <br />
          Window {meta?.window.start}–{meta?.window.end} ·{" "}
          {meta?.n_sampled_complaints?.toLocaleString()} sampled complaints ·{" "}
          {meta?.n_themes} themes via {meta?.embedding_method}.
        </p>
        {meta?.caveats?.length ? (
          <ul style={{ fontSize: 11, color: "var(--text-dim)", paddingLeft: 16, marginBottom: 0 }}>
            {meta.caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

import type { LeadLagPoint } from "../types";

// Renders the per-offset correlation table + a diverging bar for r.
export function LeadLagPanel({ rows }: { rows: LeadLagPoint[] }) {
  if (!rows?.length) return <p className="muted">No lead-lag result for this ZIP.</p>;
  const maxAbs = Math.max(0.001, ...rows.map((r) => Math.abs(r.r ?? 0)));

  return (
    <table>
      <thead>
        <tr>
          <th>Offset</th>
          <th className="num">r</th>
          <th className="num">p</th>
          <th className="num">n</th>
          <th style={{ width: 90 }}>lead ↔ lag</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const val = r.r ?? 0;
          const w = (Math.abs(val) / maxAbs) * 40;
          const sig = r.p != null && r.p < 0.05;
          return (
            <tr key={r.offset}>
              <td>{r.offset} mo</td>
              <td className="num" style={{ color: sig ? "var(--accent)" : undefined }}>
                {r.r == null ? "—" : r.r.toFixed(3)}
              </td>
              <td className="num">{r.p == null ? "—" : r.p.toFixed(3)}</td>
              <td className="num">{r.n}</td>
              <td>
                <svg width="90" height="12">
                  <line x1="45" y1="0" x2="45" y2="12" stroke="#26303f" />
                  <rect
                    x={val < 0 ? 45 - w : 45}
                    y="3"
                    width={w}
                    height="6"
                    fill={val < 0 ? "#ff4d4d" : "#3ddc84"}
                  />
                </svg>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

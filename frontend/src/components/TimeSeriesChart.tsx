import { useMemo } from "react";
import type { TimeSeries } from "../types";

// Lightweight dual-axis SVG chart: complaint volume (bars, left axis) vs
// ZHVI (line, right axis). Optionally shades a lead offset window.
interface Props {
  ts: TimeSeries;
  offset?: number | null;
}

const W = 380;
const H = 170;
const PAD = { l: 34, r: 40, t: 12, b: 22 };

export function TimeSeriesChart({ ts, offset }: Props) {
  const { bars, zhviPath, months, xFor } = useMemo(() => {
    const n = ts.months.length;
    const innerW = W - PAD.l - PAD.r;
    const innerH = H - PAD.t - PAD.b;
    const maxVol = Math.max(1, ...ts.volume);
    const zvals = ts.zhvi.filter((v): v is number => v != null);
    const zMin = zvals.length ? Math.min(...zvals) : 0;
    const zMax = zvals.length ? Math.max(...zvals) : 1;
    const xFor = (i: number) => PAD.l + (innerW * i) / Math.max(1, n - 1);
    const bw = Math.max(1.5, innerW / n - 2);

    const bars = ts.volume.map((v, i) => ({
      x: xFor(i) - bw / 2,
      y: PAD.t + innerH - (innerH * v) / maxVol,
      w: bw,
      h: (innerH * v) / maxVol,
    }));

    const zhviPath = ts.zhvi
      .map((v, i) => {
        if (v == null) return null;
        const y =
          PAD.t + innerH - (innerH * (v - zMin)) / Math.max(1, zMax - zMin);
        return `${xFor(i).toFixed(1)},${y.toFixed(1)}`;
      })
      .filter(Boolean)
      .join(" ");

    return { bars, zhviPath, months: ts.months, xFor };
  }, [ts]);

  const shade =
    offset != null && offset > 0 && months.length > offset
      ? { x1: xFor(months.length - 1 - offset), x2: xFor(months.length - 1) }
      : null;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block" }}>
      {shade && (
        <rect
          x={shade.x1}
          y={PAD.t}
          width={shade.x2 - shade.x1}
          height={H - PAD.t - PAD.b}
          fill="#ffd23f"
          opacity={0.08}
        />
      )}
      {bars.map((b, i) => (
        <rect key={i} x={b.x} y={b.y} width={b.w} height={b.h} fill="#ffd23f" opacity={0.7} />
      ))}
      {zhviPath && (
        <polyline
          points={zhviPath}
          fill="none"
          stroke="#4da3ff"
          strokeWidth={2}
          strokeLinejoin="round"
        />
      )}
      {months.map((m, i) =>
        i % Math.ceil(months.length / 6) === 0 ? (
          <text
            key={m}
            x={xFor(i)}
            y={H - 6}
            fontSize={8}
            fill="#8b98a8"
            textAnchor="middle"
          >
            {m.slice(2)}
          </text>
        ) : null,
      )}
      <text x={4} y={PAD.t + 8} fontSize={8} fill="#ffd23f">
        vol
      </text>
      <text x={W - 26} y={PAD.t + 8} fontSize={8} fill="#4da3ff">
        ZHVI
      </text>
    </svg>
  );
}

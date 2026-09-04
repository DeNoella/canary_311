import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import type { Findings, Meta, ZipRecord } from "./types";
import { CityScene } from "./components/CityScene";
import { DetailPanel } from "./components/DetailPanel";
import { FindingsPanel } from "./components/FindingsPanel";
import { Legend } from "./components/Legend";

interface Grid {
  months: string[];
  zips: Record<string, { volume: number[]; volume_z: (number | null)[]; velocity: (number | null)[] }>;
}

export default function App() {
  const [zips, setZips] = useState<ZipRecord[] | null>(null);
  const [grid, setGrid] = useState<Grid | null>(null);
  const [findings, setFindings] = useState<Findings | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const [monthIdx, setMonthIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const raf = useRef<number>();
  const last = useRef(0);

  useEffect(() => {
    Promise.all([api.zips(), api.findings(), api.meta()])
      .then(([z, f, m]) => {
        setZips(z);
        setFindings(f);
        setMeta(m);
      })
      .catch((e) => setError(String(e)));
    fetch((import.meta.env.VITE_API_BASE ?? "/api") + "/grid")
      .then((r) => (r.ok ? r.json() : null))
      .then((g: Grid | null) => {
        if (g) {
          setGrid(g);
          setMonthIdx(g.months.length - 1);
        }
      })
      .catch(() => void 0);
  }, []);

  useEffect(() => {
    if (!playing || !grid) return;
    const tick = (t: number) => {
      if (t - last.current > 550) {
        last.current = t;
        setMonthIdx((i) => (i + 1) % grid.months.length);
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current!);
  }, [playing, grid]);

  const months = grid?.months ?? [];
  const month = months[monthIdx];

  const maxVol = useMemo(() => {
    if (grid) {
      let mx = 1;
      for (const s of Object.values(grid.zips))
        for (const v of s.volume) if (v > mx) mx = v;
      return mx;
    }
    return zips ? Math.max(1, ...zips.map((z) => z.total_volume)) : 1;
  }, [grid, zips]);

  // Per-ZIP value for the currently scrubbed month (falls back to snapshot).
  const monthValues = useMemo(() => {
    const m = new Map<string, { volume: number; z: number | null }>();
    if (grid) {
      for (const [zip, s] of Object.entries(grid.zips)) {
        m.set(zip, { volume: s.volume[monthIdx] ?? 0, z: s.volume_z[monthIdx] ?? null });
      }
    } else if (zips) {
      for (const z of zips) m.set(z.zip, { volume: z.total_volume, z: z.latest_volume_z });
    }
    return m;
  }, [grid, monthIdx, zips]);

  if (error) {
    return (
      <div className="empty">
        <div>
          <h1>Canary</h1>
          <p>Couldn't reach the API ({error}).</p>
          <p className="muted">
            Start it with <code>uv run uvicorn api.main:app --port 8000</code>{" "}
            after running the pipeline (<code>uv run canary</code>).
          </p>
        </div>
      </div>
    );
  }

  if (!zips) {
    return (
      <div className="empty">
        <div>
          <h1>🐤 Canary</h1>
          <p>Loading…</p>
        </div>
      </div>
    );
  }

  if (zips.length === 0) {
    return (
      <div className="empty">
        <div>
          <h1>🐤 Canary</h1>
          <p>The API is up but there's no pipeline output yet.</p>
          <p className="muted">
            Run <code>uv run canary</code> to build <code>outputs/</code>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="scene-wrap">
        <CityScene
          zips={zips}
          monthValues={monthValues}
          maxVol={maxVol}
          selected={selected}
          onSelect={setSelected}
        />
        <div className="scene-overlay">
          <h1>
            🐤 Canary <span className="dot">·</span>{" "}
            <span className="muted" style={{ fontSize: 13 }}>
              NYC 311 complaint pressure as an early-warning signal
            </span>
          </h1>
          <p>
            {zips.length} ZIP codes · {meta?.window.start}–{meta?.window.end} ·
            bar height = complaint volume · colour = complaint pressure (z-score)
          </p>
          <Legend />
        </div>
        {months.length > 0 && (
          <div className="controls">
            <button onClick={() => setPlaying((p) => !p)}>
              {playing ? "❚❚ Pause" : "▶ Play"}
            </button>
            <span className="month">{month}</span>
            <input
              type="range"
              min={0}
              max={months.length - 1}
              value={monthIdx}
              onChange={(e) => {
                setPlaying(false);
                setMonthIdx(+e.target.value);
              }}
            />
          </div>
        )}
      </div>

      <div className="panel">
        {selected ? (
          <DetailPanel
            zip={selected}
            record={zips.find((z) => z.zip === selected)!}
            onClose={() => setSelected(null)}
          />
        ) : (
          <FindingsPanel findings={findings} meta={meta} zips={zips} onPick={setSelected} />
        )}
      </div>
    </div>
  );
}

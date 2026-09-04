import { useEffect, useMemo, useRef, useState } from "react";
import { api, type Grid } from "./api";
import type { Findings, Meta, ZipRecord } from "./types";
import { CityScene } from "./components/CityScene";
import { DetailPanel } from "./components/DetailPanel";
import { FindingsPanel } from "./components/FindingsPanel";
import { Legend } from "./components/Legend";
import { Header, type View } from "./components/Header";
import { Home } from "./components/Home";
import { About } from "./components/About";

const VIEWS: View[] = ["home", "map", "how"];
function readHash(): View {
  const h = window.location.hash.replace("#", "") as View;
  return VIEWS.includes(h) ? h : "home";
}

export default function App() {
  const [view, setView] = useState<View>(readHash());
  const [zips, setZips] = useState<ZipRecord[] | null>(null);
  const [grid, setGrid] = useState<Grid | null>(null);
  const [findings, setFindings] = useState<Findings | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const [monthIdx, setMonthIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const raf = useRef<number>();
  const last = useRef(0);

  const navigate = (v: View) => {
    window.location.hash = v;
    setView(v);
    window.scrollTo(0, 0);
  };

  useEffect(() => {
    const onHash = () => setView(readHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    Promise.all([api.zips(), api.findings(), api.meta()])
      .then(([z, f, m]) => {
        setZips(z);
        setFindings(f);
        setMeta(m);
      })
      .catch((e) => setError(String(e)));
    api
      .grid()
      .then((g) => {
        setGrid(g);
        setMonthIdx(g.months.length - 1);
      })
      .catch(() => void 0);
  }, []);

  useEffect(() => {
    if (!playing || !grid || view !== "map") return;
    const tick = (t: number) => {
      if (t - last.current > 550) {
        last.current = t;
        setMonthIdx((i) => (i + 1) % grid.months.length);
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current!);
  }, [playing, grid, view]);

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

  return (
    <div className="shell">
      <Header view={view} onNavigate={navigate} />
      <main className="view">
        {view === "home" && (
          <Home
            meta={meta}
            findings={findings}
            onExplore={() => navigate("map")}
            onHow={() => navigate("how")}
          />
        )}
        {view === "how" && <About meta={meta} onExplore={() => navigate("map")} />}
        {view === "map" && (
          <MapView
            {...{
              zips,
              error,
              months,
              month,
              monthIdx,
              setMonthIdx,
              playing,
              setPlaying,
              monthValues,
              maxVol,
              selected,
              setSelected,
              findings,
              meta,
              showHelp,
              setShowHelp,
              onHow: () => navigate("how"),
            }}
          />
        )}
      </main>
    </div>
  );
}

function MapView(p: {
  zips: ZipRecord[] | null;
  error: string | null;
  months: string[];
  month: string;
  monthIdx: number;
  setMonthIdx: (n: number) => void;
  playing: boolean;
  setPlaying: (f: (p: boolean) => boolean) => void;
  monthValues: Map<string, { volume: number; z: number | null }>;
  maxVol: number;
  selected: string | null;
  setSelected: (z: string | null) => void;
  findings: Findings | null;
  meta: Meta | null;
  showHelp: boolean;
  setShowHelp: (f: (v: boolean) => boolean) => void;
  onHow: () => void;
}) {
  if (p.error) {
    return (
      <div className="empty">
        <div>
          <h1>The map needs the data service running</h1>
          <p className="muted">Couldn't reach the API ({p.error}).</p>
          <p className="muted">
            Start it: <code>uv run uvicorn api.main:app --port 8000</code> (after{" "}
            <code>uv run canary</code>).
          </p>
        </div>
      </div>
    );
  }
  if (!p.zips) return <div className="empty"><div><p>Loading the map…</p></div></div>;
  if (p.zips.length === 0)
    return (
      <div className="empty">
        <div>
          <p>The service is up but there's no analysis output yet.</p>
          <p className="muted">Run <code>uv run canary</code>.</p>
        </div>
      </div>
    );

  return (
    <div className="app">
      <div className="scene-wrap">
        <CityScene
          zips={p.zips}
          monthValues={p.monthValues}
          maxVol={p.maxVol}
          selected={p.selected}
          onSelect={p.setSelected}
        />
        <div className="scene-overlay">
          <p className="scene-title">
            Complaint pressure across {p.zips.length} NYC neighborhoods
          </p>
          <p>
            Taller = more complaints · greener = normal · redder = unusually high ·
            pulsing = rising fastest.{" "}
            <button className="linkish" onClick={() => p.setShowHelp((v) => !v)}>
              {p.showHelp ? "hide guide" : "how to read this"}
            </button>
          </p>
          <Legend />
          {p.showHelp && (
            <div className="help-card">
              <strong>Reading the map</strong>
              <ul>
                <li>Each block is one ZIP code, on its real map location.</li>
                <li>Height = number of 311 complaints in the selected month.</li>
                <li>
                  Colour = "complaint pressure": how unusual that volume is vs. the
                  ZIP's own recent history (green normal → red high).
                </li>
                <li>Press ▶ Play to watch 3 years pass. Drag to any month.</li>
                <li>Click a block for its complaint-vs-home-value story.</li>
              </ul>
              <button className="linkish" onClick={p.onHow}>
                Full methods & data sources →
              </button>
            </div>
          )}
        </div>
        {p.months.length > 0 && (
          <div className="controls">
            <button onClick={() => p.setPlaying((x) => !x)}>
              {p.playing ? "❚❚ Pause" : "▶ Play"}
            </button>
            <span className="month">{p.month}</span>
            <input
              type="range"
              min={0}
              max={p.months.length - 1}
              value={p.monthIdx}
              onChange={(e) => {
                p.setPlaying(() => false);
                p.setMonthIdx(+e.target.value);
              }}
            />
          </div>
        )}
      </div>

      <div className="panel">
        {p.selected ? (
          <DetailPanel
            zip={p.selected}
            record={p.zips.find((z) => z.zip === p.selected)!}
            onClose={() => p.setSelected(null)}
          />
        ) : (
          <FindingsPanel
            findings={p.findings}
            meta={p.meta}
            zips={p.zips}
            onPick={p.setSelected}
          />
        )}
      </div>
    </div>
  );
}

import type { Findings, Meta } from "../types";
import {
  HOW_TO_READ,
  TAGLINE,
  WHAT_IS_IT,
  WHAT_WE_FOUND,
} from "../content";

export function Home({
  meta,
  findings,
  onExplore,
  onHow,
}: {
  meta: Meta | null;
  findings: Findings | null;
  onExplore: () => void;
  onHow: () => void;
}) {
  const stats = [
    { v: meta ? meta.n_zips.toString() : "175", l: "NYC neighborhoods (ZIP codes)" },
    {
      v: "≈9.9M",
      l: "311 complaints analysed",
    },
    {
      v: meta ? `${meta.window.start} – ${meta.window.end}` : "2022 – 2025",
      l: "time span (36 months)",
    },
    { v: "$0", l: "cost to build & run" },
  ];

  return (
    <div className="page">
      <section className="hero">
        <p className="eyebrow">NYC 311 · early-warning signal</p>
        <h1>
          Can a neighborhood's <span className="hl">complaints</span> tell us it's
          under stress — before the housing market does?
        </h1>
        <p className="lede">{TAGLINE}</p>
        <div className="cta-row">
          <button className="btn primary" onClick={onExplore}>
            Explore the 3D map →
          </button>
          <button className="btn ghost" onClick={onHow}>
            How it works
          </button>
        </div>
        <div className="statstrip">
          {stats.map((s) => (
            <div key={s.l}>
              <div className="v">{s.v}</div>
              <div className="l">{s.l}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="prose">
        <h2>What is this?</h2>
        {WHAT_IS_IT.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </section>

      <section className="prose">
        <h2>What you're looking at</h2>
        <p className="muted">
          The map is a 3D view of New York City. Here's how to read it:
        </p>
        <div className="deflist">
          {HOW_TO_READ.map((d) => (
            <div key={d.k} className="def">
              <div className="dt">{d.k}</div>
              <div className="dd">{d.v}</div>
            </div>
          ))}
        </div>
        <button className="btn primary" onClick={onExplore} style={{ marginTop: 18 }}>
          Open the map →
        </button>
      </section>

      <section className="prose">
        <h2>What we found</h2>
        {WHAT_WE_FOUND.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
        {findings?.headline && (
          <blockquote className="headline">{findings.headline}</blockquote>
        )}
        <p className="muted">
          The full write-up, regenerated every time the analysis runs, is in{" "}
          <code>FINDINGS.md</code>. Numbers and wording update automatically with
          the data.
        </p>
      </section>

      <footer className="page-footer">
        <span>
          Exploratory, correlational research — not a forecast, not causal.
        </span>
        <a href="https://github.com/DeNoella/canary_311" target="_blank" rel="noreferrer">
          github.com/DeNoella/canary_311
        </a>
      </footer>
    </div>
  );
}

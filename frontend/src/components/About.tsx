import type { Meta } from "../types";
import {
  DATA_SOURCES,
  HOW_IT_WORKS,
  LIMITATIONS,
  TECH,
} from "../content";

export function About({ meta, onExplore }: { meta: Meta | null; onExplore: () => void }) {
  return (
    <div className="page">
      <section className="hero compact">
        <p className="eyebrow">Methods · technology · data</p>
        <h1>How it works</h1>
        <p className="lede">
          The whole thing is a five-step pipeline that turns raw complaint logs
          into the map you can explore. No step uses a paid service.
        </p>
      </section>

      <section className="prose">
        <h2>The pipeline, in five steps</h2>
        <ol className="steps">
          {HOW_IT_WORKS.map((s) => (
            <li key={s.step}>
              <span className="num">{s.step}</span>
              <div>
                <div className="dt">{s.title}</div>
                <div className="dd">{s.body}</div>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="prose">
        <h2>Technologies used</h2>
        <div className="deflist">
          {TECH.map((t) => (
            <div key={t.k} className="def">
              <div className="dt">{t.k}</div>
              <div className="dd">{t.v}</div>
            </div>
          ))}
        </div>
        {meta?.embedding_method && (
          <p className="muted">
            This run used <code>{meta.embedding_method}</code> for the theme step,
            producing <strong>{meta.n_themes}</strong> themes from{" "}
            <strong>{meta.n_sampled_complaints?.toLocaleString()}</strong> sampled
            complaints.
          </p>
        )}
      </section>

      <section className="prose">
        <h2>Data sources &amp; how it was gathered</h2>
        {DATA_SOURCES.map((d) => (
          <div key={d.name} className="source">
            <h3>{d.name}</h3>
            <p>{d.what}</p>
            {d.how && (
              <p className="muted">
                <strong>How it was gathered: </strong>
                {d.how}
              </p>
            )}
          </div>
        ))}
        {meta?.dataset && (
          <p className="muted">
            This run's data: <code>{meta.dataset}</code>.
          </p>
        )}
      </section>

      <section className="prose">
        <h2>Limitations — read before drawing conclusions</h2>
        <ul className="limits">
          {(meta?.caveats?.length ? meta.caveats : LIMITATIONS).map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </section>

      <section className="prose">
        <h2>What we'd do with more time</h2>
        <ul className="limits">
          <li>Add rent, vacancy, building permits, and crime as extra comparison signals.</li>
          <li>Use a proper statistical panel model instead of simple pooled correlation.</li>
          <li>Extend to 8–10 years and several cities, holding out a test period.</li>
          <li>Use exact ZIP-code map boundaries instead of sampled centre points.</li>
        </ul>
        <button className="btn primary" onClick={onExplore} style={{ marginTop: 8 }}>
          Explore the map →
        </button>
      </section>

      <footer className="page-footer">
        <span>Built as a portfolio data-science project.</span>
        <a href="https://github.com/DeNoella/canary_311" target="_blank" rel="noreferrer">
          github.com/DeNoella/canary_311
        </a>
      </footer>
    </div>
  );
}

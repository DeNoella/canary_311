export type View = "home" | "map" | "how";

const TABS: { id: View; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "map", label: "Explore the map" },
  { id: "how", label: "How it works" },
];

export function Header({
  view,
  onNavigate,
}: {
  view: View;
  onNavigate: (v: View) => void;
}) {
  return (
    <header className="site-header">
      <div className="header-inner">
        <button className="brand" onClick={() => onNavigate("home")}>
          <span>Canary</span>
        </button>
        <nav>
          {TABS.map((t) => (
            <button
              key={t.id}
              className={view === t.id ? "nav active" : "nav"}
              onClick={() => onNavigate(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <a
          className="nav ext"
          href="https://github.com/DeNoella/canary_311"
          target="_blank"
          rel="noreferrer"
        >
          Source ↗
        </a>
      </div>
    </header>
  );
}

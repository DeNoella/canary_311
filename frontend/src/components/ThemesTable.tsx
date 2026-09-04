import type { ZipThemes } from "../types";

export function ThemesTable({ themes }: { themes: ZipThemes }) {
  return (
    <>
      <table>
        <tbody>
          {themes.top_themes.map((t) => (
            <tr key={t.theme}>
              <td style={{ width: "55%" }}>{t.theme}</td>
              <td>
                <div
                  style={{
                    background: "#ffd23f",
                    height: 8,
                    borderRadius: 4,
                    width: `${Math.max(4, t.share * 100)}%`,
                  }}
                />
              </td>
              <td className="num">{(t.share * 100).toFixed(0)}%</td>
            </tr>
          ))}
        </tbody>
      </table>

      {themes.emerging.length > 0 && (
        <>
          <h2>Emerging themes (recent share ≫ prior)</h2>
          <div>
            {themes.emerging.map((e) => (
              <div key={e.theme} className="card" style={{ padding: "8px 12px" }}>
                <strong>{e.theme}</strong>
                <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                  {(e.recent_share * 100).toFixed(0)}% now vs{" "}
                  {(e.prior_share * 100).toFixed(0)}% before
                  {e.lift != null && ` · ${e.lift.toFixed(1)}× lift`} ·{" "}
                  {e.recent_n} complaints
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}

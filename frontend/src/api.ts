import type { Findings, Meta, TimeSeries, ZipRecord, ZipThemes } from "./types";

// Data access. Two modes:
//   • Live API   — set VITE_API_BASE (e.g. "/api" behind the dev proxy, or a
//                  deployed FastAPI URL). Used automatically in `npm run dev`.
//   • Static     — no VITE_API_BASE: read the pipeline's JSON straight from
//                  /data/*.json (copied there by scripts/sync-data.mjs). This is
//                  what a Vercel / static deploy uses — no backend required.
const API_BASE: string | undefined =
  import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? "/api" : undefined);
const STATIC = !API_BASE;

function toUrl(apiPath: string): string {
  if (!STATIC) return `${API_BASE}${apiPath}`;
  const m = apiPath.match(/^\/zips\/([^/]+)\/(timeseries|themes)$/);
  if (m) return `/data/${m[2]}/${m[1]}.json`;
  if (apiPath === "/zips") return "/data/zips.json";
  return `/data${apiPath}.json`; // /meta, /findings, /grid, /leadlag
}

async function j<T>(apiPath: string): Promise<T> {
  const res = await fetch(toUrl(apiPath));
  if (!res.ok) throw new Error(`${apiPath} → ${res.status}`);
  return res.json() as Promise<T>;
}

export interface Grid {
  months: string[];
  zips: Record<
    string,
    { volume: number[]; volume_z: (number | null)[]; velocity: (number | null)[] }
  >;
}

export const api = {
  isStatic: STATIC,
  health: () =>
    STATIC
      ? Promise.resolve({ status: "static" })
      : j<{ status: string }>("/health"),
  meta: () => j<Meta>("/meta"),
  findings: () => j<Findings>("/findings"),
  zips: () => j<ZipRecord[]>("/zips"),
  grid: () => j<Grid>("/grid"),
  timeseries: (zip: string) => j<TimeSeries>(`/zips/${zip}/timeseries`),
  themes: (zip: string) => j<ZipThemes>(`/zips/${zip}/themes`),
};

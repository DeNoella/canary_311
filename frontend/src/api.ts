import type { Findings, Meta, TimeSeries, ZipRecord, ZipThemes } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function j<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => j<{ status: string }>("/health"),
  meta: () => j<Meta>("/meta"),
  findings: () => j<Findings>("/findings"),
  zips: () => j<ZipRecord[]>("/zips"),
  timeseries: (zip: string) => j<TimeSeries>(`/zips/${zip}/timeseries`),
  themes: (zip: string) => j<ZipThemes>(`/zips/${zip}/themes`),
};

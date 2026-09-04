export interface ZipRecord {
  zip: string;
  borough: string;
  lat: number | null;
  lon: number | null;
  total_volume: number;
  latest_velocity: number;
  mean_velocity: number;
  latest_volume_z: number;
  trend_slope: number;
  dominant_theme: string | null;
  best_offset: number | null;
  best_r: number | null;
  in_top_volume: boolean;
  in_top_rising: boolean;
}

export interface LeadLagPoint {
  offset: number;
  r: number | null;
  p: number | null;
  n: number;
}

export interface TimeSeries {
  zip: string;
  months: string[];
  volume: number[];
  velocity: (number | null)[];
  velocity_3m: (number | null)[];
  volume_z: (number | null)[];
  dominant_theme: (string | null)[];
  zhvi: (number | null)[];
  zhvi_mom: (number | null)[];
  leadlag: LeadLagPoint[];
}

export interface ThemeRow {
  theme: string;
  n: number;
  share: number;
}

export interface EmergingRow {
  theme: string;
  recent_share: number;
  prior_share: number;
  lift: number | null;
  recent_n: number;
}

export interface ZipThemes {
  zip: string;
  top_themes: ThemeRow[];
  emerging: EmergingRow[];
}

export interface Findings {
  generated_at: string;
  n_zips: number;
  window: { start: string; end: string; months: number };
  headline: string;
  best_pooled_all: LeadLagPoint;
  best_pooled_rising: LeadLagPoint;
  pooled: Record<string, LeadLagPoint[]>;
  top_volume_zips: string[];
  top_rising_zips: string[];
  top_themes_overall: { theme_id: number; theme: string; n: number }[];
  embedding_method: string;
}

export interface Meta {
  generated_at: string;
  window: { start: string; end: string };
  n_zips: number;
  n_sampled_complaints: number;
  n_themes: number;
  embedding_method: string;
  dataset: string;
  caveats: string[];
}

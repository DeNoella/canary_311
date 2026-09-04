// Shared green -> amber -> red ramp used by the 3D bars and the legend.
// `t` in [0,1].
export function ramp(t: number): string {
  const c = Math.max(0, Math.min(1, t));
  const stops = [
    [61, 220, 132], // #3ddc84 good
    [255, 176, 32], // #ffb020 warn
    [255, 77, 77], // #ff4d4d bad
  ];
  const seg = c >= 0.5 ? 1 : 0;
  const local = (c - seg * 0.5) / 0.5;
  const a = stops[seg];
  const b = stops[seg + 1];
  const mix = a.map((v, i) => Math.round(v + (b[i] - v) * local));
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`;
}

// Map a complaint-pressure value (z-score-ish, roughly [-1, 3]) to [0,1].
export function pressureToT(z: number | null | undefined): number {
  if (z == null || Number.isNaN(z)) return 0.1;
  return Math.max(0, Math.min(1, (z + 1) / 4));
}

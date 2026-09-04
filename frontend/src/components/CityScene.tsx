import { useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid, Html } from "@react-three/drei";
import type { ZipRecord } from "../types";
import { ZipBar } from "./ZipBar";

interface Props {
  zips: ZipRecord[];
  monthValues: Map<string, { volume: number; z: number | null }>;
  maxVol: number;
  selected: string | null;
  onSelect: (zip: string | null) => void;
}

const SPREAD = 46; // world units across the city footprint

export function CityScene({ zips, monthValues, maxVol, selected, onSelect }: Props) {
  const geo = useMemo(() => {
    const pts = zips.filter((z) => z.lat != null && z.lon != null);
    const lats = pts.map((p) => p.lat!);
    const lons = pts.map((p) => p.lon!);
    const minLat = Math.min(...lats),
      maxLat = Math.max(...lats);
    const minLon = Math.min(...lons),
      maxLon = Math.max(...lons);
    const project = (lat: number, lon: number): [number, number] => [
      ((lon - minLon) / (maxLon - minLon || 1) - 0.5) * SPREAD,
      -(((lat - minLat) / (maxLat - minLat || 1)) - 0.5) * SPREAD,
    ];
    return { pts, project };
  }, [zips]);

  const [hover, setHover] = useState<{ zip: string; x: number; y: number } | null>(null);

  return (
    <>
      <Canvas
        shadows
        camera={{ position: [0, 42, 46], fov: 42 }}
        onPointerMissed={() => onSelect(null)}
        style={{ background: "linear-gradient(180deg,#0a0e14,#0d1420)" }}
      >
        <ambientLight intensity={0.55} />
        <directionalLight
          position={[20, 40, 15]}
          intensity={1.1}
          castShadow
          shadow-mapSize={[2048, 2048]}
        />
        <fog attach="fog" args={["#0a0e14", 60, 140]} />

        <Grid
          args={[SPREAD * 1.4, SPREAD * 1.4]}
          cellSize={2}
          cellThickness={0.5}
          cellColor="#1c2635"
          sectionSize={10}
          sectionColor="#2a3a52"
          fadeDistance={120}
          infiniteGrid
        />

        {geo.pts.map((z) => {
          const [x, zpos] = geo.project(z.lat!, z.lon!);
          const mv = monthValues.get(z.zip);
          const volume = mv?.volume ?? z.total_volume;
          const zscore = mv?.z ?? z.latest_volume_z;
          return (
            <ZipBar
              key={z.zip}
              x={x}
              z={zpos}
              volume={volume}
              maxVol={maxVol}
              pressure={zscore}
              rising={z.in_top_rising}
              selected={selected === z.zip}
              dim={selected != null && selected !== z.zip}
              onClick={() => onSelect(z.zip)}
              onHover={(hovering, sx, sy) =>
                setHover(hovering ? { zip: z.zip, x: sx, y: sy } : null)
              }
            />
          );
        })}

        {hover && (
          <Html position={[0, 0, 0]} style={{ pointerEvents: "none" }} fullscreen>
            <div className="tooltip" style={{ left: hover.x, top: hover.y }}>
              <strong>{hover.zip}</strong>{" "}
              {zips.find((z) => z.zip === hover.zip)?.borough}
              <br />
              vol {Math.round(monthValues.get(hover.zip)?.volume ?? 0)} · pressure{" "}
              {(monthValues.get(hover.zip)?.z ?? 0).toFixed(2)}
            </div>
          </Html>
        )}

        <OrbitControls
          enablePan
          enableDamping
          dampingFactor={0.08}
          minDistance={14}
          maxDistance={110}
          maxPolarAngle={Math.PI / 2.15}
        />
      </Canvas>
    </>
  );
}

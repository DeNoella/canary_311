import { useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { pressureToT, ramp } from "../color";

interface Props {
  x: number;
  z: number;
  volume: number;
  maxVol: number;
  pressure: number | null;
  rising: boolean;
  selected: boolean;
  dim: boolean;
  onClick: () => void;
  onHover: (hovering: boolean, screenX: number, screenY: number) => void;
}

const MAX_H = 18;
const FOOT = 1.35;

export function ZipBar({
  x,
  z,
  volume,
  maxVol,
  pressure,
  rising,
  selected,
  dim,
  onClick,
  onHover,
}: Props) {
  const mesh = useRef<THREE.Mesh>(null);
  const cage = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshStandardMaterial>(null);
  const [hovered, setHovered] = useState(false);
  const { camera, size } = useThree();

  const targetH = Math.max(0.25, Math.sqrt(volume / maxVol) * MAX_H);
  const t = pressureToT(pressure);
  const baseColor = new THREE.Color(ramp(t));

  useFrame((state, delta) => {
    if (!mesh.current || !mat.current) return;
    const cur = mesh.current.scale.y;
    const next = THREE.MathUtils.damp(cur, targetH, 6, delta);
    mesh.current.scale.y = next;
    mesh.current.position.y = next / 2;
    if (cage.current) {
      cage.current.scale.y = next;
      cage.current.position.y = next / 2;
      cage.current.visible = selected;
    }

    // pulse the emissive for high-pressure / rising ZIPs
    const pulse =
      (rising || t > 0.7 ? 1 : 0) *
      (0.5 + 0.5 * Math.sin(state.clock.elapsedTime * 3));
    const target = new THREE.Color(baseColor);
    mat.current.color.lerp(target, 0.2);
    mat.current.emissive.lerp(target, 0.2);
    mat.current.emissiveIntensity = THREE.MathUtils.damp(
      mat.current.emissiveIntensity,
      (hovered ? 0.9 : 0.15) + pulse * 0.6,
      8,
      delta,
    );
    mat.current.opacity = THREE.MathUtils.damp(
      mat.current.opacity,
      dim ? 0.25 : 1,
      8,
      delta,
    );
  });

  const toScreen = () => {
    const v = new THREE.Vector3(x, targetH + 1, z).project(camera);
    return [((v.x + 1) / 2) * size.width, ((-v.y + 1) / 2) * size.height] as const;
  };

  return (
    <group position={[x, 0, z]}>
      <mesh
        ref={mesh}
        position={[0, 0.5, 0]}
        castShadow
        receiveShadow
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          const [sx, sy] = toScreen();
          onHover(true, sx, sy);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          onHover(false, 0, 0);
          document.body.style.cursor = "default";
        }}
      >
        <boxGeometry args={[FOOT, 1, FOOT]} />
        <meshStandardMaterial
          ref={mat}
          transparent
          metalness={0.15}
          roughness={0.4}
          color={baseColor}
          emissive={baseColor}
          emissiveIntensity={0.15}
        />
      </mesh>
      <mesh ref={cage} position={[0, 0.5, 0]} visible={false}>
        <boxGeometry args={[FOOT * 1.3, 1, FOOT * 1.3]} />
        <meshBasicMaterial color="#ffd23f" wireframe />
      </mesh>
    </group>
  );
}

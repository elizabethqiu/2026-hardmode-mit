"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface MushroomProps {
  height: number;
  color: [number, number, number];
  brightness: number;
  mood: string;
  isBreathing: boolean;
  isCelebrating: boolean;
  groveLights: { color: [number, number, number]; brightness: number }[];
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * Math.min(1, t);
}

export function Mushroom3D({
  height = 0.7,
  color = [200, 180, 120],
  brightness = 0.75,
  mood = "watchful",
  isBreathing = false,
  isCelebrating = false,
  groveLights = [],
}: MushroomProps) {
  const groupRef = useRef<THREE.Group>(null);
  const capRef = useRef<THREE.Mesh>(null);
  const capMatRef = useRef<THREE.MeshStandardMaterial>(null);
  const undersideRef = useRef<THREE.Mesh>(null);
  const undersideMatRef = useRef<THREE.MeshStandardMaterial>(null);
  const glowRef = useRef<THREE.PointLight>(null);
  const stemRef = useRef<THREE.Mesh>(null);
  const currentHeight = useRef(0.7);
  const currentColor = useRef(new THREE.Color(0.78, 0.71, 0.47));
  const celebrateStart = useRef(0);

  const targetColor = useMemo(
    () => new THREE.Color(color[0] / 255, color[1] / 255, color[2] / 255),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [color[0], color[1], color[2]]
  );

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const dt = 0.03;

    currentHeight.current = lerp(currentHeight.current, height, dt * 2);
    const stemScale = 0.3 + currentHeight.current * 1.4;

    if (stemRef.current) {
      stemRef.current.scale.y = stemScale;
      stemRef.current.position.y = stemScale * 0.5;
    }

    const capY = stemScale + 0.15;
    if (capRef.current) capRef.current.position.y = capY;
    if (undersideRef.current) undersideRef.current.position.y = capY;

    currentColor.current.lerp(targetColor, dt * 3);

    if (capMatRef.current) {
      capMatRef.current.color.copy(currentColor.current);
      capMatRef.current.emissive.copy(currentColor.current);
      capMatRef.current.emissiveIntensity = 0.7 + brightness * 1.1;
    }

    if (undersideMatRef.current) {
      undersideMatRef.current.color.copy(currentColor.current).multiplyScalar(0.8);
    }

    if (glowRef.current) {
      glowRef.current.color.copy(currentColor.current);
      glowRef.current.position.y = capY + 0.15;

      if (isBreathing) {
        const breathe = (Math.sin(t * 3) + 1) * 0.5;
        glowRef.current.intensity = 1.0 + brightness * (1.5 + breathe * 2.0);
      } else {
        glowRef.current.intensity = 1.2 + brightness * 2.0;
      }
    }

    if (isCelebrating) {
      if (celebrateStart.current === 0) celebrateStart.current = t;
      const elapsed = t - celebrateStart.current;
      if (elapsed < 3) {
        const hue = (elapsed * 0.5) % 1;
        const celebColor = new THREE.Color().setHSL(hue, 1, 0.6);
        if (capMatRef.current) {
          capMatRef.current.emissive.copy(celebColor);
          capMatRef.current.emissiveIntensity = 1.5;
        }
        if (glowRef.current) {
          glowRef.current.color.copy(celebColor);
          glowRef.current.intensity = 4.0;
        }
      } else {
        celebrateStart.current = 0;
      }
    } else {
      celebrateStart.current = 0;
    }

    if (groupRef.current) {
      groupRef.current.rotation.z = Math.sin(t * 0.5) * 0.02;
    }
  });

  const initColor = useMemo(
    () => new THREE.Color(color[0] / 255, color[1] / 255, color[2] / 255),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  return (
    <group ref={groupRef}>
      {/* Base plate */}
      <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.6, 32]} />
        <meshStandardMaterial color="#3a3a3a" roughness={0.8} />
      </mesh>

      {/* Stem */}
      <mesh ref={stemRef} position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.12, 0.16, 1, 16]} />
        <meshStandardMaterial color="#f5f0e0" roughness={0.5} metalness={0.05} />
      </mesh>

      {/* Cap */}
      <mesh ref={capRef} position={[0, 1.2, 0]}>
        <sphereGeometry args={[0.45, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial
          ref={capMatRef}
          color={initColor}
          roughness={0.25}
          metalness={0.05}
          emissive={initColor}
          emissiveIntensity={0.4}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Cap underside */}
      <mesh ref={undersideRef} position={[0, 1.2, 0]} rotation={[Math.PI, 0, 0]}>
        <circleGeometry args={[0.45, 32]} />
        <meshStandardMaterial
          ref={undersideMatRef}
          color="#e8dcc8"
          roughness={0.7}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Glow light */}
      <pointLight ref={glowRef} position={[0, 1.3, 0]} intensity={1} distance={4} decay={2} />

      {/* Grove member lights */}
      {groveLights.map((light, i) => {
        const angle = (i / Math.max(groveLights.length, 1)) * Math.PI * 2;
        const x = Math.cos(angle) * 0.5;
        const z = Math.sin(angle) * 0.5;
        const c = new THREE.Color(light.color[0] / 255, light.color[1] / 255, light.color[2] / 255);
        return (
          <group key={i} position={[x, 0.08, z]}>
            <mesh>
              <sphereGeometry args={[0.04, 8, 8]} />
              <meshStandardMaterial color={c} emissive={c} emissiveIntensity={light.brightness * 0.8} />
            </mesh>
            <pointLight color={c} intensity={light.brightness * 0.4} distance={0.5} decay={2} />
          </group>
        );
      })}
    </group>
  );
}

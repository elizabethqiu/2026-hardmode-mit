"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Mushroom3D } from "./Mushroom3D";

interface MushroomCanvasProps {
  height?: number;
  color?: [number, number, number];
  brightness?: number;
  mood?: string;
  isBreathing?: boolean;
  isCelebrating?: boolean;
  groveLights?: { color: [number, number, number]; brightness: number }[];
}

export function MushroomCanvas({
  height = 0.7,
  color = [200, 180, 120],
  brightness = 0.75,
  mood = "watchful",
  isBreathing = false,
  isCelebrating = false,
  groveLights = [],
}: MushroomCanvasProps) {
  return (
    <div className="w-full h-full min-h-[300px]">
      <Canvas
        camera={{ position: [0, 1.5, 3], fov: 40 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.28} />
          <directionalLight position={[3, 5, 2]} intensity={0.55} />
          <directionalLight position={[-2, 3, -1]} intensity={0.2} />
          <hemisphereLight args={["#ffeedd", "#223344", 0.2]} />

          <Mushroom3D
            height={height}
            color={color}
            brightness={brightness}
            mood={mood}
            isBreathing={isBreathing}
            isCelebrating={isCelebrating}
            groveLights={groveLights}
          />

          <OrbitControls
            enablePan={false}
            enableZoom={true}
            minDistance={2}
            maxDistance={6}
            minPolarAngle={0.3}
            maxPolarAngle={Math.PI / 2.1}
            autoRotate
            autoRotateSpeed={0.3}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}

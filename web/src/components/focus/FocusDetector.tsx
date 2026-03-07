"use client";

import { useFocusDetection } from "@/hooks/useFocusDetection";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Camera, CameraOff } from "lucide-react";

const STATE_COLORS: Record<string, string> = {
  FOCUSED: "bg-green-500",
  IDLE: "bg-amber-500",
  DOZING: "bg-orange-500",
  AWAY: "bg-zinc-500",
};

export function FocusDetectorWidget() {
  const { state, duration, isDetecting, videoRef, toggleDetection, sessionFocusPct } =
    useFocusDetection();

  const minutes = Math.floor(duration / 60);
  const seconds = Math.floor(duration % 60);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-40 h-30 rounded-lg overflow-hidden bg-muted">
        <video
          ref={videoRef}
          className="w-full h-full object-cover mirror"
          style={{ transform: "scaleX(-1)" }}
          muted
          playsInline
        />
        {!isDetecting && (
          <div className="absolute inset-0 flex items-center justify-center bg-muted">
            <CameraOff className="h-8 w-8 text-muted-foreground" />
          </div>
        )}
        <Badge className={`absolute top-2 right-2 ${STATE_COLORS[state]}`}>
          {state}
        </Badge>
      </div>
      <div className="text-center space-y-1">
        <p className="text-sm text-muted-foreground">
          {isDetecting ? `${minutes}m ${seconds}s in ${state}` : "Camera off"}
        </p>
        {isDetecting && (
          <p className="text-xs text-muted-foreground">Session focus: {sessionFocusPct()}%</p>
        )}
      </div>
      <Button variant="outline" size="sm" onClick={toggleDetection}>
        {isDetecting ? <CameraOff className="h-4 w-4 mr-1" /> : <Camera className="h-4 w-4 mr-1" />}
        {isDetecting ? "Stop" : "Start"} Detection
      </Button>
    </div>
  );
}

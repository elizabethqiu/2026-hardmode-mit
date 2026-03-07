"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Zap } from "lucide-react";

interface SprintTimerProps {
  topic?: string;
  durationMinutes?: number;
  startedAt?: string | null;
}

export function SprintTimerWidget({ topic, durationMinutes, startedAt }: SprintTimerProps = {}) {
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (!startedAt || !durationMinutes) { setRemaining(null); return; }

    const tick = () => {
      const elapsed = (Date.now() - new Date(startedAt).getTime()) / 1000;
      const rem = durationMinutes * 60 - elapsed;
      setRemaining(rem > 0 ? rem : 0);
    };

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt, durationMinutes]);

  if (remaining === null || remaining <= 0) return null;

  const mins = Math.floor(remaining / 60);
  const secs = Math.floor(remaining % 60);

  return (
    <Card className="border-green-500/30 bg-green-500/5">
      <CardContent className="py-4 flex items-center gap-3">
        <div className="h-10 w-10 rounded-full bg-green-500/20 flex items-center justify-center animate-pulse">
          <Zap className="h-5 w-5 text-green-400" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium">{topic || "Sprint"}</p>
          <p className="text-2xl font-bold tabular-nums text-green-400">
            {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

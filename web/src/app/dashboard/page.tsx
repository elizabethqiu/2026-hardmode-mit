"use client";

import dynamic from "next/dynamic";
import { FocusDetectorWidget } from "@/components/focus/FocusDetector";
import { useMushroom } from "@/hooks/useMushroom";
import { useFocusDetection } from "@/hooks/useFocusDetection";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { SprintTimerWidget } from "@/components/sprint/SprintTimer";
import { Clock, Flame, TrendingUp } from "lucide-react";

const MushroomCanvas = dynamic(
  () => import("@/components/mushroom/MushroomCanvas").then((m) => m.MushroomCanvas),
  { ssr: false }
);

const STATE_COLORS: Record<string, string> = {
  FOCUSED: "text-green-400",
  IDLE: "text-amber-400",
  DOZING: "text-orange-400",
  AWAY: "text-zinc-400",
};

export default function DashboardPage() {
  const mushroom = useMushroom();
  const focus = useFocusDetection();

  const minutes = Math.floor(focus.duration / 60);

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Mushroom */}
        <div className="lg:col-span-2">
          <Card className="overflow-hidden">
            <div className="h-[400px] lg:h-[500px] relative">
              <MushroomCanvas
                height={mushroom.height}
                color={mushroom.color}
                brightness={mushroom.brightness}
                mood={mushroom.mood}
                isBreathing={mushroom.isBreathing}
                isCelebrating={mushroom.isCelebrating}
                groveLights={mushroom.groveLights}
              />
              <div className="absolute top-4 left-4">
                <Badge variant="outline" className="bg-card/80 backdrop-blur">
                  <span className={`mr-1 ${STATE_COLORS[focus.state]}`}>●</span>
                  {mushroom.mood}
                </Badge>
              </div>
            </div>
          </Card>
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Focus status */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Focus Status</CardTitle>
            </CardHeader>
            <CardContent>
              <FocusDetectorWidget />
            </CardContent>
          </Card>

          {/* Session stats */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Session</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>Current state</span>
                </div>
                <span className={`font-medium ${STATE_COLORS[focus.state]}`}>
                  {focus.state} ({minutes}m)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Flame className="h-4 w-4" />
                  <span>Focus rate</span>
                </div>
                <span className="font-medium">{focus.sessionFocusPct()}%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <TrendingUp className="h-4 w-4" />
                  <span>Focus time</span>
                </div>
                <span className="font-medium">
                  {Math.round(focus.focusSeconds.current / 60)}m
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Sprint timer */}
          <SprintTimerWidget />
        </div>
      </div>

      {/* Chat panel */}
      <ChatPanel
        focusState={focus.state}
        focusDuration={focus.duration}
        sessionFocusPct={focus.sessionFocusPct()}
        onMushroomUpdate={mushroom.applyClaudeResponse}
        onCelebrate={mushroom.celebrate}
      />
    </div>
  );
}

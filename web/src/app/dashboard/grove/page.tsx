"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useGrove } from "@/hooks/useGrove";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Users, Plus, Link as LinkIcon, Clock, Zap, Copy } from "lucide-react";
import { toast } from "sonner";

const STATE_COLORS: Record<string, string> = {
  FOCUSED: "bg-green-500",
  IDLE: "bg-amber-500",
  DOZING: "bg-orange-500",
  AWAY: "bg-zinc-500",
};

export default function GrovePage() {
  const {
    grove, members, nudges, activeSprint, proposedSprint,
    pactProgress, loading, createGrove, joinGrove, proposeSprint, acceptSprint,
  } = useGrove();
  const [tab, setTab] = useState<"create" | "join">("create");
  const [name, setName] = useState("");
  const [goalHours, setGoalHours] = useState("3");
  const [inviteCode, setInviteCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[50vh]">
        <div className="animate-pulse text-muted-foreground">Loading grove...</div>
      </div>
    );
  }

  // No grove yet — show create/join
  if (!grove) {
    return (
      <div className="p-6 max-w-lg mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Join a Grove</h1>
          <p className="text-muted-foreground mt-1">Study groups that keep each other accountable</p>
        </div>

        <div className="flex gap-2">
          <Button variant={tab === "create" ? "default" : "outline"} onClick={() => setTab("create")}>
            <Plus className="h-4 w-4 mr-1" /> Create
          </Button>
          <Button variant={tab === "join" ? "default" : "outline"} onClick={() => setTab("join")}>
            <LinkIcon className="h-4 w-4 mr-1" /> Join
          </Button>
        </div>

        {tab === "create" ? (
          <Card>
            <CardHeader>
              <CardTitle>Create a Grove</CardTitle>
              <CardDescription>Start a study group and invite friends</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Grove Name</label>
                <Input placeholder="e.g. 6.042 Study Group" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Daily Goal (hours)</label>
                <Input type="number" min="1" max="12" step="0.5" value={goalHours} onChange={(e) => setGoalHours(e.target.value)} />
              </div>
              <Button
                className="w-full"
                disabled={!name.trim() || submitting}
                onClick={async () => {
                  setSubmitting(true);
                  const result = await createGrove(name.trim(), parseFloat(goalHours));
                  setSubmitting(false);
                  if (result) {
                    toast.success("Grove created! Share the invite code with friends.");
                    router.refresh();
                  }
                }}
              >
                {submitting ? "Creating..." : "Create Grove"}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Join a Grove</CardTitle>
              <CardDescription>Enter an invite code from a friend</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                placeholder="Enter invite code (e.g. A3B7CX)"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                className="text-center text-lg tracking-widest uppercase"
              />
              <Button
                className="w-full"
                disabled={!inviteCode.trim() || submitting}
                onClick={async () => {
                  setSubmitting(true);
                  const result = await joinGrove(inviteCode.trim());
                  setSubmitting(false);
                  if (result) {
                    toast.success(`Joined ${result.name}!`);
                    router.refresh();
                  } else {
                    toast.error("Invalid invite code");
                  }
                }}
              >
                {submitting ? "Joining..." : "Join Grove"}
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  // Has a grove — show details
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{grove.name}</h1>
          <p className="text-muted-foreground">
            {members.length} members · {grove.daily_goal_hours}h daily goal
          </p>
        </div>
        {grove.invite_code && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              navigator.clipboard.writeText(grove.invite_code!);
              toast.success("Invite code copied!");
            }}
          >
            <Copy className="h-4 w-4 mr-1" />
            {grove.invite_code}
          </Button>
        )}
      </div>

      {/* Members */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4" /> Members
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {pactProgress.map((m) => (
            <div key={m.user_id} className="flex items-center gap-3">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs">
                  {m.display_name.slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">{m.display_name}</span>
                  {m.is_self && <Badge variant="secondary" className="text-xs">You</Badge>}
                  <Badge className={`text-xs ${STATE_COLORS[m.state]}`}>{m.state}</Badge>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <Progress value={m.progress_pct} className="h-2 flex-1" />
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {m.today_focus_hours}h / {m.goal_hours}h
                  </span>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Sprint controls */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Zap className="h-4 w-4" /> Sprints
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {activeSprint && (
            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
              <p className="text-sm font-medium text-green-400">Sprint active — {activeSprint.duration_minutes} min</p>
            </div>
          )}
          {proposedSprint && !activeSprint && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between">
              <p className="text-sm text-amber-400">Sprint proposed — {proposedSprint.duration_minutes} min</p>
              <Button size="sm" onClick={() => acceptSprint(proposedSprint.id)}>Accept</Button>
            </div>
          )}
          {!activeSprint && !proposedSprint && (
            <Button variant="outline" className="w-full" onClick={() => proposeSprint(25)}>
              <Zap className="h-4 w-4 mr-1" /> Propose 25-min Sprint
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Recent nudges */}
      {nudges.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {nudges.slice(0, 5).map((n) => (
                <div key={n.id} className="flex items-start gap-2 text-sm">
                  <Clock className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                  <div>
                    <Badge variant="secondary" className="text-xs mr-1">{n.nudge_type}</Badge>
                    <span className="text-muted-foreground">{n.message}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

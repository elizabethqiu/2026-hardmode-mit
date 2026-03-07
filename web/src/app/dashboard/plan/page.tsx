"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { usePlan } from "@/hooks/usePlan";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Send, BookOpen, Play, SkipForward, CheckCircle, Clock, Zap, Bot,
} from "lucide-react";
import { toast } from "sonner";

interface PlannerMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  plan?: any;
}

const STATUS_ICONS: Record<string, typeof CheckCircle> = {
  completed: CheckCircle,
  active: Zap,
  skipped: SkipForward,
  pending: Clock,
};

const STATUS_COLORS: Record<string, string> = {
  completed: "text-green-400",
  active: "text-primary animate-pulse",
  skipped: "text-muted-foreground",
  pending: "text-muted-foreground",
};

export default function PlanPage() {
  const {
    plan, loading, activeSprint, nextPending, completedCount, totalMinutesDone,
    createPlan, startSprint, completeSprint, skipSprint,
  } = usePlan();
  const [messages, setMessages] = useState<PlannerMessage[]>([]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const sendToPlanner = useCallback(async (text: string) => {
    if (chatLoading) return;
    setChatLoading(true);

    const userMsg: PlannerMessage = { id: crypto.randomUUID(), role: "user", content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);

    const apiMessages = updatedMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await fetch("/api/claude/planner", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: apiMessages,
          context: plan ? { existing_plan: plan.plan_summary, sprints: plan.sprints } : null,
        }),
      });

      const data = await res.json();

      const assistantContent = data.needs_more_info
        ? data.question
        : data.message || data.plan_summary || "Here's your study plan.";

      const assistantMsg: PlannerMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: assistantContent,
        plan: !data.needs_more_info ? data : undefined,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Auto-save plan if sprints were generated
      if (!data.needs_more_info && data.sprints?.length > 0) {
        await createPlan(data.plan_summary || "", data.sprints);
        toast.success("Study plan saved!");
      }
    } catch (err) {
      console.error("Planner error:", err);
    } finally {
      setChatLoading(false);
    }
  }, [messages, chatLoading, plan, createPlan]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    sendToPlanner(input.trim());
    setInput("");
  }

  // Sprint timer
  const [sprintRemaining, setSprintRemaining] = useState<number | null>(null);
  useEffect(() => {
    if (!activeSprint?.started_at) { setSprintRemaining(null); return; }
    const tick = () => {
      const elapsed = (Date.now() - new Date(activeSprint.started_at!).getTime()) / 1000;
      const rem = activeSprint.duration_minutes * 60 - elapsed;
      setSprintRemaining(rem > 0 ? rem : 0);
      if (rem <= 0) {
        completeSprint(activeSprint.id);
        toast.success("Sprint completed!");
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [activeSprint, completeSprint]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[50vh]">
        <div className="animate-pulse text-muted-foreground">Loading plan...</div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Study Plan</h1>
        <p className="text-muted-foreground">Chat with Planning Claude to build your study session</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Planner chat */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Bot className="h-4 w-4" /> Planning Claude
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div ref={scrollRef} className="h-64 overflow-y-auto space-y-3 mb-3 pr-2">
              {messages.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-12">
                  Tell me what you need to study today...
                </p>
              )}
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"}`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="animate-pulse">🍄</div>
                  <span>Planning your session...</span>
                </div>
              )}
            </div>
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                placeholder="e.g. I need to study linear algebra for 2 hours"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={chatLoading}
              />
              <Button type="submit" size="icon" disabled={chatLoading || !input.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Sprint cards */}
        <div className="space-y-4">
          {/* Progress overview */}
          {plan && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <BookOpen className="h-4 w-4" /> Today&apos;s Progress
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">{plan.plan_summary}</p>
                <div className="flex items-center gap-3">
                  <Progress
                    value={(completedCount / Math.max(plan.sprints.length, 1)) * 100}
                    className="flex-1"
                  />
                  <span className="text-sm font-medium">
                    {completedCount}/{plan.sprints.length}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {totalMinutesDone} minutes studied
                </p>
              </CardContent>
            </Card>
          )}

          {/* Active sprint timer */}
          {activeSprint && sprintRemaining !== null && (
            <Card className="border-green-500/30 bg-green-500/5">
              <CardContent className="py-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="h-10 w-10 rounded-full bg-green-500/20 flex items-center justify-center animate-pulse">
                    <Zap className="h-5 w-5 text-green-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{activeSprint.topic}</p>
                    <p className="text-2xl font-bold tabular-nums text-green-400">
                      {String(Math.floor(sprintRemaining / 60)).padStart(2, "0")}:
                      {String(Math.floor(sprintRemaining % 60)).padStart(2, "0")}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => completeSprint(activeSprint.id)}>
                    <CheckCircle className="h-4 w-4 mr-1" /> Done
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => skipSprint(activeSprint.id)}>
                    <SkipForward className="h-4 w-4 mr-1" /> Skip
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Sprint list */}
          {plan?.sprints.map((sprint) => {
            const Icon = STATUS_ICONS[sprint.status] || Clock;
            return (
              <Card key={sprint.id} className={sprint.status === "active" ? "border-primary/30" : ""}>
                <CardContent className="py-3 flex items-center gap-3">
                  <Icon className={`h-5 w-5 shrink-0 ${STATUS_COLORS[sprint.status]}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{sprint.topic}</p>
                    <p className="text-xs text-muted-foreground">
                      {sprint.duration_minutes} min
                      {sprint.status === "completed" && sprint.actual_minutes > 0 && ` (${sprint.actual_minutes}m actual)`}
                    </p>
                  </div>
                  {sprint.status === "pending" && !activeSprint && (
                    <Button size="sm" variant="outline" onClick={() => startSprint(sprint.id)}>
                      <Play className="h-4 w-4" />
                    </Button>
                  )}
                  <Badge variant={sprint.status === "completed" ? "default" : "secondary"} className="text-xs">
                    {sprint.status}
                  </Badge>
                </CardContent>
              </Card>
            );
          })}

          {/* Start next sprint button */}
          {!activeSprint && nextPending && (
            <Button className="w-full" onClick={() => startSprint(nextPending.id)}>
              <Play className="h-4 w-4 mr-2" />
              Start: {nextPending.topic} ({nextPending.duration_minutes}m)
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

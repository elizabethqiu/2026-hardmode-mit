"use client";

import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";

interface Sprint {
  id: string;
  topic: string;
  duration_minutes: number;
  sprint_order: number;
  status: "pending" | "active" | "completed" | "skipped";
  started_at: string | null;
  completed_at: string | null;
  actual_minutes: number;
}

interface Plan {
  id: string;
  plan_date: string;
  plan_summary: string | null;
  sprints: Sprint[];
}

export function usePlan() {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const supabase = createClient();

  const loadPlan = useCallback(async () => {
    setLoading(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { setLoading(false); return; }

    const today = new Date().toISOString().split("T")[0];

    const { data: planData } = await supabase
      .from("study_plans")
      .select("*")
      .eq("user_id", user.id)
      .eq("plan_date", today)
      .single();

    if (!planData) { setLoading(false); setPlan(null); return; }

    const { data: sprintData } = await supabase
      .from("study_sprints")
      .select("*")
      .eq("plan_id", planData.id)
      .order("sprint_order", { ascending: true });

    setPlan({ ...planData, sprints: sprintData || [] });
    setLoading(false);
  }, [supabase]);

  useEffect(() => { loadPlan(); }, [loadPlan]);

  const createPlan = useCallback(async (
    summary: string,
    sprints: { topic: string; duration_minutes: number; order: number }[]
  ) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return null;

    const today = new Date().toISOString().split("T")[0];

    const { data: planData, error } = await supabase
      .from("study_plans")
      .upsert(
        { user_id: user.id, plan_date: today, plan_summary: summary },
        { onConflict: "user_id,plan_date" }
      )
      .select()
      .single();

    if (error || !planData) return null;

    // Delete existing sprints for this plan
    await supabase.from("study_sprints").delete().eq("plan_id", planData.id);

    // Insert new sprints
    const sprintRows = sprints.map((s) => ({
      plan_id: planData.id,
      topic: s.topic,
      duration_minutes: s.duration_minutes,
      sprint_order: s.order,
      status: "pending",
    }));

    await supabase.from("study_sprints").insert(sprintRows);

    await loadPlan();
    return planData;
  }, [supabase, loadPlan]);

  const startSprint = useCallback(async (sprintId: string) => {
    await supabase
      .from("study_sprints")
      .update({ status: "active", started_at: new Date().toISOString() })
      .eq("id", sprintId);
    await loadPlan();
  }, [supabase, loadPlan]);

  const completeSprint = useCallback(async (sprintId: string) => {
    const sprint = plan?.sprints.find((s) => s.id === sprintId);
    let actualMinutes = 0;
    if (sprint?.started_at) {
      actualMinutes = Math.round((Date.now() - new Date(sprint.started_at).getTime()) / 60000);
    }
    await supabase
      .from("study_sprints")
      .update({
        status: "completed",
        completed_at: new Date().toISOString(),
        actual_minutes: actualMinutes,
      })
      .eq("id", sprintId);
    await loadPlan();
  }, [supabase, plan, loadPlan]);

  const skipSprint = useCallback(async (sprintId: string) => {
    await supabase
      .from("study_sprints")
      .update({ status: "skipped" })
      .eq("id", sprintId);
    await loadPlan();
  }, [supabase, loadPlan]);

  const activeSprint = plan?.sprints.find((s) => s.status === "active") ?? null;
  const nextPending = plan?.sprints.find((s) => s.status === "pending") ?? null;
  const completedCount = plan?.sprints.filter((s) => s.status === "completed").length ?? 0;
  const totalMinutesDone = plan?.sprints
    .filter((s) => s.status === "completed")
    .reduce((acc, s) => acc + (s.actual_minutes || s.duration_minutes), 0) ?? 0;

  return {
    plan,
    loading,
    activeSprint,
    nextPending,
    completedCount,
    totalMinutesDone,
    createPlan,
    startSprint,
    completeSprint,
    skipSprint,
    refresh: loadPlan,
  };
}

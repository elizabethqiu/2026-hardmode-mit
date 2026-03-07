"use client";

import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";

interface GroveMember {
  user_id: string;
  display_name: string;
  state: string;
  focus_score: number;
  today_focus_hours: number;
  in_sprint: boolean;
  session_minutes: number;
}

interface Grove {
  id: string;
  name: string;
  daily_goal_hours: number;
  invite_code: string | null;
  created_by: string;
}

interface Sprint {
  id: string;
  grove_id: string;
  duration_minutes: number;
  status: string;
  started_at: string | null;
  proposed_by: string | null;
}

interface Nudge {
  id: string;
  nudge_type: string;
  message: string;
  target_user_id: string | null;
  created_at: string;
}

export function useGrove() {
  const [grove, setGrove] = useState<Grove | null>(null);
  const [members, setMembers] = useState<GroveMember[]>([]);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [nudges, setNudges] = useState<Nudge[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const supabase = createClient();

  useEffect(() => {
    loadGrove();
  }, []);

  async function loadGrove() {
    setLoading(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { setLoading(false); return; }
    setUserId(user.id);

    // Get user's grove membership
    const { data: membership } = await supabase
      .from("grove_members")
      .select("grove_id")
      .eq("user_id", user.id)
      .limit(1)
      .single();

    if (!membership) { setLoading(false); return; }

    // Get grove details
    const { data: groveData } = await supabase
      .from("groves")
      .select("*")
      .eq("id", membership.grove_id)
      .single();

    if (groveData) setGrove(groveData);

    // Get members with focus states
    const { data: memberData } = await supabase
      .from("focus_states")
      .select("*")
      .eq("grove_id", membership.grove_id);

    if (memberData) {
      // Fetch display names
      const userIds = memberData.map((m: any) => m.user_id);
      const { data: users } = await supabase
        .from("users")
        .select("id, display_name")
        .in("id", userIds);

      const nameMap = new Map((users || []).map((u: any) => [u.id, u.display_name]));
      setMembers(
        memberData.map((m: any) => ({
          ...m,
          display_name: nameMap.get(m.user_id) || "Unknown",
        }))
      );
    }

    // Get recent sprints
    const { data: sprintData } = await supabase
      .from("sprints")
      .select("*")
      .eq("grove_id", membership.grove_id)
      .order("created_at", { ascending: false })
      .limit(5);

    if (sprintData) setSprints(sprintData);

    // Get recent nudges
    const { data: nudgeData } = await supabase
      .from("grove_nudges")
      .select("*")
      .eq("grove_id", membership.grove_id)
      .order("created_at", { ascending: false })
      .limit(10);

    if (nudgeData) setNudges(nudgeData);

    // Subscribe to realtime changes
    supabase
      .channel(`grove-${membership.grove_id}`)
      .on("postgres_changes", { event: "*", schema: "public", table: "focus_states", filter: `grove_id=eq.${membership.grove_id}` },
        (payload: any) => {
          const record = payload.new;
          if (record) {
            setMembers((prev) => {
              const idx = prev.findIndex((m) => m.user_id === record.user_id);
              if (idx >= 0) {
                const updated = [...prev];
                updated[idx] = { ...updated[idx], ...record };
                return updated;
              }
              return [...prev, record];
            });
          }
        }
      )
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "grove_nudges", filter: `grove_id=eq.${membership.grove_id}` },
        (payload: any) => {
          if (payload.new) setNudges((prev) => [payload.new, ...prev].slice(0, 10));
        }
      )
      .on("postgres_changes", { event: "*", schema: "public", table: "sprints", filter: `grove_id=eq.${membership.grove_id}` },
        (payload: any) => {
          if (payload.new) {
            setSprints((prev) => {
              const idx = prev.findIndex((s) => s.id === payload.new.id);
              if (idx >= 0) {
                const updated = [...prev];
                updated[idx] = payload.new;
                return updated;
              }
              return [payload.new, ...prev].slice(0, 5);
            });
          }
        }
      )
      .subscribe();

    setLoading(false);
  }

  const createGrove = useCallback(async (name: string, dailyGoalHours: number) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return null;

    const inviteCode = Math.random().toString(36).slice(2, 8).toUpperCase();

    const { data: newGrove, error } = await supabase
      .from("groves")
      .insert({ name, created_by: user.id, daily_goal_hours: dailyGoalHours, invite_code: inviteCode })
      .select()
      .single();

    if (error || !newGrove) return null;

    await supabase.from("grove_members").insert({
      grove_id: newGrove.id,
      user_id: user.id,
      led_position: 0,
    });

    // Initialize focus state
    await supabase.from("focus_states").upsert({
      user_id: user.id,
      grove_id: newGrove.id,
      state: "AWAY",
      focus_score: 0,
      session_minutes: 0,
      today_focus_hours: 0,
      in_sprint: false,
    }, { onConflict: "user_id" });

    setGrove(newGrove);
    return newGrove;
  }, [supabase]);

  const joinGrove = useCallback(async (inviteCode: string) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return null;

    const { data: groveData } = await supabase
      .from("groves")
      .select("*")
      .eq("invite_code", inviteCode.toUpperCase())
      .single();

    if (!groveData) return null;

    // Count existing members for LED position
    const { count } = await supabase
      .from("grove_members")
      .select("*", { count: "exact", head: true })
      .eq("grove_id", groveData.id);

    await supabase.from("grove_members").insert({
      grove_id: groveData.id,
      user_id: user.id,
      led_position: count || 0,
    });

    await supabase.from("focus_states").upsert({
      user_id: user.id,
      grove_id: groveData.id,
      state: "AWAY",
      focus_score: 0,
      session_minutes: 0,
      today_focus_hours: 0,
      in_sprint: false,
    }, { onConflict: "user_id" });

    setGrove(groveData);
    return groveData;
  }, [supabase]);

  const proposeSprint = useCallback(async (durationMinutes = 25) => {
    if (!grove || !userId) return;
    await supabase.from("sprints").insert({
      grove_id: grove.id,
      proposed_by: userId,
      duration_minutes: durationMinutes,
      status: "proposed",
    });
  }, [grove, userId, supabase]);

  const acceptSprint = useCallback(async (sprintId: string) => {
    await supabase
      .from("sprints")
      .update({ status: "active", started_at: new Date().toISOString() })
      .eq("id", sprintId);
  }, [supabase]);

  const activeSprint = sprints.find((s) => s.status === "active");
  const proposedSprint = sprints.find((s) => s.status === "proposed");

  const pactProgress = members.map((m) => ({
    ...m,
    goal_hours: grove?.daily_goal_hours || 3,
    progress_pct: Math.min(100, Math.round(((m.today_focus_hours || 0) / (grove?.daily_goal_hours || 3)) * 100)),
    is_self: m.user_id === userId,
  }));

  return {
    grove,
    members,
    sprints,
    nudges,
    loading,
    userId,
    activeSprint,
    proposedSprint,
    pactProgress,
    createGrove,
    joinGrove,
    proposeSprint,
    acceptSprint,
    refresh: loadGrove,
  };
}

// Supabase Edge Function — Daily Digest
// Aggregates a full day of focus_history data, calls Insight Claude, writes summary.
// Triggered at end of day (manually, cron, or orchestrator schedule).

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import Anthropic from "https://esm.sh/@anthropic-ai/sdk@0.32.1";

const INSIGHT_PROMPT = `You are Enoki Insight — you analyze a full day of focus data for a study grove.
You receive timestamped focus state snapshots (recorded every ~60 seconds) for each member.
Produce a concise daily summary with specific stats and 2-4 actionable insights.

Output ONLY valid JSON:
{
  "summary": "<2-3 sentence human-readable summary of the grove's day>",
  "highlights": ["<specific highlight with numbers>", "<another>"],
  "member_stats": [
    {"name": "<display_name>", "focus_hours": <float>, "best_streak_min": <int>}
  ]
}`;

Deno.serve(async (req) => {
  try {
    const { grove_id, date } = await req.json();
    if (!grove_id || !date) {
      return new Response(JSON.stringify({ error: "grove_id and date required" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Fetch all focus_history records for the given date
    const dayStart = `${date}T00:00:00Z`;
    const dayEnd = `${date}T23:59:59Z`;

    const { data: history } = await supabase
      .from("focus_history")
      .select("user_id, state, focus_score, recorded_at, users!inner(display_name)")
      .eq("grove_id", grove_id)
      .gte("recorded_at", dayStart)
      .lte("recorded_at", dayEnd)
      .order("recorded_at", { ascending: true });

    if (!history || history.length === 0) {
      const empty = { summary: "No activity recorded for this day.", highlights: [], member_stats: [] };
      await supabase.from("daily_summaries").upsert({
        grove_id,
        date,
        summary_json: empty,
      }, { onConflict: "grove_id,date" });

      return new Response(JSON.stringify(empty), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // Pre-aggregate stats per member for Claude context
    const memberMap: Record<string, { name: string; snapshots: { state: string; time: string }[] }> = {};
    for (const row of history as any[]) {
      const uid = row.user_id;
      const name = row.users?.display_name ?? "Unknown";
      if (!memberMap[uid]) {
        memberMap[uid] = { name, snapshots: [] };
      }
      memberMap[uid].snapshots.push({
        state: row.state,
        time: row.recorded_at,
      });
    }

    // Calculate basic stats per member
    const memberStats = Object.entries(memberMap).map(([uid, data]) => {
      const total = data.snapshots.length;
      const focused = data.snapshots.filter(s => s.state === "FOCUSED").length;
      const focusHours = (focused / 60).toFixed(1); // each snapshot ~1 min
      return {
        user_id: uid,
        name: data.name,
        total_snapshots: total,
        focused_snapshots: focused,
        focus_hours_approx: parseFloat(focusHours),
        focus_percentage: total > 0 ? Math.round((focused / total) * 100) : 0,
      };
    });

    const anthropic = new Anthropic({ apiKey: Deno.env.get("ANTHROPIC_API_KEY") });
    const msg = await anthropic.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 512,
      system: INSIGHT_PROMPT,
      messages: [{
        role: "user",
        content: `Date: ${date}\nGrove member stats:\n${JSON.stringify(memberStats, null, 2)}\n\nTotal snapshots across grove: ${history.length}`,
      }],
    });

    const text = msg.content[0].type === "text" ? msg.content[0].text : "{}";
    const parsed = JSON.parse(text.replace(/```json\n?|\n?```/g, "").trim());

    await supabase.from("daily_summaries").upsert({
      grove_id,
      date,
      summary_json: parsed,
    }, { onConflict: "grove_id,date" });

    return new Response(JSON.stringify(parsed), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
});

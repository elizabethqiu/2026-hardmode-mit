import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@/lib/supabase/server";
import { PERSONAL_SYSTEM_PROMPT, PERSONAL_TOOLS } from "@/lib/claude/prompts";

const MAX_TOOL_ROUNDS = 3;
const MAX_HISTORY = 20;

export async function POST(request: Request) {
  try {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const body = await request.json();
    const { user_message, payload } = body;

    // Load conversation history
    const { data: historyRows } = await supabase
      .from("conversation_messages")
      .select("role, content")
      .eq("user_id", user.id)
      .order("created_at", { ascending: true })
      .limit(MAX_HISTORY);

    const messages: any[] = (historyRows || []).map((r: any) => ({
      role: r.role,
      content: r.content,
    }));

    // Add user message (either typed text or sensor payload)
    const userContent = user_message
      ? user_message
      : "Current sensor data and context:\n" + JSON.stringify(payload, null, 2);

    messages.push({ role: "user", content: userContent });

    // Save user message
    await supabase.from("conversation_messages").insert({
      user_id: user.id,
      role: "user",
      content: userContent,
    });

    // Call Claude with tool loop
    const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY! });

    let finalResponse: any = null;

    for (let round = 0; round <= MAX_TOOL_ROUNDS; round++) {
      const msg = await anthropic.messages.create({
        model: "claude-sonnet-4-6",
        max_tokens: 512,
        system: PERSONAL_SYSTEM_PROMPT,
        messages,
        tools: PERSONAL_TOOLS,
      });

      if (msg.stop_reason === "tool_use") {
        // Serialize assistant content for history
        const assistantContent = msg.content.map((block: any) => {
          if (block.type === "text") return { type: "text", text: block.text };
          if (block.type === "tool_use")
            return { type: "tool_use", id: block.id, name: block.name, input: block.input };
          return block;
        });
        messages.push({ role: "assistant", content: assistantContent });

        // Execute tools
        const toolResults: any[] = [];
        for (const block of msg.content) {
          if (block.type === "tool_use") {
            const result = await executeTool(block.name, block.input, user.id, supabase);
            toolResults.push({
              type: "tool_result",
              tool_use_id: block.id,
              content: JSON.stringify(result),
            });
          }
        }
        messages.push({ role: "user", content: toolResults });
        continue;
      }

      // Final text response
      for (const block of msg.content) {
        if (block.type === "text") {
          let text = block.text.trim();
          if (text.startsWith("```")) {
            text = text.split("\n").filter((l: string) => !l.startsWith("```")).join("\n").trim();
          }
          try {
            finalResponse = JSON.parse(text);
          } catch {
            finalResponse = { message: text, enoki_mood: "watchful", height: 0.7, led_color: [200, 180, 120], led_brightness: 0.75, speak_message: false, nudge_intensity: "none" };
          }
          break;
        }
      }
      break;
    }

    if (!finalResponse) {
      finalResponse = { message: "", enoki_mood: "watchful", height: 0.7, led_color: [200, 180, 120], led_brightness: 0.75, speak_message: false, nudge_intensity: "none" };
    }

    // Save assistant response
    await supabase.from("conversation_messages").insert({
      user_id: user.id,
      role: "assistant",
      content: finalResponse.message || JSON.stringify(finalResponse),
    });

    // Trim old messages (keep latest MAX_HISTORY)
    const { count } = await supabase
      .from("conversation_messages")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id);

    if (count && count > MAX_HISTORY * 2) {
      const { data: oldest } = await supabase
        .from("conversation_messages")
        .select("id")
        .eq("user_id", user.id)
        .order("created_at", { ascending: true })
        .limit(count - MAX_HISTORY);

      if (oldest && oldest.length > 0) {
        await supabase
          .from("conversation_messages")
          .delete()
          .in("id", oldest.map((r: any) => r.id));
      }
    }

    return NextResponse.json(finalResponse);
  } catch (e) {
    console.error("Personal Claude error:", e);
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

async function executeTool(name: string, input: any, userId: string, supabase: any) {
  switch (name) {
    case "start_sprint": {
      const minutes = input.minutes || 25;
      // Find user's grove
      const { data: membership } = await supabase
        .from("grove_members")
        .select("grove_id")
        .eq("user_id", userId)
        .limit(1)
        .single();

      if (membership) {
        await supabase.from("sprints").insert({
          grove_id: membership.grove_id,
          proposed_by: userId,
          duration_minutes: minutes,
          status: "proposed",
        });
        return { ok: true, minutes, proposed_to_grove: true };
      }
      return { ok: true, minutes, proposed_to_grove: false };
    }

    case "set_goal": {
      const description = input.description || "";
      await supabase.from("user_goals").upsert(
        { user_id: userId, description, updated_at: new Date().toISOString() },
        { onConflict: "user_id" }
      );
      return { ok: true, goal: description };
    }

    case "check_grove_status": {
      const { data: membership } = await supabase
        .from("grove_members")
        .select("grove_id")
        .eq("user_id", userId)
        .limit(1)
        .single();

      if (!membership) return { ok: false, error: "Not in a grove" };

      const { data: states } = await supabase
        .from("focus_states")
        .select("user_id, state, focus_score, today_focus_hours, in_sprint")
        .eq("grove_id", membership.grove_id);

      const { data: users } = await supabase
        .from("users")
        .select("id, display_name")
        .in("id", (states || []).map((s: any) => s.user_id));

      const nameMap = new Map((users || []).map((u: any) => [u.id, u.display_name]));

      return {
        ok: true,
        members: (states || []).map((s: any) => ({
          name: nameMap.get(s.user_id) || "Unknown",
          state: s.state,
          focus_hours: s.today_focus_hours,
          in_sprint: s.in_sprint,
        })),
      };
    }

    case "update_mushroom": {
      return { ok: true, mood: input.mood, height: input.height };
    }

    default:
      return { ok: false, error: `Unknown tool: ${name}` };
  }
}

import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@/lib/supabase/server";
import { PLANNER_SYSTEM_PROMPT } from "@/lib/claude/prompts";

export async function POST(request: Request) {
  try {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const body = await request.json();
    const { messages: clientMessages, context } = body;

    const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY! });

    const systemPrompt = PLANNER_SYSTEM_PROMPT + (
      context ? `\n\nContext:\n${JSON.stringify(context, null, 2)}` : ""
    );

    const msg = await anthropic.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 1024,
      system: systemPrompt,
      messages: clientMessages || [],
    });

    let text = "";
    for (const block of msg.content) {
      if (block.type === "text") {
        text = block.text.trim();
        break;
      }
    }

    if (text.startsWith("```")) {
      text = text.split("\n").filter((l) => !l.startsWith("```")).join("\n").trim();
    }

    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = {
        needs_more_info: true,
        question: text || "Could you tell me more about what you'd like to study?",
        plan_summary: "",
        sprints: [],
        message: "",
        propose_to_grove: false,
      };
    }

    return NextResponse.json(parsed);
  } catch (e) {
    console.error("Planner Claude error:", e);
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

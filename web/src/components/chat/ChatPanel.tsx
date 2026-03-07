"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { MessageBubble } from "./MessageBubble";
import { Send, Bot } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  mood?: string;
}

interface ChatPanelProps {
  focusState: string;
  focusDuration: number;
  sessionFocusPct: number;
  onMushroomUpdate: (response: Record<string, any>) => void;
  onCelebrate: () => void;
}

export function ChatPanel({
  focusState,
  focusDuration,
  sessionFocusPct,
  onMushroomUpdate,
  onCelebrate,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastAutoCall = useRef(0);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string, isAuto = false) => {
      if (loading) return;
      setLoading(true);

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: isAuto ? `[Auto] ${text}` : text,
      };
      if (!isAuto) setMessages((prev) => [...prev, userMsg]);

      try {
        const res = await fetch("/api/claude/personal", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_message: isAuto ? null : text,
            payload: {
              current_state: focusState,
              state_duration_seconds: Math.round(focusDuration),
              session_focus_percentage: sessionFocusPct,
              time_of_day: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
            },
          }),
        });

        const data = await res.json();

        if (data.enoki_mood) {
          onMushroomUpdate(data);
        }

        if (data.message) {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: data.message,
              mood: data.enoki_mood,
            },
          ]);
        }
      } catch (err) {
        console.error("Claude call failed:", err);
      } finally {
        setLoading(false);
      }
    },
    [focusState, focusDuration, sessionFocusPct, loading, onMushroomUpdate]
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input.trim());
    setInput("");
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Bot className="h-4 w-4" /> Chat with Enoki
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={scrollRef} className="h-48 overflow-y-auto space-y-3 mb-3 pr-2">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">
              Start the webcam and talk to your mushroom companion...
            </p>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} role={msg.role} content={msg.content} mood={msg.mood} />
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="animate-pulse">🍄</div>
              <span>Enoki is thinking...</span>
            </div>
          )}
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            placeholder="Talk to Enoki..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <Button type="submit" size="icon" disabled={loading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

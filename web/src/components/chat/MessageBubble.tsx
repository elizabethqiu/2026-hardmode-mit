import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  mood?: string;
}

const MOOD_EMOJI: Record<string, string> = {
  focused: "😊",
  watchful: "👀",
  concerned: "😟",
  gentle: "🤗",
  urgent: "😤",
};

export function MessageBubble({ role, content, mood }: MessageBubbleProps) {
  const isAssistant = role === "assistant";

  return (
    <div className={cn("flex", isAssistant ? "justify-start" : "justify-end")}>
      <div
        className={cn(
          "max-w-[80%] rounded-xl px-3 py-2 text-sm",
          isAssistant
            ? "bg-secondary text-secondary-foreground"
            : "bg-primary text-primary-foreground"
        )}
      >
        {isAssistant && mood && (
          <span className="mr-1">{MOOD_EMOJI[mood] || "🍄"}</span>
        )}
        {content}
      </div>
    </div>
  );
}

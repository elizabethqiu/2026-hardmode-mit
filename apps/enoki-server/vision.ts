import { anthropic } from "./claude";

export type VisionRequestBody = {
  task?: string;
  image?: string;
};

export async function runVisionCheck(task: string, image: string) {
  const response = await anthropic.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 120,
    temperature: 0,
    messages: [
      {
        role: "user",
        content: [
          {
            type: "text",
            text: `The user's current task is: ${task}.
Look at this image from smart glasses and decide whether the user still appears to be doing that task.
Return valid JSON only with this exact shape:
{
  "on_task": true,
  "confidence": 0.0,
  "reason": "short explanation"
}`,
          },
          {
            type: "image",
            source: {
              type: "base64",
              media_type: "image/jpeg",
              data: image,
            },
          },
        ],
      },
    ],
  });

  const textBlocks = response.content.filter(
    (
      block,
    ): block is Extract<(typeof response.content)[number], { type: "text" }> =>
      block.type === "text",
  );

  return (
    textBlocks
      .map((block) => block.text)
      .join("\n")
      .trim() || "{}"
  );
}

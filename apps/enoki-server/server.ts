import { handleRequest } from "./index";

process.on("uncaughtException", (error) => {
  console.error("uncaughtException:", error);
});

process.on("unhandledRejection", (reason) => {
  console.error("unhandledRejection:", reason);
});

const PORT = Number(process.env.PORT || 3000);

const server = Bun.serve({
  port: PORT,
  fetch: async (req) => {
    try {
      return await handleRequest(req);
    } catch (error) {
      console.error("unhandled fetch error:", error);
      return new Response(
        JSON.stringify({
          error: "internal server error",
        }),
        {
          status: 500,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
          },
        },
      );
    }
  },
  error(error) {
    console.error("bun server error:", error);
    return new Response(
      JSON.stringify({
        error: "server crashed while handling request",
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      },
    );
  },
});

console.log(`enoki server running on http://localhost:${server.port}`);

import {
  getErrorInfo,
  getFailureEvent,
  runGaPipeline,
  type RunGaRequestBody,
  type StreamEvent,
} from "@/lib/server/ga-runner";
import { buildChildEnv, getRuntimeConfig } from "@/lib/server/runtime-config";

export async function POST(request: Request) {
  try {
    const runtimeConfig = getRuntimeConfig();
    const childEnv = buildChildEnv(runtimeConfig);

    const body = (await request.json()) as RunGaRequestBody;
    const { k } = body;

    if (typeof k !== "number" || k < 1) {
      return new Response(JSON.stringify({ error: "Invalid k value" }), { status: 400 });
    }

    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      async start(controller) {
        function sendEvent(data: StreamEvent) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
        }

        try {
          await runGaPipeline(body, runtimeConfig, childEnv, sendEvent);
          controller.close();
        } catch (error: unknown) {
          console.error("Optimization error:", error);
          sendEvent(getFailureEvent(error, runtimeConfig));
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error: unknown) {
    const errorInfo = getErrorInfo(error);
    console.error("Error starting GA stream:", error);
    return new Response(JSON.stringify({
      error: "Failed to start optimization",
      details: errorInfo.message,
    }), { status: 500, headers: { "Content-Type": "application/json" } });
  }
}

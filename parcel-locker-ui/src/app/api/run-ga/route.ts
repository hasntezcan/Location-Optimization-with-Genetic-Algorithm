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

    if (typeof k !== "number" || !Number.isInteger(k) || k < 1 || k > 30) {
      return new Response(JSON.stringify({ error: "Invalid k value" }), { status: 400 });
    }

    if (
      body.fixedFacilityIds !== undefined &&
      (
        !Array.isArray(body.fixedFacilityIds) ||
        body.fixedFacilityIds.some((value) => {
          const id = typeof value === "number" ? value : Number(value);
          return !Number.isInteger(id) || id <= 0;
        })
      )
    ) {
      return new Response(JSON.stringify({ error: "Invalid fixedFacilityIds value" }), { status: 400 });
    }

    if (
      body.includeExistingLockers !== undefined &&
      typeof body.includeExistingLockers !== "boolean"
    ) {
      return new Response(JSON.stringify({ error: "Invalid includeExistingLockers value" }), { status: 400 });
    }

    const encoder = new TextEncoder();
    let isStreamClosed = false;

    const stream = new ReadableStream({
      async start(controller) {
        function sendEvent(data: StreamEvent) {
          if (isStreamClosed) return;
          try {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
          } catch {
            isStreamClosed = true;
          }
        }

        try {
          await runGaPipeline(body, runtimeConfig, childEnv, sendEvent);
          if (!isStreamClosed) {
            isStreamClosed = true;
            controller.close();
          }
        } catch (error: unknown) {
          console.error("Optimization error:", error);
          sendEvent(getFailureEvent(error, runtimeConfig));
          if (!isStreamClosed) {
            isStreamClosed = true;
            controller.close();
          }
        }
      },
      cancel() {
        isStreamClosed = true;
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

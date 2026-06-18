export type RunGaParams = {
  k: number;
  populationSize: number;
  maxGenerations: number;
  mutationRate: number;
  crossoverRate: number;
  archiveSize: number;
  randomSeed: number | null;
  fixedFacilityIds?: Array<number | string>;
  includeExistingLockers?: boolean;
};

export type GaStreamEvent = {
  stage?: string;
  currentGeneration?: number;
  maxGenerations?: number;
  progressPercent?: number;
  log?: string;
  message?: string;
  error?: string;
  stderr?: string;
  success?: boolean;
  paretoInfo?: string;
};

export type RunGaCallbacks = {
  onProgress?: (event: GaStreamEvent) => void;
  onStatus?: (message: string) => void;
  onComplete?: (event: GaStreamEvent) => void;
  onError?: (error: Error) => void;
};

export async function runGaOptimization(
  params: RunGaParams,
  callbacks: RunGaCallbacks = {}
): Promise<void> {
  try {
    const response = await fetch("/api/run-ga", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error("Konum önerisi oluşturma akışı başlatılamadı");
    }

    if (!response.body) {
      throw new Error("Sunucudan öneri yanıtı alınamadı");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (part.startsWith("data: ")) {
          try {
            const data = JSON.parse(part.slice(6)) as GaStreamEvent;

            if (data.stage) callbacks.onStatus?.(data.stage);
            callbacks.onProgress?.(data);

            if (data.error) {
              throw new Error(data.error + (data.stderr ? `\n\n${data.stderr}` : ""));
            }

            if (data.success) {
              callbacks.onComplete?.(data);
              break;
            }
          } catch (e) {
            if (e instanceof Error && e.message !== "Unexpected end of JSON input") {
              throw e;
            }
          }
        }
      }
    }
  } catch (error: unknown) {
    const normalized = error instanceof Error ? error : new Error(String(error));
    callbacks.onError?.(normalized);
    throw normalized;
  }
}

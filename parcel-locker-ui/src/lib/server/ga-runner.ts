import { spawn } from "child_process";
import { promises as fs } from "fs";
import path from "path";
import { runPythonScript } from "@/lib/python-runner";
import type { RuntimeConfig } from "@/lib/server/runtime-config";
import {
  deriveOptimizerInputsFromScenario,
  type ScenarioAdapterResult,
} from "@/lib/server/scenario-adapter";

export type StreamEvent = Record<string, unknown>;

export type RunGaRequestBody = {
  // Required for the V0 request shape (no scenarioPath). When scenarioPath
  // is present, k/fixedFacilityIds/includeExistingLockers are derived from
  // the scenario instead and any client-sent values here are ignored.
  k?: number;
  populationSize?: number;
  maxGenerations?: number;
  mutationRate?: number;
  crossoverRate?: number;
  archiveSize?: number;
  randomSeed?: number | string | null;
  fixedFacilityIds?: Array<number | string>;
  includeExistingLockers?: boolean;
  // Scenario-driven request fields (additive; see scenario-adapter.ts).
  scenarioPath?: string;
  forceExistingOff?: boolean;
  targetTotalFacilityCount?: number;
};

type ResolvedRunGaRequestBody = Omit<RunGaRequestBody, "fixedFacilityIds"> & {
  fixedFacilityIds: number[];
};

const MIN_MAX_GENERATIONS = 500;

export type ProcessErrorInfo = {
  message: string;
  scriptPath?: string;
  stderr?: string;
};

export function getErrorInfo(error: unknown): ProcessErrorInfo {
  if (error instanceof Error) {
    return { message: error.message };
  }

  if (typeof error === "object" && error !== null) {
    const value = error as { message?: unknown; scriptPath?: unknown; stderr?: unknown };
    return {
      message: typeof value.message === "string" ? value.message : String(error),
      scriptPath: typeof value.scriptPath === "string" ? value.scriptPath : undefined,
      stderr: typeof value.stderr === "string" ? value.stderr : undefined,
    };
  }

  return { message: String(error) };
}

function buildMavenExecArgs(body: RunGaRequestBody): string[] {
  const args: string[] = [];
  if (body.k !== undefined) args.push("--k", String(body.k));
  if (body.populationSize !== undefined) args.push("--populationSize", String(body.populationSize));
  if (body.maxGenerations !== undefined) args.push("--maxGenerations", String(body.maxGenerations));
  if (body.mutationRate !== undefined) args.push("--mutationRate", String(body.mutationRate));
  if (body.crossoverRate !== undefined) args.push("--crossoverRate", String(body.crossoverRate));
  if (body.archiveSize !== undefined) args.push("--archiveSize", String(body.archiveSize));
  if (body.randomSeed !== undefined && body.randomSeed !== null && body.randomSeed !== "") {
    args.push("--randomSeed", String(body.randomSeed));
  }
  if (body.fixedFacilityIds?.length) {
    args.push("--fixedFacilityIds", body.fixedFacilityIds.join(","));
  }
  if (body.includeExistingLockers) {
    args.push("--includeExistingLockers");
  }
  return args;
}

function normalizeFixedFacilityIds(rawIds: Array<number | string> | undefined): number[] {
  if (!rawIds?.length) return [];

  const normalized = new Set<number>();
  for (const rawId of rawIds) {
    const id = typeof rawId === "number" ? rawId : Number(rawId);
    if (!Number.isInteger(id) || id <= 0) {
      throw new Error(`Invalid fixed facility ID: ${String(rawId)}`);
    }
    normalized.add(id);
  }
  return [...normalized];
}

async function resolveRunBody(
  body: RunGaRequestBody
): Promise<ResolvedRunGaRequestBody> {
  const fixedFacilityIds = normalizeFixedFacilityIds(body.fixedFacilityIds);

  return {
    ...body,
    maxGenerations: Math.max(MIN_MAX_GENERATIONS, body.maxGenerations ?? MIN_MAX_GENERATIONS),
    fixedFacilityIds,
  };
}

async function runJavaGa(
  body: RunGaRequestBody,
  runtimeConfig: RuntimeConfig,
  childEnv: NodeJS.ProcessEnv,
  sendEvent: (data: StreamEvent) => void
): Promise<void> {
  const resolvedBody = await resolveRunBody(body);
  const args = buildMavenExecArgs(resolvedBody);

  console.log(`Running Maven GA with args: ${args.join(" ")}`);

  const execArgsStr = args.length > 0 ? `-Dexec.args=${args.join(" ")}` : "";
  const mvnArgs = ["compile", "exec:java"];
  if (execArgsStr) {
    mvnArgs.push(execArgsStr);
  }

  sendEvent({ stage: "Running Java GA", message: "Compiling and starting GA..." });

  const isWindows = process.platform === "win32";
  const mavenCmd = runtimeConfig.mavenCmd || (isWindows ? "mvn.cmd" : "mvn");
  const command = isWindows ? "cmd.exe" : mavenCmd;
  const commandArgs = isWindows
    ? ["/d", "/s", "/c", mavenCmd, ...mvnArgs]
    : mvnArgs;

  await new Promise<void>((resolve, reject) => {
    const proc = spawn(command, commandArgs, {
      cwd: runtimeConfig.projectRoot,
      env: childEnv,
      windowsHide: true,
    });

    let errorBuffer = "";
    const timeoutId = setTimeout(() => {
      proc.kill();
      reject(new Error(`Java GA process timed out after ${runtimeConfig.maxRuntimeMs} ms.`));
    }, runtimeConfig.maxRuntimeMs);

    proc.stdout.on("data", (data) => {
      const lines = data.toString().split("\n");
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        const progressMatch = trimmed.match(/PROGRESS\s+generation=(\d+)\s+max=(\d+)/i);
        if (progressMatch) {
          const currentGeneration = parseInt(progressMatch[1], 10);
          const parsedMaxGenerations = parseInt(progressMatch[2], 10);
          const pct = Math.round((currentGeneration / parsedMaxGenerations) * 100);
          sendEvent({
            stage: "Running Java GA",
            currentGeneration,
            maxGenerations: parsedMaxGenerations,
            progressPercent: pct,
            log: `[Gen ${currentGeneration}/${parsedMaxGenerations}] Optimizing… ${pct}%`,
          });
        } else if (trimmed.startsWith("STAGE")) {
          sendEvent({
            stage: "Running Java GA",
            log: trimmed,
          });
        } else if (
          trimmed.startsWith("BOUNDS_DEBUG") ||
          trimmed.includes("BOUNDS DEBUG") ||
          trimmed.includes("ASSESSMENT BOUNDS") ||
          trimmed.includes("NORMALIZED RANGES") ||
          trimmed.includes("HYPERVOLUME") ||
          trimmed.includes("Total runtime") ||
          trimmed.includes("Bounds pool size") ||
          trimmed.includes("Initial archive") ||
          trimmed.includes("Final archive") ||
          trimmed.includes("ideal") ||
          trimmed.includes("nadir") ||
          trimmed.includes("Ideal") ||
          trimmed.includes("Nadir") ||
          trimmed.includes("Initial ND") ||
          trimmed.includes("Final ND") ||
          trimmed.includes("hypervolume")
        ) {
          console.log(`[java] ${trimmed}`);
          if (!trimmed.includes("BOUNDS_DEBUG") && !trimmed.includes("BOUNDS DEBUG")) {
            sendEvent({ stage: "Running Java GA", log: trimmed });
          }
        }
      }
    });

    proc.stderr.on("data", (data) => {
      errorBuffer += data.toString();
    });

    proc.on("error", (err) => {
      clearTimeout(timeoutId);
      const detailedError = [
        "Failed to spawn Maven process.",
        `Command: ${command}`,
        `Args: ${commandArgs.join(" ")}`,
        `CWD: ${runtimeConfig.projectRoot}`,
        `Platform: ${process.platform}`,
        `Original error: ${err.message}`,
      ].join("\n");
      reject(new Error(detailedError));
    });

    proc.on("close", (code) => {
      clearTimeout(timeoutId);
      if (code !== 0) {
        reject(new Error(`Java GA process failed with exit code ${code}. Stderr: ${errorBuffer}`));
      } else {
        resolve();
      }
    });
  });
}

function buildScenarioSummary(scenarioResult: ScenarioAdapterResult): Record<string, unknown> {
  return {
    scenarioId: scenarioResult.scenarioId,
    scenarioPath: scenarioResult.scenarioPath,
    existingEnabled: scenarioResult.existingEnabled,
    facilityCountMode: scenarioResult.facilityCountMode,
    targetNewFacilityCount: scenarioResult.targetNewFacilityCount,
    targetTotalFacilityCount: scenarioResult.targetTotalFacilityCount,
    physicalFacilityCount: scenarioResult.physicalFacilityCount,
    effectiveFacilityLocationCount: scenarioResult.effectiveFacilityLocationCount,
    activeExistingCandidateCount: scenarioResult.activeExistingCandidateIds.length,
    lockedCandidateCount: scenarioResult.lockedCandidateIds.length,
    disabledCandidateCount: scenarioResult.disabledCandidateIds.length,
    optimizerRunRequired: scenarioResult.optimizerRunRequired,
    adapterWarnings: scenarioResult.warnings,
  };
}

/**
 * Merge scenario metadata into the run_metadata.json Java already wrote,
 * so a scenario-driven run's metadata is traceable without duplicating
 * Java's metadata writer. No-op (with a logged warning) if the file is
 * missing or unreadable — this is best-effort, not a new metadata system.
 */
async function mergeScenarioMetadataIntoRunMetadata(
  runtimeConfig: RuntimeConfig,
  scenarioResult: ScenarioAdapterResult
): Promise<void> {
  const runMetadataPath = path.join(runtimeConfig.outputDir, "run_metadata.json");
  try {
    const raw = await fs.readFile(runMetadataPath, "utf-8");
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    parsed.scenario = buildScenarioSummary(scenarioResult);
    await fs.writeFile(runMetadataPath, JSON.stringify(parsed, null, 2) + "\n", "utf-8");
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`Could not merge scenario metadata into ${runMetadataPath}:`, message);
  }
}

export async function runGaPipeline(
  body: RunGaRequestBody,
  runtimeConfig: RuntimeConfig,
  childEnv: NodeJS.ProcessEnv,
  sendEvent: (data: StreamEvent) => void
): Promise<void> {
  sendEvent({ stage: "Starting optimization", message: "Preparing Maven environment..." });

  let effectiveBody: RunGaRequestBody = body;
  let scenarioResult: ScenarioAdapterResult | null = null;

  if (body.scenarioPath) {
    sendEvent({
      stage: "Resolving scenario",
      message: `Deriving optimizer inputs from scenario: ${body.scenarioPath}`,
    });

    scenarioResult = await deriveOptimizerInputsFromScenario(
      {
        scenarioPath: body.scenarioPath,
        forceExistingOff: body.forceExistingOff,
        targetTotalFacilityCount: body.targetTotalFacilityCount,
      },
      runtimeConfig,
      childEnv
    );

    const scenarioSummary = buildScenarioSummary(scenarioResult);

    if (!scenarioResult.optimizerRunRequired || !scenarioResult.javaCliArgs) {
      sendEvent({
        stage: "Completed",
        message:
          "This scenario represents a current-network evaluation; no optimizer run was required.",
        success: true,
        scenario: scenarioSummary,
      });
      return;
    }

    // Scenario data is the source of truth here: active existing facilities
    // and locked candidates are folded into fixedFacilityIds, and
    // includeExistingLockers is explicitly forced off so Java never
    // re-derives existing facilities from existing_locker_count.
    effectiveBody = {
      ...body,
      k: scenarioResult.javaCliArgs.k,
      fixedFacilityIds: scenarioResult.effectiveFixedCandidateIds,
      includeExistingLockers: false,
    };

    sendEvent({
      stage: "Resolving scenario",
      message: "Scenario resolved to optimizer inputs.",
      scenario: scenarioSummary,
    });
  }

  await runJavaGa(effectiveBody, runtimeConfig, childEnv, sendEvent);

  if (scenarioResult) {
    await mergeScenarioMetadataIntoRunMetadata(runtimeConfig, scenarioResult);
  }

  sendEvent({ stage: "Generating plots", message: "Running plot_archives.py..." });
  console.log("Generating Plots...");
  const plotResult = await runPythonScript(runtimeConfig.plotScriptPath, [], {
    cwd: runtimeConfig.projectRoot,
    env: childEnv,
  });
  console.log("Plot Output:", plotResult.stdout);

  sendEvent({ stage: "Syncing UI assets", message: "Copying latest plot..." });
  try {
    await fs.mkdir(runtimeConfig.uiMockDir, { recursive: true });
    await fs.copyFile(runtimeConfig.outputLatestPlotPath, runtimeConfig.uiLatestPlotPath);
    console.log(`Updated UI plot: ${runtimeConfig.uiLatestPlotPath}`);
  } catch (copyError: unknown) {
    const message = copyError instanceof Error ? copyError.message : String(copyError);
    console.error("Failed to copy latest plot into UI public folder:", message);
  }

  sendEvent({ stage: "Processing GA output", message: "Running process_ga_data.py..." });
  console.log("Processing GA data for UI...");
  const processResult = await runPythonScript(runtimeConfig.processScriptPath, [], {
    cwd: runtimeConfig.uiRoot,
    env: childEnv,
  });
  console.log("Python Output:", processResult.stdout);

  const paretoInfo = processResult.stdout.split("\n").filter((line) => line.includes("Pareto")).pop();

  sendEvent({
    stage: "Completed",
    message: "Optimization completed successfully.",
    success: true,
    paretoInfo,
    ...(scenarioResult ? { scenario: buildScenarioSummary(scenarioResult) } : {}),
  });
}

export function getFailureEvent(
  error: unknown,
  runtimeConfig: RuntimeConfig
): StreamEvent {
  const errorInfo = getErrorInfo(error);

  let stage = "Failed";
  let errorMessage = errorInfo.message;
  let stderr = "";

  if (errorInfo.message.includes("Python command could not be resolved")) {
    stage = "Failed while detecting Python";
  } else if (errorInfo.scriptPath === runtimeConfig.scenarioAdapterScriptPath) {
    stage = "Failed while deriving scenario inputs";
    stderr = errorInfo.stderr || "";
    errorMessage = errorInfo.message;
  } else if (errorInfo.scriptPath === runtimeConfig.plotScriptPath) {
    stage = "Failed while generating plots";
    stderr = errorInfo.stderr || "";
    errorMessage = errorInfo.message;
  } else if (errorInfo.scriptPath === runtimeConfig.processScriptPath) {
    stage = "Failed while processing GA output";
    stderr = errorInfo.stderr || "";
    errorMessage = errorInfo.message;
  } else if (errorInfo.message.includes("Java GA process failed")) {
    stage = "Failed during Java GA execution";
  }

  return {
    stage,
    error: errorMessage,
    stderr,
  };
}

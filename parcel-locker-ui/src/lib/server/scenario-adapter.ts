import path from "path";
import { runPythonScript } from "@/lib/python-runner";
import type { RuntimeConfig } from "@/lib/server/runtime-config";

// Repository-relative directory that scenario paths must resolve inside.
// Keep in sync with runtime-config.ts's `scenariosDir`.
const SCENARIO_DIR_PREFIX = "data/scenarios/";

export type ScenarioJavaCliArgs = {
  k: number;
  fixedFacilityIds?: string;
};

export type ScenarioAdapterResult = {
  scenarioId: string | null;
  scenarioPath: string;
  runType: string | null;
  existingEnabled: boolean;
  facilityCountMode: string;
  optimizerRunRequired: boolean;
  targetNewFacilityCount: number | null;
  targetTotalFacilityCount: number | null;
  resolvedK: number | null;
  activeExistingCandidateIds: number[];
  lockedCandidateIds: number[];
  disabledCandidateIds: number[];
  effectiveFixedCandidateIds: number[];
  physicalFacilityCount: number;
  effectiveFacilityLocationCount: number;
  javaCliArgs: ScenarioJavaCliArgs | null;
  warnings: string[];
  metadata: Record<string, unknown>;
};

export type ScenarioRunOptions = {
  scenarioPath: string;
  forceExistingOff?: boolean;
  targetTotalFacilityCount?: number;
};

/**
 * Resolve a client-supplied scenario path to an absolute path, rejecting
 * anything that isn't a repository-relative path under `data/scenarios/`.
 *
 * This is the only allowed entry point for scenario file access from the
 * API route: it must never accept absolute paths or `..` segments, since
 * the request body is untrusted input.
 */
export function resolveScenarioPath(rawPath: string, runtimeConfig: RuntimeConfig): string {
  if (typeof rawPath !== "string" || !rawPath.trim()) {
    throw new Error("scenarioPath must be a non-empty string.");
  }

  const normalizedInput = rawPath.trim().replace(/\\/g, "/");

  if (path.win32.isAbsolute(normalizedInput) || path.posix.isAbsolute(normalizedInput)) {
    throw new Error("scenarioPath must be a repository-relative path, not absolute.");
  }
  if (normalizedInput.split("/").some((segment) => segment === "..")) {
    throw new Error("scenarioPath must not contain '..' segments.");
  }
  if (!normalizedInput.startsWith(SCENARIO_DIR_PREFIX)) {
    throw new Error(`scenarioPath must be under ${SCENARIO_DIR_PREFIX}.`);
  }

  const resolved = path.resolve(runtimeConfig.projectRoot, normalizedInput);
  const scenariosRoot = path.resolve(runtimeConfig.scenariosDir);
  if (resolved !== scenariosRoot && !resolved.startsWith(scenariosRoot + path.sep)) {
    throw new Error("scenarioPath resolves outside the allowed scenarios directory.");
  }

  return resolved;
}

/**
 * Invoke scripts/scenario/derive_optimizer_inputs.py and parse its JSON
 * stdout. Never passes `--includeExistingLockers`-equivalent behavior to
 * Java: active existing candidates come from scenario.facilities[] via
 * `effectiveFixedCandidateIds`/`javaCliArgs.fixedFacilityIds`, not from
 * `existing_locker_count`.
 */
export async function deriveOptimizerInputsFromScenario(
  options: ScenarioRunOptions,
  runtimeConfig: RuntimeConfig,
  childEnv: NodeJS.ProcessEnv
): Promise<ScenarioAdapterResult> {
  const absoluteScenarioPath = resolveScenarioPath(options.scenarioPath, runtimeConfig);

  const args = [
    "--scenario",
    absoluteScenarioPath,
    "--candidate-csv",
    runtimeConfig.candidateCsv,
  ];
  if (options.forceExistingOff) {
    args.push("--force-existing-off");
  }
  if (options.targetTotalFacilityCount !== undefined) {
    args.push("--override-target-total-facility-count", String(options.targetTotalFacilityCount));
  }

  const { stdout } = await runPythonScript(runtimeConfig.scenarioAdapterScriptPath, args, {
    cwd: runtimeConfig.projectRoot,
    env: childEnv,
  });

  try {
    return JSON.parse(stdout) as ScenarioAdapterResult;
  } catch (parseError: unknown) {
    const message = parseError instanceof Error ? parseError.message : String(parseError);
    throw new Error(`Scenario adapter produced invalid JSON output: ${message}`);
  }
}

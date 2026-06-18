import path from "path";

const DEFAULT_GA_MAX_RUNTIME_MS = 60 * 60 * 1000;

export type RuntimeConfig = {
  projectRoot: string;
  uiRoot: string;
  candidateCsv: string;
  distanceMatrix: string;
  outputDir: string;
  uiMockDir: string;
  plotScriptPath: string;
  processScriptPath: string;
  outputLatestPlotPath: string;
  uiLatestPlotPath: string;
  mavenCmd?: string;
  maxRuntimeMs: number;
};

function resolvePathFromProjectRoot(projectRoot: string, value: string): string {
  return path.isAbsolute(value) ? path.normalize(value) : path.resolve(projectRoot, value);
}

export function getRuntimeConfig(): RuntimeConfig {
  const inferredUiRoot = process.cwd();
  const projectRoot = process.env.PROJECT_ROOT
    ? path.resolve(process.env.PROJECT_ROOT)
    : path.resolve(inferredUiRoot, "..");
  const uiRoot = process.env.UI_ROOT
    ? path.resolve(process.env.UI_ROOT)
    : inferredUiRoot;
  const outputDir = resolvePathFromProjectRoot(projectRoot, process.env.GA_OUTPUT_DIR || "output");
  const uiMockDir = resolvePathFromProjectRoot(
    projectRoot,
    process.env.UI_MOCK_DIR || "parcel-locker-ui/public/mock"
  );
  const maxRuntimeMs = Number(process.env.GA_MAX_RUNTIME_MS || DEFAULT_GA_MAX_RUNTIME_MS);

  return {
    projectRoot,
    uiRoot,
    candidateCsv: resolvePathFromProjectRoot(
      projectRoot,
      process.env.GA_CANDIDATE_CSV || "data/candidate_points.csv"
    ),
    distanceMatrix: resolvePathFromProjectRoot(
      projectRoot,
      process.env.GA_DISTANCE_MATRIX || "data/kadikoy_distance_meters_nxn.npy"
    ),
    outputDir,
    uiMockDir,
    plotScriptPath: path.join(projectRoot, "scripts/plot_archives.py"),
    processScriptPath: path.join(uiRoot, "src/scripts/process_ga_data.py"),
    outputLatestPlotPath: path.join(outputDir, "archive_comparison_latest.png"),
    uiLatestPlotPath: path.join(uiMockDir, "archive_comparison_latest.png"),
    mavenCmd: process.env.MAVEN_CMD?.trim(),
    maxRuntimeMs: Number.isFinite(maxRuntimeMs) && maxRuntimeMs > 0
      ? maxRuntimeMs
      : DEFAULT_GA_MAX_RUNTIME_MS,
  };
}

export function buildChildEnv(runtimeConfig: RuntimeConfig): NodeJS.ProcessEnv {
  return {
    ...process.env,
    PROJECT_ROOT: runtimeConfig.projectRoot,
    UI_ROOT: runtimeConfig.uiRoot,
    GA_CANDIDATE_CSV: runtimeConfig.candidateCsv,
    GA_DISTANCE_MATRIX: runtimeConfig.distanceMatrix,
    GA_OUTPUT_DIR: runtimeConfig.outputDir,
    UI_MOCK_DIR: runtimeConfig.uiMockDir,
  };
}

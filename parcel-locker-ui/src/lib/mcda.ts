import type { ArchiveSolution } from "@/lib/types";

type ObjectiveRawKey = "accessibility" | "equity";
type ObjectiveNormKey = "norm_f1" | "norm_f2";

export type McdaSelectionResult =
  | {
      status: "selected";
      selectedIndex: number;
      selectedSolution: ArchiveSolution;
      accessibilityWeight: number;
      inequityWeight: number;
    }
  | {
      status: "no-pareto";
      accessibilityWeight: number;
      inequityWeight: number;
    }
  | {
      status: "missing-selected";
      accessibilityWeight: number;
      inequityWeight: number;
    }
  | {
      status: "missing-index";
      accessibilityWeight: number;
      inequityWeight: number;
    };

export function getMcdaWeights(preference: number): {
  accessibilityWeight: number;
  inequityWeight: number;
} {
  return {
    accessibilityWeight: (100 - preference) / 100,
    inequityWeight: preference / 100,
  };
}

function getNormalizedObjectiveCosts(
  solutions: ArchiveSolution[],
  rawKey: ObjectiveRawKey,
  normKey: ObjectiveNormKey
): number[] {
  if (!solutions.length) return [];

  const normalizedValues = solutions.map((solution) => solution.metrics[normKey]);
  if (normalizedValues.every((value) => Number.isFinite(value))) {
    return normalizedValues as number[];
  }

  const rawValues = solutions.map((solution) => solution.metrics[rawKey]);
  const min = Math.min(...rawValues);
  const max = Math.max(...rawValues);
  if (max === min) return solutions.map(() => 0);

  return rawValues.map((value) => (value - min) / (max - min));
}

export function selectMcdaSolution(
  archiveSolutions: ArchiveSolution[],
  preference: number
): McdaSelectionResult {
  const { accessibilityWeight, inequityWeight } = getMcdaWeights(preference);
  const paretoSolutions = archiveSolutions.filter((solution) => solution.isPareto);

  if (!paretoSolutions.length) {
    return { status: "no-pareto", accessibilityWeight, inequityWeight };
  }

  const accessibilityCosts = getNormalizedObjectiveCosts(
    paretoSolutions,
    "accessibility",
    "norm_f1"
  );
  const inequityCosts = getNormalizedObjectiveCosts(paretoSolutions, "equity", "norm_f2");

  let bestParetoIndex = 0;
  let bestScore = Number.POSITIVE_INFINITY;

  paretoSolutions.forEach((_solution, index) => {
    const score =
      accessibilityWeight * accessibilityCosts[index] +
      inequityWeight * inequityCosts[index];

    if (score < bestScore) {
      bestScore = score;
      bestParetoIndex = index;
    }
  });

  const selectedSolution = paretoSolutions[bestParetoIndex];

  if (!selectedSolution) {
    return { status: "missing-selected", accessibilityWeight, inequityWeight };
  }

  const selectedIndex = archiveSolutions.findIndex(
    (solution) => solution.id === selectedSolution.id
  );

  if (selectedIndex === -1) {
    return { status: "missing-index", accessibilityWeight, inequityWeight };
  }

  return {
    status: "selected",
    selectedIndex,
    selectedSolution,
    accessibilityWeight,
    inequityWeight,
  };
}

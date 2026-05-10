import type { ArchiveSolution, Locker } from "@/lib/types";

export function getOptimalParams(k: number): {
  popSize: number;
  maxGenerations: number;
  mutationRate: number;
  crossoverRate: number;
  archiveSize: number;
} {
  if (k <= 4) return { popSize: 200, maxGenerations: 200, mutationRate: 0.4, crossoverRate: 0.9, archiveSize: 100 };
  if (k <= 7) return { popSize: 100, maxGenerations: 500, mutationRate: 0.4, crossoverRate: 0.9, archiveSize: 50 };
  if (k <= 12) return { popSize: 50, maxGenerations: 1600, mutationRate: 0.3, crossoverRate: 0.9, archiveSize: 25 };
  if (k <= 20) return { popSize: 50, maxGenerations: 3000, mutationRate: 0.3, crossoverRate: 0.9, archiveSize: 25 };
  return { popSize: 50, maxGenerations: 5000, mutationRate: 0.3, crossoverRate: 0.9, archiveSize: 25 };
}

export function getCurrentSolution(
  archiveSolutions: ArchiveSolution[],
  currentSolutionIndex: number
): ArchiveSolution | null {
  return currentSolutionIndex >= 0 && currentSolutionIndex < archiveSolutions.length
    ? archiveSolutions[currentSolutionIndex]
    : null;
}

export function getParetoSolutionCount(archiveSolutions: ArchiveSolution[]): number {
  return archiveSolutions.filter((solution) => solution.isPareto).length;
}

export function findSolutionIndex(archiveSolutions: ArchiveSolution[], solutionId: number): number {
  return archiveSolutions.findIndex((solution) => solution.id === solutionId);
}

export function solutionToUiLockers(solution: ArchiveSolution | null): Locker[] {
  if (!solution?.lockers?.length) return [];

  return solution.lockers.map((locker, index) => ({
    id: locker.id,
    name: `Locker ${String(index + 1).padStart(2, "0")}`,
    lat: locker.lat,
    lng: locker.lng,
    neighborhood: locker.neighborhood,
    score: locker.score,
    source: locker.source,
  }));
}

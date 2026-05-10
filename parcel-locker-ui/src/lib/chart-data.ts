import type { ArchiveSolution } from "@/lib/types";

export interface ChartPoint {
  id: number;
  x: number;
  y: number;
  isPareto?: boolean;
  isBestF1?: boolean;
  isBestF2?: boolean;
  isSelected: boolean;
  size: number;
}

export function buildParetoChartData(
  archiveSolutions: ArchiveSolution[],
  currentSolution: ArchiveSolution | null
): ChartPoint[] {
  return archiveSolutions.map((sol) => ({
    id: sol.id,
    x: sol.metrics.accessibility,
    y: sol.metrics.equity,
    isPareto: sol.isPareto,
    isBestF1: sol.isBestF1,
    isBestF2: sol.isBestF2,
    isSelected: sol.id === currentSolution?.id,
    size: sol.id === currentSolution?.id ? 300 : 100,
  }));
}

export function buildParetoLineData(chartData: ChartPoint[]): ChartPoint[] {
  return chartData
    .filter((point) => point.isPareto)
    .sort((a, b) => a.x - b.x);
}

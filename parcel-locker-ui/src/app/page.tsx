"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { ControlPanel } from "@/components/dashboard/control-panel";
import { LockerDetailPanel } from "@/components/dashboard/locker-detail-panel";
import { LockerStrip } from "@/components/dashboard/locker-strip";
import type { CandidatePoint, ArchiveSolution, Locker } from "@/lib/types";
import { Maximize2, Minimize2 } from "lucide-react";
import {
  ScatterChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Cell
} from 'recharts';

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return m > 0 ? `${m}m ${String(s).padStart(2, '0')}s` : `${s}s`;
}

function formatMetric(value: number | undefined, digits = 3): string {
  return Number.isFinite(value) ? value!.toFixed(digits) : "N/A";
}

const getOptimalParams = (k: number) => {
  if (k <= 4) return { popSize: 200, maxGenerations: 200, mutationRate: 0.4, crossoverRate: 0.9, archiveSize: 100 };
  if (k <= 7) return { popSize: 100, maxGenerations: 500, mutationRate: 0.4, crossoverRate: 0.9, archiveSize: 50 };
  if (k <= 12) return { popSize: 50, maxGenerations: 1600, mutationRate: 0.3, crossoverRate: 0.9, archiveSize: 25 };
  if (k <= 20) return { popSize: 50, maxGenerations: 3000, mutationRate: 0.3, crossoverRate: 0.9, archiveSize: 25 };
  return { popSize: 50, maxGenerations: 5000, mutationRate: 0.3, crossoverRate: 0.9, archiveSize: 25 };
};

const LockerMap = dynamic(
  () => import("@/components/dashboard/locker-map").then((mod) => mod.LockerMap),
  { ssr: false }
);

function solutionToUiLockers(solution: ArchiveSolution | null): Locker[] {
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

interface ChartPoint {
  id: number;
  x: number;
  y: number;
  isPareto?: boolean;
  isBestF1?: boolean;
  isBestF2?: boolean;
  isSelected: boolean;
  size: number;
}

function getNormalizedObjectiveCosts(
  solutions: ArchiveSolution[],
  rawKey: "accessibility" | "equity",
  normKey: "norm_f1" | "norm_f2"
) {
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

export default function HomePage() {
  const [inputLockerCount, setInputLockerCount] = useState(5);
  const [populationSize, setPopulationSize] = useState(100);
  const [maxGenerations, setMaxGenerations] = useState(200);

  const [mutationRate, setMutationRate] = useState(0.1);
  const [crossoverRate, setCrossoverRate] = useState(0.9);

  const [archiveSize, setArchiveSize] = useState(50);
  const [randomSeed, setRandomSeed] = useState("");

  const [, setActiveLockerCount] = useState(5);

  const [candidates, setCandidates] = useState<CandidatePoint[]>([]);
  const [boundary, setBoundary] = useState<GeoJSON.FeatureCollection | null>(null);

  const [archiveSolutions, setArchiveSolutions] = useState<ArchiveSolution[]>([]);
  const [currentSolutionIndex, setCurrentSolutionIndex] = useState(0);
  const [mcdaPreference, setMcdaPreference] = useState<number>(50);

  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(700);

  const [selectedLocker, setSelectedLocker] = useState<Locker | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info', text: string } | null>(null);
  const [isPlotModalOpen, setIsPlotModalOpen] = useState(false);
  const [plotTimestamp, setPlotTimestamp] = useState(0);

  const [optimizationStage, setOptimizationStage] = useState("Starting");
  const [optimizationGeneration, setOptimizationGeneration] = useState(0);
  const [optimizationMaxGenerations, setOptimizationMaxGenerations] = useState(0);
  const [optimizationProgress, setOptimizationProgress] = useState(0);
  const [optimizationLogs, setOptimizationLogs] = useState<string[]>([]);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [chartSize, setChartSize] = useState({ width: 0, height: 0 });

  // Focus mode
  const [isFocusMode, setIsFocusMode] = useState(false);

  // Time tracking
  const [elapsedMs, setElapsedMs] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  const handleLockerCountChange = (value: number) => {
    setInputLockerCount(value);
    const params = getOptimalParams(value);
    setPopulationSize(params.popSize);
    setMaxGenerations(params.maxGenerations);
    setMutationRate(params.mutationRate);
    setCrossoverRate(params.crossoverRate);
    setArchiveSize(params.archiveSize);
  };

  const loadData = async () => {
    try {
      const [candidateResponse, boundaryResponse] = await Promise.all([
        fetch("/mock/candidate-points.json"),
        fetch("/mock/kadikoy_boundary.geojson"),
      ]);

      if (!candidateResponse.ok) throw new Error("Candidate fetch failed");
      if (!boundaryResponse.ok) throw new Error("Boundary fetch failed");

      const candidateData: CandidatePoint[] = await candidateResponse.json();
      const boundaryData = (await boundaryResponse.json()) as GeoJSON.FeatureCollection;

      let archiveData: ArchiveSolution[] = [];
      const archiveResponse = await fetch("/mock/ga-results.json");
      if (archiveResponse.ok) {
        archiveData = await archiveResponse.json();
      } else {
        console.warn("Archive results not found. Run optimization to generate ga-results.json.");
      }

      setCandidates(candidateData);
      setBoundary(boundaryData);
      setArchiveSolutions(archiveData);
    } catch (error) {
      console.error("Failed to load data:", error);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    const element = chartContainerRef.current;
    if (!element || typeof ResizeObserver === "undefined") return;

    const updateSize = (width: number, height: number) => {
      setChartSize({
        width: Math.max(0, Math.floor(width)),
        height: Math.max(0, Math.floor(height)),
      });
    };

    const rect = element.getBoundingClientRect();
    updateSize(rect.width, rect.height);

    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      updateSize(entry.contentRect.width, entry.contentRect.height);
    });

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!isPlaying || archiveSolutions.length <= 1) return;

    const timer = window.setInterval(() => {
      setCurrentSolutionIndex((prev) => {
        if (prev >= archiveSolutions.length - 1) return 0;
        return prev + 1;
      });
    }, playbackSpeed);

    return () => window.clearInterval(timer);
  }, [isPlaying, playbackSpeed, archiveSolutions.length]);

  const currentSolution =
    currentSolutionIndex >= 0 && currentSolutionIndex < archiveSolutions.length
      ? archiveSolutions[currentSolutionIndex]
      : null;
  const paretoSolutionCount = useMemo(
    () => archiveSolutions.filter((solution) => solution.isPareto).length,
    [archiveSolutions]
  );

  const chartData = useMemo<ChartPoint[]>(() => {
    return archiveSolutions.map((sol) => ({
      id: sol.id,
      x: sol.metrics.accessibility,
      y: sol.metrics.equity,
      isPareto: sol.isPareto,
      isBestF1: sol.isBestF1,
      isBestF2: sol.isBestF2,
      isSelected: sol.id === currentSolution?.id,
      size: sol.id === currentSolution?.id ? 300 : 100
    }));
  }, [archiveSolutions, currentSolution]);

  const paretoLineData = useMemo(() => {
    return chartData
      .filter(p => p.isPareto)
      .sort((a, b) => a.x - b.x);
  }, [chartData]);

  const lockersForDisplay = useMemo(
    () => solutionToUiLockers(currentSolution),
    [currentSolution]
  );

  useEffect(() => {
    if (!lockersForDisplay.length) {
      setSelectedLocker(null);
      return;
    }

    setSelectedLocker((prev) => {
      if (!prev) return null;
      return lockersForDisplay.find((locker) => locker.id === prev.id) ?? null;
    });
  }, [lockersForDisplay]);

  const handleShowResults = async () => {
    const clamped = Math.max(1, Math.min(inputLockerCount, 20));
    setInputLockerCount(clamped);
    setIsOptimizing(true);
    setStatusMessage(null);
    setOptimizationStage("Starting");
    setOptimizationGeneration(0);
    setOptimizationProgress(0);
    setOptimizationLogs([]);
    setElapsedMs(0);
    startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setElapsedMs(Date.now() - startTimeRef.current);
    }, 1000);

    try {
      const response = await fetch("/api/run-ga", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          k: clamped,
          populationSize,
          maxGenerations,
          mutationRate,
          crossoverRate,
          archiveSize,
          randomSeed: randomSeed ? parseInt(randomSeed, 10) : null
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to start optimization stream");
      }

      if (!response.body) {
        throw new Error("No response body");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          if (part.startsWith('data: ')) {
            try {
              const data = JSON.parse(part.slice(6));

              if (data.stage) setOptimizationStage(data.stage);
              if (data.currentGeneration !== undefined) setOptimizationGeneration(data.currentGeneration);
              if (data.maxGenerations !== undefined) setOptimizationMaxGenerations(data.maxGenerations);
              if (data.progressPercent !== undefined) setOptimizationProgress(data.progressPercent);

              if (data.log || data.message) {
                setOptimizationLogs(prev => [...prev, data.log || data.message].slice(-5));
              }

              if (data.error) {
                throw new Error(data.error + (data.stderr ? `\n\n${data.stderr}` : ''));
              }

              if (data.success) {
                break;
              }
            } catch (e) {
              if (e instanceof Error && e.message !== 'Unexpected end of JSON input') {
                throw e;
              }
            }
          }
        }
      }

      await loadData();
      setPlotTimestamp(Date.now());

      setActiveLockerCount(clamped);
      setCurrentSolutionIndex(0);
      setIsPlaying(false);
      setSelectedLocker(null);

      setStatusMessage({ type: 'success', text: `Optimization completed for k=${clamped}!` });
      setTimeout(() => setStatusMessage(null), 5000);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      console.error("Optimization error:", message);
      setStatusMessage({ type: 'error', text: `Error: ${message}` });
    } finally {
      setIsOptimizing(false);
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    }
  };

  const handleNextSolution = () => {
    setCurrentSolutionIndex((prev) =>
      prev >= archiveSolutions.length - 1 ? archiveSolutions.length - 1 : prev + 1
    );
  };

  const handlePrevSolution = () => {
    setCurrentSolutionIndex((prev) => (prev <= 0 ? 0 : prev - 1));
  };

  const handleRunMcda = () => {
    const paretoSolutions = archiveSolutions.filter((solution) => solution.isPareto);

    if (!paretoSolutions.length) {
      setStatusMessage({
        type: "info",
        text: "No Pareto solutions are available yet. Run optimization before using MCDA.",
      });
      return;
    }

    const accessibilityWeight = (100 - mcdaPreference) / 100;
    const inequityWeight = mcdaPreference / 100;
    const accessibilityCosts = getNormalizedObjectiveCosts(
      paretoSolutions,
      "accessibility",
      "norm_f1"
    );
    const inequityCosts = getNormalizedObjectiveCosts(paretoSolutions, "equity", "norm_f2");

    let bestParetoIndex = 0;
    let bestScore = Number.POSITIVE_INFINITY;

    paretoSolutions.forEach((solution, index) => {
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
      setStatusMessage({
        type: "error",
        text: "MCDA could not select a Pareto solution from the available archive.",
      });
      return;
    }

    const selectedIndex = archiveSolutions.findIndex((solution) => solution.id === selectedSolution.id);

    if (selectedIndex === -1) {
      setStatusMessage({
        type: "error",
        text: "MCDA selected a Pareto solution, but it could not be matched to the archive.",
      });
      return;
    }

    setCurrentSolutionIndex(selectedIndex);
    setIsPlaying(false);
    setStatusMessage({
      type: "success",
      text: `MCDA selected solution #${selectedIndex + 1} with Accessibility ${Math.round(
        accessibilityWeight * 100
      )}% / Inequity ${Math.round(inequityWeight * 100)}%.`,
    });
    setTimeout(() => setStatusMessage(null), 5000);
  };

  const selectedSolutionLabel = currentSolution ? `#${currentSolutionIndex + 1}` : "N/A";
  const currentSolutionType = currentSolution?.isBestF1
    ? "Best accessibility"
    : currentSolution?.isBestF2
      ? "Best inequity"
      : currentSolution?.isPareto
        ? "Pareto solution"
        : "Archive solution";
  const isChartReady = chartSize.width > 80 && chartSize.height > 80;
  const statusClassName = statusMessage
    ? statusMessage.type === 'success'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : statusMessage.type === 'error'
        ? 'border-rose-200 bg-rose-50 text-rose-700'
        : 'border-blue-200 bg-blue-50 text-blue-700'
    : "";

  return (
    <main className="relative min-h-screen bg-slate-50 px-4 py-4 text-slate-900 sm:px-5 lg:px-6">

      <div className="relative mx-auto flex max-w-[1500px] flex-col gap-4">
        <header className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm sm:px-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <span className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Optimization-Based
              </span>
              <h1 className="mt-2 max-w-4xl text-2xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-3xl">
                Recommendation System for Parcel Locker Locations
              </h1>
              <p className="mt-1 max-w-3xl text-sm leading-5 text-slate-600">
                Multi-objective GA for Kadikoy placement scenarios with Pareto metrics, archive coverage, and map diagnostics.
              </p>
            </div>

            {statusMessage ? (
              <div className={`w-full rounded-lg border px-4 py-3 text-sm font-medium shadow-sm lg:max-w-lg ${statusClassName}`}>
                <div className="flex items-center gap-3">
                  {statusMessage.type === 'success' && <span className="text-lg">✓</span>}
                  {statusMessage.type === 'error' && <span className="text-lg">⚠</span>}
                  {statusMessage.type === 'info' && <span className="text-lg">ℹ</span>}
                  <p>{statusMessage.text}</p>
                </div>
              </div>
            ) : (
              <div className="grid w-full grid-cols-3 gap-2 lg:max-w-md">
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Solutions</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums text-slate-950">{archiveSolutions.length}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Pareto</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums text-emerald-700">{paretoSolutionCount}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Selected</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums text-slate-950">{selectedSolutionLabel}</p>
                </div>
              </div>
            )}
          </div>
        </header>

        <section className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Current Solution</p>
              <div className="mt-2 flex items-end justify-between gap-3">
                <p className="text-2xl font-semibold tabular-nums text-slate-950">{selectedSolutionLabel}</p>
                <span className="rounded-md bg-white px-2 py-1 text-[10px] font-semibold text-slate-500 shadow-sm">
                  {currentSolutionType}
                </span>
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Archive Coverage</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-950">{archiveSolutions.length}</p>
              <p className="mt-1 text-xs text-slate-500">{paretoSolutionCount} Pareto candidates</p>
            </div>
            <div className="rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-blue-500">Accessibility</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-blue-800">
                {formatMetric(currentSolution?.metrics.accessibility, 4)}
              </p>
              <p className="mt-1 text-xs text-blue-700/70">Objective f1</p>
            </div>
            <div className="rounded-lg border border-emerald-100 bg-emerald-50/70 px-4 py-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600">Inequity</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-emerald-800">
                {formatMetric(currentSolution?.metrics.equity, 4)}
              </p>
              <p className="mt-1 text-xs text-emerald-700/70">Objective f2</p>
            </div>
          </div>

          <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50/70 p-2.5 sm:p-3">
            <LockerStrip
              lockers={lockersForDisplay}
              selectedLockerId={selectedLocker?.id ?? ""}
              onSelectLocker={setSelectedLocker}
              isPareto={currentSolution?.isPareto}
            />
          </div>

          <div className="mt-4 grid grid-cols-12 gap-4 transition-all duration-500 lg:min-h-[500px]">
            <div className={`col-span-12 transition-all duration-500 lg:h-[calc(100vh-300px)] lg:min-h-[500px] ${isFocusMode ? 'hidden' : 'lg:col-span-3'}`}>
              <ControlPanel
                lockerCount={inputLockerCount}
                onLockerCountChange={handleLockerCountChange}
                populationSize={populationSize}
                onPopulationSizeChange={setPopulationSize}
                maxGenerations={maxGenerations}
                onMaxGenerationsChange={setMaxGenerations}
                mutationRate={mutationRate}
                onMutationRateChange={setMutationRate}
                crossoverRate={crossoverRate}
                onCrossoverRateChange={setCrossoverRate}
                archiveSize={archiveSize}
                onArchiveSizeChange={setArchiveSize}
                randomSeed={randomSeed}
                onRandomSeedChange={setRandomSeed}
                onShowResults={handleShowResults}
                currentGeneration={currentSolutionIndex}
                generationCount={archiveSolutions.length}
                isPlaying={isPlaying}
                playbackSpeed={playbackSpeed}
                onTogglePlayback={() => setIsPlaying((prev) => !prev)}
                onPrevGeneration={handlePrevSolution}
                onNextGeneration={handleNextSolution}
                onGenerationChange={(value) => {
                  const maxIndex = Math.max(0, archiveSolutions.length - 1);
                  setCurrentSolutionIndex(Math.max(0, Math.min(value, maxIndex)));
                }}
                onPlaybackSpeedChange={setPlaybackSpeed}
                mcdaPreference={mcdaPreference}
                onMcdaPreferenceChange={(value) => {
                  setMcdaPreference(Number.isFinite(value) ? value : 50);
                }}
                onRunMcda={handleRunMcda}
                paretoSolutionCount={paretoSolutionCount}
                isOptimizing={isOptimizing}
                isCurrentSolutionPareto={currentSolution?.isPareto}
                isBestF1={currentSolution?.isBestF1}
                isBestF2={currentSolution?.isBestF2}
              />
            </div>

            <div className={`col-span-12 min-h-[350px] relative transition-all duration-500 lg:h-[calc(100vh-300px)] lg:min-h-[500px] ${isFocusMode ? 'lg:col-span-7' : 'lg:col-span-6'}`}>
              {isOptimizing && (
                <div className="absolute inset-0 z-[60] flex items-center justify-center rounded-2xl bg-white/60 p-6 backdrop-blur-sm animate-in fade-in duration-300">
                  <div className="w-full max-w-md rounded-2xl border border-white/60 bg-white/80 p-6 shadow-2xl backdrop-blur-xl">
                    <h3 className="text-lg font-bold text-slate-900 mb-2">Optimization Progress</h3>
                    <p className="text-xs font-semibold uppercase tracking-widest text-indigo-600 mb-6">{optimizationStage}</p>

                    {optimizationMaxGenerations > 0 && (
                      <div className="mb-4">
                        <div className="flex justify-between text-xs font-bold text-slate-500 mb-2">
                          <span>Generation {optimizationGeneration} / {optimizationMaxGenerations}</span>
                          <span>{optimizationProgress}%</span>
                        </div>
                        <div className="h-2.5 w-full rounded-full bg-slate-200 overflow-hidden">
                          <div
                            className="h-full bg-indigo-500 transition-all duration-300 rounded-full"
                            style={{ width: `${optimizationProgress}%` }}
                          />
                        </div>
                        <div className="mt-2 flex justify-between text-[10px] text-slate-400 font-medium">
                          <span>Elapsed: {formatDuration(elapsedMs)}</span>
                          {optimizationProgress > 5 && (
                            <span>Est. remaining: ~{formatDuration((elapsedMs / optimizationProgress) * (100 - optimizationProgress))}</span>
                          )}
                        </div>
                      </div>
                    )}

                    <div className="rounded-xl bg-slate-900 p-3 text-[10px] font-mono text-emerald-400 h-24 overflow-hidden flex flex-col justify-end shadow-inner">
                      {optimizationLogs.map((log, i) => (
                        <div key={i} className="truncate">{log}</div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {currentSolution ? (
                <LockerMap
                  candidates={candidates}
                  boundary={boundary}
                  lockers={lockersForDisplay}
                  selectedLocker={selectedLocker}
                  onSelectLocker={setSelectedLocker}
                  currentGeneration={currentSolution}
                />
              ) : (
                <div className="flex h-full min-h-[420px] items-center justify-center rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                  <p className="text-sm text-slate-500">Loading solution data...</p>
                </div>
              )}
            </div>

            <div className={`col-span-12 transition-all duration-500 lg:h-[calc(100vh-300px)] lg:min-h-[500px] ${isFocusMode ? 'lg:col-span-5' : 'lg:col-span-3'}`}>
              {selectedLocker && currentSolution ? (
                <LockerDetailPanel
                  locker={selectedLocker}
                  solution={currentSolution}
                  onClose={() => setSelectedLocker(null)}
                />
              ) : (
                <div className="flex flex-col h-full gap-4 overflow-hidden">
                  <div className={`flex min-h-[245px] flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${isFocusMode ? 'h-full' : ''}`}>
                    <div className="w-full h-full flex flex-col">
                      <div className="flex items-start justify-between mb-2 gap-1">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 shrink-0 leading-5">Pareto Front</span>
                        <div className="flex flex-wrap items-center justify-end gap-x-2 gap-y-1">
                          <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-indigo-400 border-t border-dashed border-indigo-400"></div><span className="text-[9px] text-slate-500">Pareto</span></div>
                          <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-blue-500"></div><span className="text-[9px] text-slate-500">Accessibility</span></div>
                          <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-emerald-600"></div><span className="text-[9px] text-slate-500">Inequity</span></div>
                          <button
                            onClick={() => setIsFocusMode(prev => !prev)}
                            className="hidden lg:flex h-6 w-6 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:bg-slate-50 hover:text-indigo-600 hover:border-indigo-300"
                            aria-label={isFocusMode ? 'Exit focus mode' : 'Enter focus mode'}
                            title={isFocusMode ? 'Exit Focus Mode' : 'Focus Mode'}
                          >
                            {isFocusMode ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
                          </button>
                        </div>
                      </div>
                      <div ref={chartContainerRef} className="min-h-[210px] min-w-0 flex-1">
                        {chartData.length > 0 && isChartReady ? (
                          <ScatterChart
                            width={chartSize.width}
                            height={chartSize.height}
                            margin={{ top: 10, right: 20, bottom: 20, left: -10 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                            <XAxis
                              type="number"
                              dataKey="x"
                              name="Accessibility"
                              unit=""
                              fontSize={10}
                              domain={['auto', 'auto']}
                              tickCount={5}
                              label={{ value: 'Accessibility', position: 'insideBottom', offset: -10, fontSize: 10 }}
                            />
                            <YAxis
                              type="number"
                              dataKey="y"
                              name="Inequity"
                              unit=""
                              fontSize={10}
                              domain={['auto', 'auto']}
                              tickCount={5}
                              label={{ value: 'Inequity', angle: -90, position: 'insideLeft', offset: 10, fontSize: 10 }}
                            />
                            <ZAxis type="number" dataKey="size" range={[50, 400]} />
                            <Tooltip
                              cursor={{ strokeDasharray: '3 3' }}
                              content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                  const data = payload[0].payload as ChartPoint;
                                  return (
                                    <div className="rounded-lg border border-slate-200 bg-white p-2 shadow-md text-[10px]">
                                      <div className="flex items-center justify-between gap-4 mb-1">
                                        <p className="font-bold">Solution #{data.id + 1}</p>
                                        {data.isSelected && <span className="text-[8px] bg-slate-900 text-white px-1 rounded">SELECTED</span>}
                                      </div>
                                      <p>Accessibility: {data.x.toFixed(4)}</p>
                                      <p>Inequity: {data.y.toFixed(4)}</p>
                                      {data.isBestF1 && <p className="text-blue-500 font-bold">Best Accessibility</p>}
                                      {data.isBestF2 && <p className="text-emerald-600 font-bold">Best Inequity</p>}
                                      {data.isPareto && <p className="text-emerald-500">Pareto Optimal</p>}
                                    </div>
                                  );
                                }
                                return null;
                              }}
                            />
                            <Line
                              type="monotone"
                              data={paretoLineData}
                              dataKey="y"
                              stroke="#818cf8"
                              strokeDasharray="5 5"
                              dot={false}
                              activeDot={false}
                              legendType="none"
                              connectNulls
                            />
                            <Scatter
                              name="Solutions"
                              data={chartData}
                              onClick={(data: unknown) => {
                                const id = (data as Partial<ChartPoint> | null)?.id;
                                if (typeof id !== "number") return;
                                const index = archiveSolutions.findIndex(s => s.id === id);
                                if (index !== -1) setCurrentSolutionIndex(index);
                              }}
                            >
                              {chartData.map((entry, index) => {
                                let fill = "#94a3b8"; // Default gray
                                let stroke = "none";
                                let strokeWidth = 0;

                                if (entry.isSelected) {
                                  stroke = "#0f172a";
                                  strokeWidth = 3;
                                }

                                if (entry.isBestF1) fill = "#3b82f6"; // Blue
                                else if (entry.isBestF2) fill = "#059669"; // Emerald
                                else if (entry.isPareto) fill = "#10b981"; // Light Emerald

                                return (
                                  <Cell
                                    key={`cell-${index}`}
                                    fill={fill}
                                    stroke={stroke}
                                    strokeWidth={strokeWidth}
                                    className={`cursor-pointer transition-all duration-200 hover:opacity-80 ${entry.isSelected ? 'animate-pulse' : ''}`}
                                  />
                                );
                              })}
                            </Scatter>
                          </ScatterChart>
                        ) : (
                          <div className="flex h-full min-h-[180px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 text-center text-xs text-slate-500">
                            {chartData.length > 0 ? "Preparing chart..." : "Run optimization to generate archive results."}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  {!isFocusMode && (
                    <div className="flex min-h-[210px] flex-1 flex-col items-center justify-center overflow-hidden rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
                      <div className="w-full h-full flex flex-col p-2">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Static Analysis Plot</span>
                          <span className="text-[9px] text-indigo-600 font-semibold bg-indigo-50 px-1.5 py-0.5 rounded animate-pulse">Click to expand</span>
                        </div>
                        <div
                          className="flex-1 relative rounded-xl overflow-hidden border border-slate-200/60 bg-white cursor-zoom-in group"
                          onClick={() => setIsPlotModalOpen(true)}
                        >
                          <img
                            src={`/mock/archive_comparison_latest.png?t=${plotTimestamp}`}
                            alt="GA Analysis"
                            className="absolute inset-0 w-full h-full object-contain transition-transform duration-300 group-hover:scale-105"
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                          <div className="absolute inset-0 bg-slate-900/0 group-hover:bg-slate-900/5 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                            <span className="bg-white/90 px-3 py-1.5 rounded-full text-[10px] font-bold shadow-lg">VIEW FULLSCREEN</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>

        <footer className="mt-4 rounded-2xl border border-white/60 bg-white/55 px-6 py-4 shadow-[0_6px_20px_rgba(15,23,42,0.04)] backdrop-blur-xl">
          <div className="flex flex-col items-center justify-between gap-2 sm:flex-row">
            <p className="text-[11px] font-medium text-slate-400">
              © {new Date().getFullYear()} Parcel Locker Optimization — Capstone Project
            </p>
            <div className="flex items-center gap-4">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-300">Multi-Objective GA</span>
              <span className="h-3 w-px bg-slate-200" />
              <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-300">Kadıköy, Istanbul</span>
            </div>
          </div>
        </footer>
      </div>

      {/* Fullscreen Image Modal */}
      {isPlotModalOpen && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-900/90 backdrop-blur-md p-4 sm:p-8 animate-in fade-in duration-300"
          onClick={() => setIsPlotModalOpen(false)}
        >
          <div className="relative w-full h-full max-w-7xl flex flex-col items-center justify-center">
            <button
              className="absolute -top-4 -right-4 sm:top-0 sm:right-0 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white text-slate-900 shadow-xl transition hover:bg-slate-100 hover:scale-110"
              onClick={(e) => {
                e.stopPropagation();
                setIsPlotModalOpen(false);
              }}
            >
              <span className="text-xl font-bold">✕</span>
            </button>
            <div
              className="w-full h-full rounded-2xl overflow-hidden border border-white/20 shadow-2xl bg-white"
              onClick={(e) => e.stopPropagation()}
            >
              <img
                src={`/mock/archive_comparison_latest.png?t=${plotTimestamp}`}
                alt="GA Analysis Fullscreen"
                className="w-full h-full object-contain"
              />
            </div>
            <div className="mt-4 text-center">
              <p className="text-white/70 text-sm font-medium">Static Analysis Plot - Full View</p>
              <p className="text-white/40 text-xs mt-1">Click anywhere outside or use the close button to return</p>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

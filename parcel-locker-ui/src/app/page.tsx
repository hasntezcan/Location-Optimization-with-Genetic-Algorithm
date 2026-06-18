"use client";

/* eslint-disable @next/next/no-img-element */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DashboardModeSwitch,
  type DashboardMode,
} from "@/components/dashboard/dashboard-mode-switch";
import { DevDashboard } from "@/components/dashboard/dev-dashboard";
import { UserDashboard } from "@/components/dashboard/user-dashboard";
import type { CandidatePoint, ArchiveSolution, Locker } from "@/lib/types";
import { runGaOptimization } from "@/lib/ga-api";
import { selectMcdaSolution } from "@/lib/mcda";
import {
  getCurrentSolution,
  getOptimalParams,
  MIN_MAX_GENERATIONS,
  getParetoSolutionCount,
  solutionToUiLockers,
} from "@/lib/solution-utils";
import {
  buildParetoChartData,
  buildParetoLineData,
  type ChartPoint,
} from "@/lib/chart-data";

function localizeGaStreamText(text: string): string {
  const trimmed = text.trim();
  const progressMatch = trimmed.match(/^\[Gen (\d+)\/(\d+)\] Optimizing(?:…|\.\.\.) (\d+)%$/);

  if (progressMatch) {
    return `[Adım ${progressMatch[1]}/${progressMatch[2]}] Öneriler hesaplanıyor... ${progressMatch[3]}%`;
  }

  const translations: Record<string, string> = {
    Starting: "Başlatılıyor",
    "Starting optimization": "Öneri oluşturma başlatılıyor",
    "Running Java GA": "Konum alternatifleri hesaplanıyor",
    "Generating plots": "Özet görseller hazırlanıyor",
    "Syncing UI assets": "Özet görseller güncelleniyor",
    "Processing GA output": "Öneri sonuçları hazırlanıyor",
    Completed: "Tamamlandı",
    Failed: "Başarısız oldu",
    "Failed while detecting Python": "Çalıştırma ortamı hazırlanırken hata oluştu",
    "Failed while generating plots": "Özet görseller hazırlanırken hata oluştu",
    "Failed while processing GA output": "Öneri sonuçları hazırlanırken hata oluştu",
    "Failed during Java GA execution": "Konum alternatifleri hesaplanırken hata oluştu",
    "Preparing Maven environment...": "Çalıştırma ortamı hazırlanıyor...",
    "Compiling and starting GA...": "Konum öneri motoru hazırlanıyor...",
    "Running plot_archives.py...": "Özet görseller hazırlanıyor...",
    "Copying latest plot...": "Özet görsel güncelleniyor...",
    "Running process_ga_data.py...": "Öneri sonuçları hazırlanıyor...",
    "Optimization completed successfully.": "Konum önerileri başarıyla oluşturuldu.",
  };

  return translations[trimmed] ?? text;
}

function localizeErrorMessage(message: string): string {
  return message
    .replace("Failed to spawn Maven process.", "Çalıştırma süreci başlatılamadı.")
    .replace("Failed to spawn Python process", "Yardımcı işlem başlatılamadı")
    .replace("Python command could not be resolved. Tried:", "Gerekli çalıştırma komutu bulunamadı. Denenenler:")
    .replace(/Java GA process timed out after (\d+) ms\./, "Öneri hesaplama süresi $1 ms sonunda doldu.")
    .replace(/Java GA process failed with exit code (\d+)\. Stderr:/, "Öneri hesaplama süreci $1 çıkış koduyla başarısız oldu. Stderr:")
    .replace(/Python script failed with exit code (\d+)/, "Yardımcı işlem $1 çıkış koduyla başarısız oldu");
}

const INITIAL_LOCKER_COUNT = 5;
const INITIAL_GA_PARAMS = getOptimalParams(INITIAL_LOCKER_COUNT);

export default function HomePage() {
  const [dashboardMode, setDashboardMode] = useState<DashboardMode>("user");
  const [inputLockerCount, setInputLockerCount] = useState(INITIAL_LOCKER_COUNT);
  const [populationSize, setPopulationSize] = useState(INITIAL_GA_PARAMS.popSize);
  const [maxGenerations, setMaxGenerations] = useState(INITIAL_GA_PARAMS.maxGenerations);

  const [mutationRate, setMutationRate] = useState(INITIAL_GA_PARAMS.mutationRate);
  const [crossoverRate, setCrossoverRate] = useState(INITIAL_GA_PARAMS.crossoverRate);

  const [archiveSize, setArchiveSize] = useState(INITIAL_GA_PARAMS.archiveSize);
  const [randomSeed, setRandomSeed] = useState("");
  const [includeExistingLockers, setIncludeExistingLockers] = useState(true);

  const [, setActiveLockerCount] = useState(INITIAL_LOCKER_COUNT);

  const [candidates, setCandidates] = useState<CandidatePoint[]>([]);
  const [boundary, setBoundary] = useState<GeoJSON.FeatureCollection | null>(null);

  const [archiveSolutions, setArchiveSolutions] = useState<ArchiveSolution[]>([]);
  const [currentSolutionIndex, setCurrentSolutionIndex] = useState(0);
  const [mcdaPreference, setMcdaPreference] = useState<number>(50);

  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(700);

  const [selectedLocker, setSelectedLocker] = useState<Locker | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{
    type: "success" | "error" | "info";
    text: string;
  } | null>(null);
  const [isPlotModalOpen, setIsPlotModalOpen] = useState(false);
  const [plotTimestamp, setPlotTimestamp] = useState(0);
  const [isPlotAvailable, setIsPlotAvailable] = useState(true);

  const [optimizationStage, setOptimizationStage] = useState("Starting");
  const [optimizationGeneration, setOptimizationGeneration] = useState(0);
  const [optimizationMaxGenerations, setOptimizationMaxGenerations] = useState(0);
  const [optimizationProgress, setOptimizationProgress] = useState(0);
  const [optimizationLogs, setOptimizationLogs] = useState<string[]>([]);

  const [isFocusMode, setIsFocusMode] = useState(false);

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
    setIsPlotAvailable(true);
  }, [plotTimestamp]);

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

  const currentSolution = getCurrentSolution(archiveSolutions, currentSolutionIndex);
  const paretoSolutionCount = useMemo(
    () => getParetoSolutionCount(archiveSolutions),
    [archiveSolutions]
  );

  const chartData = useMemo<ChartPoint[]>(() => {
    return buildParetoChartData(archiveSolutions, currentSolution);
  }, [archiveSolutions, currentSolution]);

  const paretoLineData = useMemo(() => {
    return buildParetoLineData(chartData);
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
    const clamped = Math.max(1, Math.min(inputLockerCount, 30));
    const userModeParams = getOptimalParams(clamped);
    const runPopulationSize = dashboardMode === "user" ? userModeParams.popSize : populationSize;
    const runMaxGenerations = Math.max(
      MIN_MAX_GENERATIONS,
      dashboardMode === "user" ? userModeParams.maxGenerations : maxGenerations
    );
    const runMutationRate = dashboardMode === "user" ? userModeParams.mutationRate : mutationRate;
    const runCrossoverRate = dashboardMode === "user" ? userModeParams.crossoverRate : crossoverRate;
    const runArchiveSize = dashboardMode === "user" ? userModeParams.archiveSize : archiveSize;

    setInputLockerCount(clamped);
    if (dashboardMode === "user") {
      setPopulationSize(runPopulationSize);
      setMaxGenerations(runMaxGenerations);
      setMutationRate(runMutationRate);
      setCrossoverRate(runCrossoverRate);
      setArchiveSize(runArchiveSize);
    }
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
      await runGaOptimization(
        {
          k: clamped,
          populationSize: runPopulationSize,
          maxGenerations: runMaxGenerations,
          mutationRate: runMutationRate,
          crossoverRate: runCrossoverRate,
          archiveSize: runArchiveSize,
          randomSeed: randomSeed ? parseInt(randomSeed, 10) : null,
          includeExistingLockers,
        },
        {
          onProgress: (data) => {
            if (data.stage) setOptimizationStage(data.stage);
            if (data.currentGeneration !== undefined) setOptimizationGeneration(data.currentGeneration);
            if (data.maxGenerations !== undefined) setOptimizationMaxGenerations(data.maxGenerations);
            if (data.progressPercent !== undefined) setOptimizationProgress(data.progressPercent);

            if (data.log || data.message) {
              const logMessage = (data.log || data.message) as string;
              setOptimizationLogs((prev) => [...prev, logMessage].slice(-5));
            }
          },
        }
      );

      await loadData();
      setPlotTimestamp(Date.now());

      setActiveLockerCount(clamped);
      setCurrentSolutionIndex(0);
      setIsPlaying(false);
      setSelectedLocker(null);

      setStatusMessage({ type: "success", text: `k=${clamped} için konum önerileri oluşturuldu.` });
      setTimeout(() => setStatusMessage(null), 5000);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      console.error("Optimization error:", message);
      setStatusMessage({ type: "error", text: `Hata: ${localizeErrorMessage(message)}` });
    } finally {
      setIsOptimizing(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
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

  const handleSelectSolutionId = (id: number) => {
    const index = archiveSolutions.findIndex((solution) => solution.id === id);
    if (index !== -1) setCurrentSolutionIndex(index);
  };

  const selectSolutionByPreference = useCallback(
    (preference: number, showStatus = true) => {
      const selection = selectMcdaSolution(archiveSolutions, preference);

      if (selection.status === "no-pareto") {
        if (showStatus) {
          setStatusMessage({
            type: "info",
            text: "Henüz uygun alternatif bulunmuyor. Öncelik seçimini kullanmadan önce konum önerilerini oluşturun.",
          });
        }
        return;
      }

      if (selection.status === "missing-selected") {
        if (showStatus) {
          setStatusMessage({
            type: "error",
            text: "Öncelik seçimi mevcut alternatiflerden bir öneri seçemedi.",
          });
        }
        return;
      }

      if (selection.status === "missing-index") {
        if (showStatus) {
          setStatusMessage({
            type: "error",
            text: "Öncelik seçimi bir öneri buldu, ancak bu öneri mevcut listeyle eşleştirilemedi.",
          });
        }
        return;
      }

      setCurrentSolutionIndex(selection.selectedIndex);
      setIsPlaying(false);

      if (showStatus) {
        setStatusMessage({
          type: "success",
          text: `Öncelik seçimi, yakınlık ${Math.round(
            selection.accessibilityWeight * 100
          )}% / denge ${Math.round(selection.inequityWeight * 100)}% ağırlığıyla #${selection.selectedIndex + 1} önerisini seçti.`,
        });
        setTimeout(() => setStatusMessage(null), 5000);
      }
    },
    [archiveSolutions]
  );

  const handleRunMcda = () => {
    selectSolutionByPreference(mcdaPreference);
  };

  const handleSolutionIndexChange = (value: number) => {
    const maxIndex = Math.max(0, archiveSolutions.length - 1);
    setCurrentSolutionIndex(Math.max(0, Math.min(value, maxIndex)));
  };

  const handleMcdaPreferenceChange = (value: number) => {
    setMcdaPreference(Number.isFinite(value) ? value : 50);
  };

  const handleUserMcdaPreferenceChange = (value: number) => {
    const nextValue = Number.isFinite(value) ? value : 50;
    setMcdaPreference(nextValue);
    selectSolutionByPreference(nextValue, false);
  };

  const statusClassName = statusMessage
    ? statusMessage.type === "success"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : statusMessage.type === "error"
        ? "border-rose-200 bg-rose-50 text-rose-700"
        : "border-blue-200 bg-blue-50 text-blue-700"
    : "";
  const optimizationState = {
    optimizationStageLabel: localizeGaStreamText(optimizationStage),
    optimizationGeneration,
    optimizationMaxGenerations,
    optimizationProgress,
    elapsedMs,
    localizedOptimizationLogs: optimizationLogs.map(localizeGaStreamText),
  };
  const chartState = {
    chartData,
    paretoLineData,
    onSelectSolutionId: handleSelectSolutionId,
  };

  return (
    <main className="relative min-h-screen bg-slate-50 px-4 py-4 text-slate-900 sm:px-5 lg:px-6">
      <div className="relative mx-auto flex max-w-[1500px] flex-col gap-4">
        <header className="rounded-2xl border border-slate-200 bg-white px-5 py-6 text-center shadow-sm sm:px-6">
          <div className="mx-auto max-w-4xl">
            <h1 className="text-4xl font-bold leading-tight tracking-tight text-slate-950 md:text-5xl">
              Kargo Dolabı Lokasyon Öneri Paneli
            </h1>
            <p className="mx-auto mt-3 max-w-3xl text-center text-sm leading-6 text-slate-600">
              Kadıköy için talep, erişilebilirlik ve bölgesel dengeyi dikkate alan konum önerileri oluşturun.
            </p>

            <div className="mt-5 flex justify-center">
              <DashboardModeSwitch mode={dashboardMode} onModeChange={setDashboardMode} />
            </div>

            {statusMessage ? (
              <div className={`mx-auto mt-4 w-full max-w-3xl rounded-lg border px-4 py-3 text-sm font-medium shadow-sm ${statusClassName}`}>
                <div className="flex items-center justify-center gap-3">
                  {statusMessage.type === "success" && <span className="text-lg">✓</span>}
                  {statusMessage.type === "error" && <span className="text-lg">⚠</span>}
                  {statusMessage.type === "info" && <span className="text-lg">ℹ</span>}
                  <p>{statusMessage.text}</p>
                </div>
              </div>
            ) : null}
          </div>
        </header>

        {dashboardMode === "dev" ? (
          <DevDashboard
            candidates={candidates}
            boundary={boundary}
            lockersForDisplay={lockersForDisplay}
            selectedLocker={selectedLocker}
            onSelectLocker={setSelectedLocker}
            currentSolution={currentSolution}
            archiveSolutions={archiveSolutions}
            controlState={{
              lockerCount: inputLockerCount,
              includeExistingLockers,
              populationSize,
              maxGenerations,
              mutationRate,
              crossoverRate,
              archiveSize,
              randomSeed,
              currentSolutionIndex,
              archiveSolutionCount: archiveSolutions.length,
              isPlaying,
              playbackSpeed,
              mcdaPreference,
              paretoSolutionCount,
              isOptimizing,
            }}
            controlActions={{
              onLockerCountChange: handleLockerCountChange,
              onIncludeExistingLockersChange: setIncludeExistingLockers,
              onPopulationSizeChange: setPopulationSize,
              onMaxGenerationsChange: setMaxGenerations,
              onMutationRateChange: setMutationRate,
              onCrossoverRateChange: setCrossoverRate,
              onArchiveSizeChange: setArchiveSize,
              onRandomSeedChange: setRandomSeed,
              onShowResults: handleShowResults,
              onTogglePlayback: () => setIsPlaying((prev) => !prev),
              onPrevSolution: handlePrevSolution,
              onNextSolution: handleNextSolution,
              onSolutionIndexChange: handleSolutionIndexChange,
              onPlaybackSpeedChange: setPlaybackSpeed,
              onMcdaPreferenceChange: handleMcdaPreferenceChange,
              onRunMcda: handleRunMcda,
            }}
            optimizationState={optimizationState}
            chartState={chartState}
            plotState={{
              plotTimestamp,
              isPlotAvailable,
              onPlotAvailableChange: setIsPlotAvailable,
              onOpenPlotModal: () => setIsPlotModalOpen(true),
            }}
            focusState={{
              isFocusMode,
              onToggleFocusMode: () => setIsFocusMode((prev) => !prev),
            }}
          />
        ) : (
          <UserDashboard
            candidates={candidates}
            boundary={boundary}
            lockersForDisplay={lockersForDisplay}
            selectedLocker={selectedLocker}
            onSelectLocker={setSelectedLocker}
            currentSolution={currentSolution}
            controlState={{
              lockerCount: inputLockerCount,
              includeExistingLockers,
              isOptimizing,
              mcdaPreference,
              paretoSolutionCount,
            }}
            controlActions={{
              onLockerCountChange: handleLockerCountChange,
              onIncludeExistingLockersChange: setIncludeExistingLockers,
              onShowResults: handleShowResults,
              onMcdaPreferenceChange: handleUserMcdaPreferenceChange,
            }}
            chartState={chartState}
            optimizationState={optimizationState}
          />
        )}

        <footer className="mt-4 rounded-2xl border border-white/60 bg-white/55 px-6 py-4 shadow-[0_6px_20px_rgba(15,23,42,0.04)] backdrop-blur-xl">
          <div className="flex flex-col items-center justify-between gap-2 sm:flex-row">
            <p className="text-[11px] font-medium text-slate-400">
              © {new Date().getFullYear()} Kargo Dolabı Lokasyon Öneri Paneli
            </p>
            <div className="flex items-center gap-4">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-300">Lokasyon Optimizasyonu</span>
              <span className="h-3 w-px bg-slate-200" />
              <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-300">Kadıköy, İstanbul</span>
            </div>
          </div>
        </footer>
      </div>

      {isPlotModalOpen && (
        <div
          className="fixed inset-0 z-[9999] flex animate-in items-center justify-center bg-slate-900/90 p-4 backdrop-blur-md duration-300 fade-in sm:p-8"
          onClick={() => setIsPlotModalOpen(false)}
        >
          <div className="relative flex h-full w-full max-w-7xl flex-col items-center justify-center">
            <button
              type="button"
              className="absolute -right-4 -top-4 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white text-slate-900 shadow-xl transition hover:scale-110 hover:bg-slate-100 sm:right-0 sm:top-0"
              onClick={(event) => {
                event.stopPropagation();
                setIsPlotModalOpen(false);
              }}
            >
              <span className="text-xl font-bold">✕</span>
            </button>
            <div
              className="relative h-full w-full overflow-hidden rounded-2xl border border-white/20 bg-white shadow-2xl"
              onClick={(event) => event.stopPropagation()}
            >
              {isPlotAvailable ? (
                <img
                  src={`/mock/archive_comparison_latest.png?t=${plotTimestamp}`}
                  alt="Tam ekran optimizasyon özeti"
                  onError={() => setIsPlotAvailable(false)}
                  className="absolute inset-0 h-full w-full object-contain"
                />
              ) : (
                <div className="flex h-full items-center justify-center px-6 text-center text-sm font-medium text-slate-500">
                  Optimizasyon tamamlandığında özet görsel burada görüntülenir.
                </div>
              )}
            </div>
            <div className="mt-4 text-center">
              <p className="text-sm font-medium text-white/70">Optimizasyon özeti - detaylı görünüm</p>
              <p className="mt-1 text-xs text-white/40">
                Geri dönmek için dış alana tıklayın veya kapat düğmesini kullanın
              </p>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

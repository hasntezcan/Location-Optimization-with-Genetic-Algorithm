"use client";

/* eslint-disable @next/next/no-img-element */

import { ArchiveComparisonChart } from "@/components/dashboard/archive-comparison-chart";
import { ControlPanel } from "@/components/dashboard/control-panel";
import { DashboardMapPanel } from "@/components/dashboard/dashboard-map-panel";
import { LockerDetailPanel } from "@/components/dashboard/locker-detail-panel";
import type { ChartPoint } from "@/lib/chart-data";
import type { ArchiveSolution, CandidatePoint, Locker } from "@/lib/types";

function formatMetric(value: number | undefined, digits = 3): string {
  return Number.isFinite(value) ? value!.toFixed(digits) : "Yok";
}

function getRecommendationType(solution: ArchiveSolution | null): string {
  if (!solution) return "Henüz oluşturulmadı";
  if (solution.isBestF1) return "Yakınlık odaklı öneri";
  if (solution.isBestF2) return "Denge odaklı öneri";
  if (solution.isPareto) return "Öne çıkan alternatif";
  return "Alternatif öneri";
}

export type DevDashboardControlState = {
  lockerCount: number;
  includeExistingLockers: boolean;
  populationSize: number;
  maxGenerations: number;
  mutationRate: number;
  crossoverRate: number;
  archiveSize: number;
  randomSeed: string;
  currentSolutionIndex: number;
  archiveSolutionCount: number;
  isPlaying: boolean;
  playbackSpeed: number;
  mcdaPreference: number;
  paretoSolutionCount: number;
  isOptimizing: boolean;
};

export type DevDashboardControlActions = {
  onLockerCountChange: (value: number) => void;
  onIncludeExistingLockersChange: (value: boolean) => void;
  onPopulationSizeChange: (value: number) => void;
  onMaxGenerationsChange: (value: number) => void;
  onMutationRateChange: (value: number) => void;
  onCrossoverRateChange: (value: number) => void;
  onArchiveSizeChange: (value: number) => void;
  onRandomSeedChange: (value: string) => void;
  onShowResults: () => void;
  onTogglePlayback: () => void;
  onPrevSolution: () => void;
  onNextSolution: () => void;
  onSolutionIndexChange: (value: number) => void;
  onPlaybackSpeedChange: (value: number) => void;
  onMcdaPreferenceChange: (value: number) => void;
  onRunMcda: () => void;
};

export type DevDashboardOptimizationState = {
  optimizationStageLabel: string;
  optimizationGeneration: number;
  optimizationMaxGenerations: number;
  optimizationProgress: number;
  elapsedMs: number;
  localizedOptimizationLogs: string[];
};

export type DevDashboardChartState = {
  chartData: ChartPoint[];
  paretoLineData: ChartPoint[];
  onSelectSolutionId: (id: number) => void;
};

export type DevDashboardPlotState = {
  plotTimestamp: number;
  isPlotAvailable: boolean;
  onPlotAvailableChange: (isAvailable: boolean) => void;
  onOpenPlotModal: () => void;
};

export type DevDashboardFocusState = {
  isFocusMode: boolean;
  onToggleFocusMode: () => void;
};

export type DevDashboardProps = {
  candidates: CandidatePoint[];
  boundary: GeoJSON.FeatureCollection | null;
  lockersForDisplay: Locker[];
  selectedLocker: Locker | null;
  onSelectLocker: (locker: Locker | null) => void;
  currentSolution: ArchiveSolution | null;
  archiveSolutions: ArchiveSolution[];
  controlState: DevDashboardControlState;
  controlActions: DevDashboardControlActions;
  optimizationState: DevDashboardOptimizationState;
  chartState: DevDashboardChartState;
  plotState: DevDashboardPlotState;
  focusState: DevDashboardFocusState;
};

export function DevDashboard({
  candidates,
  boundary,
  lockersForDisplay,
  selectedLocker,
  onSelectLocker,
  currentSolution,
  archiveSolutions,
  controlState,
  controlActions,
  optimizationState,
  chartState,
  plotState,
  focusState,
}: DevDashboardProps) {
  const selectedSolutionLabel = currentSolution
    ? `#${controlState.currentSolutionIndex + 1}`
    : "Öneri yok";
  const currentSolutionType = getRecommendationType(currentSolution);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Seçili öneri</p>
          <div className="mt-2 flex items-end justify-between gap-3">
            <p className="text-2xl font-semibold tabular-nums text-slate-950">
              {selectedSolutionLabel}
            </p>
            <span className="rounded-md bg-white px-2 py-1 text-[10px] font-semibold text-slate-500 shadow-sm">
              {currentSolutionType}
            </span>
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Uygun alternatifler
          </p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-950">
            {archiveSolutions.length}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {controlState.paretoSolutionCount} öne çıkan alternatif
          </p>
        </div>
        <div className="rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-blue-500">
            Ortalama erişim performansı
          </p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-blue-800">
            {formatMetric(currentSolution?.metrics.accessibility, 4)}
          </p>
          <p className="mt-1 text-xs text-blue-700/70">Müşteriye yakınlık</p>
        </div>
        <div className="rounded-lg border border-emerald-100 bg-emerald-50/70 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600">
            Bölgesel denge
          </p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-emerald-800">
            {formatMetric(currentSolution?.metrics.equity, 4)}
          </p>
          <p className="mt-1 text-xs text-emerald-700/70">Mahalleler arası denge</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-12 gap-4 transition-all duration-500 lg:min-h-[500px]">
        <div
          className={`col-span-12 transition-all duration-500 lg:h-[calc(100vh-300px)] lg:min-h-[500px] ${
            focusState.isFocusMode ? "hidden" : "lg:col-span-3"
          }`}
        >
          <ControlPanel
            lockerCount={controlState.lockerCount}
            onLockerCountChange={controlActions.onLockerCountChange}
            populationSize={controlState.populationSize}
            onPopulationSizeChange={controlActions.onPopulationSizeChange}
            maxGenerations={controlState.maxGenerations}
            onMaxGenerationsChange={controlActions.onMaxGenerationsChange}
            mutationRate={controlState.mutationRate}
            onMutationRateChange={controlActions.onMutationRateChange}
            crossoverRate={controlState.crossoverRate}
            onCrossoverRateChange={controlActions.onCrossoverRateChange}
            archiveSize={controlState.archiveSize}
            onArchiveSizeChange={controlActions.onArchiveSizeChange}
            randomSeed={controlState.randomSeed}
            onRandomSeedChange={controlActions.onRandomSeedChange}
            onShowResults={controlActions.onShowResults}
            currentGeneration={controlState.currentSolutionIndex}
            generationCount={controlState.archiveSolutionCount}
            isPlaying={controlState.isPlaying}
            playbackSpeed={controlState.playbackSpeed}
            onTogglePlayback={controlActions.onTogglePlayback}
            onPrevGeneration={controlActions.onPrevSolution}
            onNextGeneration={controlActions.onNextSolution}
            onGenerationChange={controlActions.onSolutionIndexChange}
            onPlaybackSpeedChange={controlActions.onPlaybackSpeedChange}
            mcdaPreference={controlState.mcdaPreference}
            onMcdaPreferenceChange={controlActions.onMcdaPreferenceChange}
            onRunMcda={controlActions.onRunMcda}
            paretoSolutionCount={controlState.paretoSolutionCount}
            isOptimizing={controlState.isOptimizing}
            isCurrentSolutionPareto={currentSolution?.isPareto}
            isBestF1={currentSolution?.isBestF1}
            isBestF2={currentSolution?.isBestF2}
          />
        </div>

        <div className="relative col-span-12 xl:col-span-6">
          <DashboardMapPanel
          candidates={candidates}
          boundary={boundary}
          lockers={lockersForDisplay}
          selectedLocker={selectedLocker}
          onSelectLocker={onSelectLocker}
          currentSolution={currentSolution}
          isOptimizing={controlState.isOptimizing}
          className={`col-span-12 transition-all duration-500 lg:h-[calc(100vh-300px)] lg:min-h-[500px] ${
            focusState.isFocusMode ? "lg:col-span-7" : "lg:col-span-6"
          }`}
            {...optimizationState}
          />

          <label className="absolute bottom-4 right-4 z-20 flex cursor-pointer items-center gap-2 rounded-full border border-slate-200/80 bg-white/90 px-3 py-2 text-[10px] font-semibold text-slate-700 shadow-sm backdrop-blur-sm">
            <input
              type="checkbox"
              checked={controlState.includeExistingLockers}
              onChange={(event) => controlActions.onIncludeExistingLockersChange(event.target.checked)}
              disabled={controlState.isOptimizing}
              className="h-3.5 w-3.5 rounded border-slate-300 accent-emerald-600 disabled:cursor-not-allowed"
            />
            <span>Mevcut dolapları hesaba kat</span>
          </label>
        </div>

        <div
          className={`col-span-12 transition-all duration-500 lg:h-[calc(100vh-300px)] lg:min-h-[500px] ${
            focusState.isFocusMode ? "lg:col-span-5" : "lg:col-span-3"
          }`}
        >
          {selectedLocker && currentSolution ? (
            <LockerDetailPanel
              locker={selectedLocker}
              solution={currentSolution}
              onClose={() => onSelectLocker(null)}
            />
          ) : (
            <div className="flex h-full flex-col gap-4 overflow-hidden">
              <div
                className={`flex min-h-[245px] flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${
                  focusState.isFocusMode ? "h-full" : ""
                }`}
              >
                <ArchiveComparisonChart
                  chartData={chartState.chartData}
                  paretoLineData={chartState.paretoLineData}
                  onSelectSolutionId={chartState.onSelectSolutionId}
                  showFocusButton
                  isFocusMode={focusState.isFocusMode}
                  onToggleFocusMode={focusState.onToggleFocusMode}
                />
              </div>

              {!focusState.isFocusMode ? (
                <div className="flex min-h-[210px] flex-1 flex-col items-center justify-center overflow-hidden rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
                  <div className="flex h-full w-full flex-col p-2">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                        Optimizasyon özeti
                      </span>
                      <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[9px] font-semibold text-indigo-600">
                        Detayı gör
                      </span>
                    </div>
                    <div
                      className={`group relative flex-1 overflow-hidden rounded-xl border border-slate-200/60 bg-white ${
                        plotState.isPlotAvailable ? "cursor-zoom-in" : "cursor-default"
                      }`}
                      onClick={() => {
                        if (plotState.isPlotAvailable) plotState.onOpenPlotModal();
                      }}
                    >
                      {plotState.isPlotAvailable ? (
                        <>
                          <img
                            src={`/mock/archive_comparison_latest.png?t=${plotState.plotTimestamp}`}
                            alt="Optimizasyon özeti"
                            className="absolute inset-0 h-full w-full object-contain transition-transform duration-300 group-hover:scale-105"
                            onError={() => plotState.onPlotAvailableChange(false)}
                          />
                          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/0 opacity-0 transition-colors group-hover:bg-slate-900/5 group-hover:opacity-100">
                            <span className="rounded-full bg-white/90 px-3 py-1.5 text-[10px] font-bold shadow-lg">
                              DETAYI GÖR
                            </span>
                          </div>
                        </>
                      ) : (
                        <div className="flex h-full min-h-[150px] items-center justify-center px-4 text-center text-xs leading-5 text-slate-500">
                          Optimizasyon tamamlandığında özet görsel burada görüntülenir.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

"use client";

import { DashboardMapPanel } from "@/components/dashboard/dashboard-map-panel";
import { UserControlPanel } from "@/components/dashboard/user-control-panel";
import type { ChartPoint } from "@/lib/chart-data";
import type { ArchiveSolution, CandidatePoint, Locker } from "@/lib/types";

export type UserDashboardOptimizationState = {
  optimizationStageLabel: string;
  optimizationGeneration: number;
  optimizationMaxGenerations: number;
  optimizationProgress: number;
  elapsedMs: number;
  localizedOptimizationLogs: string[];
};

export type UserDashboardControlState = {
  lockerCount: number;
  includeExistingLockers: boolean;
  isOptimizing: boolean;
  mcdaPreference: number;
  paretoSolutionCount: number;
};

export type UserDashboardControlActions = {
  onLockerCountChange: (value: number) => void;
  onIncludeExistingLockersChange: (value: boolean) => void;
  onShowResults: () => void;
  onMcdaPreferenceChange: (value: number) => void;
};

export type UserDashboardChartState = {
  chartData: ChartPoint[];
  paretoLineData: ChartPoint[];
  onSelectSolutionId: (id: number) => void;
};

export type UserDashboardProps = {
  candidates: CandidatePoint[];
  boundary: GeoJSON.FeatureCollection | null;
  lockersForDisplay: Locker[];
  selectedLocker: Locker | null;
  onSelectLocker: (locker: Locker | null) => void;
  currentSolution: ArchiveSolution | null;
  controlState: UserDashboardControlState;
  controlActions: UserDashboardControlActions;
  chartState: UserDashboardChartState;
  optimizationState: UserDashboardOptimizationState;
};

export function UserDashboard({
  candidates,
  boundary,
  lockersForDisplay,
  selectedLocker,
  onSelectLocker,
  currentSolution,
  controlState,
  controlActions,
  chartState,
  optimizationState,
}: UserDashboardProps) {
  return (
    <section className="relative rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-4 lg:flex lg:h-[calc(100vh-180px)] lg:min-h-[640px] lg:items-end lg:justify-end">
          <UserControlPanel
            lockerCount={controlState.lockerCount}
            onLockerCountChange={controlActions.onLockerCountChange}
            onShowResults={controlActions.onShowResults}
            isOptimizing={controlState.isOptimizing}
            mcdaPreference={controlState.mcdaPreference}
            onMcdaPreferenceChange={controlActions.onMcdaPreferenceChange}
            paretoSolutionCount={controlState.paretoSolutionCount}
            chartData={chartState.chartData}
            paretoLineData={chartState.paretoLineData}
            onSelectSolutionId={chartState.onSelectSolutionId}
          />
        </div>

        <DashboardMapPanel
          candidates={candidates}
          boundary={boundary}
          lockers={lockersForDisplay}
          selectedLocker={selectedLocker}
          onSelectLocker={onSelectLocker}
          currentSolution={currentSolution}
          isOptimizing={controlState.isOptimizing}
          className="col-span-12 lg:col-span-8 lg:h-[calc(100vh-180px)] lg:min-h-[640px]"
          {...optimizationState}
        />
      </div>

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
    </section>
  );
}

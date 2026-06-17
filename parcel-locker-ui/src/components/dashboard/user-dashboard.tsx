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
  isOptimizing: boolean;
  mcdaPreference: number;
  paretoSolutionCount: number;
};

export type UserDashboardControlActions = {
  onLockerCountChange: (value: number) => void;
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
    <section className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-4 lg:h-[calc(100vh-210px)] lg:min-h-[610px]">
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
          className="col-span-12 lg:col-span-8 lg:h-[calc(100vh-210px)] lg:min-h-[610px]"
          {...optimizationState}
        />
      </div>
    </section>
  );
}

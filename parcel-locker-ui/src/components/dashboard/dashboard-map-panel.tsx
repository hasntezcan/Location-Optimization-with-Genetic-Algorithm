"use client";

import dynamic from "next/dynamic";
import type { ArchiveSolution, CandidatePoint, Locker } from "@/lib/types";

const LockerMap = dynamic(
  () => import("@/components/dashboard/locker-map").then((mod) => mod.LockerMap),
  { ssr: false }
);

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return m > 0 ? `${m}dk ${String(s).padStart(2, "0")}sn` : `${s}sn`;
}

export type DashboardMapPanelProps = {
  candidates: CandidatePoint[];
  boundary: GeoJSON.FeatureCollection | null;
  lockers: Locker[];
  selectedLocker: Locker | null;
  onSelectLocker: (locker: Locker | null) => void;
  currentSolution: ArchiveSolution | null;
  isOptimizing: boolean;
  optimizationStageLabel: string;
  optimizationGeneration: number;
  optimizationMaxGenerations: number;
  optimizationProgress: number;
  elapsedMs: number;
  localizedOptimizationLogs: string[];
  className?: string;
};

export function DashboardMapPanel({
  candidates,
  boundary,
  lockers,
  selectedLocker,
  onSelectLocker,
  currentSolution,
  isOptimizing,
  optimizationStageLabel,
  optimizationGeneration,
  optimizationMaxGenerations,
  optimizationProgress,
  elapsedMs,
  localizedOptimizationLogs,
  className = "",
}: DashboardMapPanelProps) {
  return (
    <div className={`relative min-h-[350px] ${className}`}>
      {isOptimizing ? (
        <div className="absolute inset-0 z-[60] flex animate-in items-center justify-center rounded-2xl bg-white/60 p-6 backdrop-blur-sm duration-300 fade-in">
          <div className="w-full max-w-md rounded-2xl border border-white/60 bg-white/80 p-6 shadow-2xl backdrop-blur-xl">
            <h3 className="mb-2 text-lg font-bold text-slate-900">Öneriler oluşturuluyor</h3>
            <p className="mb-6 text-xs font-semibold uppercase tracking-widest text-indigo-600">
              {optimizationStageLabel}
            </p>

            {optimizationMaxGenerations > 0 ? (
              <div className="mb-4">
                <div className="mb-2 flex justify-between text-xs font-bold text-slate-500">
                  <span>
                    İşlem adımı {optimizationGeneration} / {optimizationMaxGenerations}
                  </span>
                  <span>{optimizationProgress}%</span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-full rounded-full bg-indigo-500 transition-all duration-300"
                    style={{ width: `${optimizationProgress}%` }}
                  />
                </div>
                <div className="mt-2 flex justify-between text-[10px] font-medium text-slate-400">
                  <span>Geçen süre: {formatDuration(elapsedMs)}</span>
                  {optimizationProgress > 5 ? (
                    <span>
                      Tahmini kalan: ~
                      {formatDuration((elapsedMs / optimizationProgress) * (100 - optimizationProgress))}
                    </span>
                  ) : null}
                </div>
              </div>
            ) : null}

            <div className="flex h-24 flex-col justify-end overflow-hidden rounded-xl bg-slate-900 p-3 font-mono text-[10px] text-emerald-400 shadow-inner">
              {localizedOptimizationLogs.map((log, index) => (
                <div key={`${log}-${index}`} className="truncate">
                  {log}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {currentSolution ? (
        <LockerMap
          candidates={candidates}
          boundary={boundary}
          lockers={lockers}
          selectedLocker={selectedLocker}
          onSelectLocker={onSelectLocker}
          currentGeneration={currentSolution}
        />
      ) : (
        <div className="flex h-full min-h-[420px] flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <p className="text-sm font-semibold text-slate-700">Harita verileri hazırlanıyor...</p>
          <p className="mt-2 max-w-sm text-xs leading-5 text-slate-500">
            Önerileri oluşturduğunuzda seçilen konumlar haritada görüntülenecek.
          </p>
        </div>
      )}
    </div>
  );
}

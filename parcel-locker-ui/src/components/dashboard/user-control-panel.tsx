"use client";

import { useEffect, useState } from "react";
import { ArchiveComparisonChart } from "@/components/dashboard/archive-comparison-chart";
import type { ChartPoint } from "@/lib/chart-data";

export type UserControlPanelProps = {
  lockerCount: number;
  onLockerCountChange: (value: number) => void;
  onShowResults: () => void;
  isOptimizing: boolean;
  mcdaPreference: number;
  onMcdaPreferenceChange: (value: number) => void;
  paretoSolutionCount: number;
  chartData: ChartPoint[];
  paretoLineData: ChartPoint[];
  onSelectSolutionId: (id: number) => void;
};

const cardClass =
  "rounded-lg border border-slate-200 bg-white p-3 shadow-[0_1px_2px_rgba(15,23,42,0.05)]";
const inputClass =
  "h-9 w-16 rounded-lg border border-slate-200 bg-white px-2 text-center text-sm font-semibold tabular-nums text-slate-800 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400";

export function UserControlPanel({
  lockerCount,
  onLockerCountChange,
  onShowResults,
  isOptimizing,
  mcdaPreference,
  onMcdaPreferenceChange,
  paretoSolutionCount,
  chartData,
  paretoLineData,
  onSelectSolutionId,
}: UserControlPanelProps) {
  const [countText, setCountText] = useState(String(lockerCount));
  const safeMcdaPreference = Number.isFinite(mcdaPreference) ? mcdaPreference : 50;

  useEffect(() => {
    setCountText(String(lockerCount));
  }, [lockerCount]);

  const commitLockerCount = (raw: string) => {
    const parsed = Number(raw);
    const clamped = Number.isFinite(parsed) ? Math.max(1, Math.min(20, parsed)) : 1;
    setCountText(String(clamped));
    onLockerCountChange(clamped);
  };

  return (
    <aside className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/80 p-3 shadow-sm">
      <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden">
        <div className={cardClass}>
          <label className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Kaç konum önerilsin?
          </label>
          <div className="mt-2 flex items-center gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={countText}
              onChange={(event) => {
                const cleaned = event.target.value.replace(/[^0-9]/g, "");
                setCountText(cleaned);
                if (cleaned !== "") {
                  const parsed = Number(cleaned);
                  if (parsed >= 1 && parsed <= 20) onLockerCountChange(parsed);
                }
              }}
              onBlur={() => commitLockerCount(countText)}
              disabled={isOptimizing}
              className={inputClass}
            />
            <button
              type="button"
              onClick={onShowResults}
              disabled={isOptimizing}
              className={`h-9 flex-1 rounded-lg px-3 text-xs font-bold text-white shadow-sm transition ${
                isOptimizing
                  ? "cursor-not-allowed bg-slate-400"
                  : "bg-emerald-600 hover:bg-emerald-700"
              }`}
            >
              Çalıştır
            </button>
          </div>
        </div>

        <div className={cardClass}>
          <div className="flex items-center justify-between gap-3">
            <label className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Öncelik
            </label>
            <span className="text-[10px] font-bold tabular-nums text-emerald-700">
              {paretoSolutionCount} alternatif
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={safeMcdaPreference}
            onChange={(event) => onMcdaPreferenceChange(Number(event.target.value))}
            disabled={isOptimizing || paretoSolutionCount === 0}
            className="mt-3 h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-emerald-600 disabled:opacity-50"
          />
          <div className="mt-2 flex justify-between text-[9px] font-semibold uppercase tracking-wider text-slate-400">
            <span>Erişilebilirlik</span>
            <span>Bölgesel denge</span>
          </div>
        </div>

        <div className="min-h-0 flex-1 rounded-lg border border-slate-200 bg-white p-3 shadow-[0_1px_2px_rgba(15,23,42,0.05)]">
          <ArchiveComparisonChart
            title="Alternatif Karşılaştırması"
            chartData={chartData}
            paretoLineData={paretoLineData}
            onSelectSolutionId={onSelectSolutionId}
            showLegend={false}
            className="h-full"
            chartClassName="min-h-[390px]"
          />
        </div>
      </div>
    </aside>
  );
}

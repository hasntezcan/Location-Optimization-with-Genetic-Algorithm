"use client";

import { useState } from "react";

type ControlPanelProps = {
  lockerCount: number;
  onLockerCountChange: (value: number) => void;
  populationSize: number;
  onPopulationSizeChange: (value: number) => void;
  maxGenerations: number;
  onMaxGenerationsChange: (value: number) => void;
  mutationRate: number;
  onMutationRateChange: (value: number) => void;
  onShowResults: () => void;
  currentGeneration: number;
  generationCount: number;
  isPlaying: boolean;
  playbackSpeed: number;
  onTogglePlayback: () => void;
  onPrevGeneration: () => void;
  onNextGeneration: () => void;
  onGenerationChange: (value: number) => void;
  onPlaybackSpeedChange: (value: number) => void;
  isOptimizing?: boolean;
  isCurrentSolutionPareto?: boolean;
  isBestF1?: boolean;
  isBestF2?: boolean;
};

export function ControlPanel({
  lockerCount,
  onLockerCountChange,
  populationSize,
  onPopulationSizeChange,
  maxGenerations,
  onMaxGenerationsChange,
  mutationRate,
  onMutationRateChange,
  onShowResults,
  currentGeneration,
  generationCount,
  isPlaying,
  playbackSpeed,
  onTogglePlayback,
  onPrevGeneration,
  onNextGeneration,
  onGenerationChange,
  onPlaybackSpeedChange,
  isOptimizing = false,
  isCurrentSolutionPareto = false,
  isBestF1 = false,
  isBestF2 = false,
}: ControlPanelProps) {

  const [localLockerCount, setLocalLockerCount] = useState<string>(lockerCount.toString());

  const handleLockerCountChange = (value: string) => {
    setLocalLockerCount(value);
    if (value !== "" && !isNaN(Number(value))) {
      onLockerCountChange(Number(value));
    }
  };

  const handleLockerCountBlur = () => {
    if (localLockerCount === "" || isNaN(Number(localLockerCount))) {
      setLocalLockerCount("1");
      onLockerCountChange(1);
    } else {
      const val = Math.max(1, Math.min(50, Number(localLockerCount)));
      setLocalLockerCount(val.toString());
      onLockerCountChange(val);
    }
  };

  return (
    <aside className="flex h-full min-h-0 flex-col overflow-hidden rounded-[30px] border border-white/60 bg-white/55 p-4 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl lg:max-h-[calc(100vh-290px)]">
      <div className="min-h-0 flex-1 overflow-y-auto pr-2">
        <div>
          <span className="inline-flex rounded-full border border-slate-200/70 bg-white/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            Controls
          </span>

          <h2 className="mt-3 text-[22px] font-semibold tracking-tight text-slate-900">
            Archive Explorer
          </h2>

          <p className="mt-2 text-sm leading-6 text-slate-600">
            Browse optimized solutions from the Pareto archive (Accessibility vs. Equity).
          </p>
        </div>

          <div className="mt-8 space-y-6">
          <div className="rounded-[22px] border border-slate-200/50 bg-white/60 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Locker Count (k)
              </label>
              <span className="rounded-lg bg-indigo-600 px-2 py-1 text-[11px] font-bold text-white">
                Active: {lockerCount}
              </span>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <input
                type="text"
                value={localLockerCount}
                onChange={(e) => handleLockerCountChange(e.target.value)}
                onBlur={handleLockerCountBlur}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
                      <button
                        onClick={onShowResults}
                        disabled={isOptimizing}
                        className={`h-10 whitespace-nowrap rounded-xl px-4 text-xs font-bold text-white shadow-md transition ${
                          isOptimizing
                            ? "bg-slate-400 cursor-not-allowed"
                            : "bg-indigo-600 hover:bg-indigo-700"
                        }`}
                      >
                        {isOptimizing ? "Optimizing..." : "Run Optimization"}
                      </button>
                    </div>
                    <p className="mt-2 text-[10px] text-slate-400">
                      * Changing parameters requires re-running the optimization.
                    </p>
          </div>

          <div className="rounded-[22px] border border-slate-200/50 bg-white/60 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Current Solution
              </label>
              <div className="flex flex-wrap items-center justify-end gap-2">
                {isBestF1 && (
                  <span className="rounded-lg bg-blue-500 px-2 py-1 text-[10px] font-bold text-white shadow-sm">
                    BEST DISTANCE
                  </span>
                )}
                {isBestF2 && (
                  <span className="rounded-lg bg-emerald-600 px-2 py-1 text-[10px] font-bold text-white shadow-sm">
                    BEST COST
                  </span>
                )}
                {isCurrentSolutionPareto && !isBestF1 && !isBestF2 && (
                  <span className="rounded-lg bg-emerald-500 px-2 py-1 text-[10px] font-bold text-white animate-pulse">
                    PARETO
                  </span>
                )}
                <span className="rounded-lg bg-slate-900 px-2 py-1 text-[11px] font-bold text-white">
                  #{currentGeneration + 1}
                </span>
              </div>
            </div>

            <div className="mt-4 flex items-center gap-3">
              <button
                onClick={onPrevGeneration}
                disabled={currentGeneration === 0}
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
              >
                ←
              </button>
              
              <input
                type="range"
                min={0}
                max={generationCount - 1}
                value={currentGeneration}
                onChange={(e) => onGenerationChange(Number(e.target.value))}
                className={`h-1.5 flex-1 cursor-pointer appearance-none rounded-full transition-colors ${
                  isCurrentSolutionPareto ? "bg-emerald-200 accent-emerald-600" : "bg-slate-200 accent-slate-900"
                }`}
              />

              <button
                onClick={onNextGeneration}
                disabled={currentGeneration === generationCount - 1}
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
              >
                →
              </button>
            </div>
          </div>

          <div className="rounded-[22px] border border-slate-200/50 bg-white/60 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Playback Control
              </label>
              <button
                onClick={onTogglePlayback}
                className={`flex h-10 w-24 items-center justify-center rounded-xl text-xs font-bold transition ${
                  isPlaying 
                    ? "bg-rose-500 text-white shadow-[0_4px_12px_rgba(244,63,94,0.3)]" 
                    : "bg-emerald-500 text-white shadow-[0_4px_12px_rgba(16,185,129,0.3)]"
                }`}
              >
                {isPlaying ? "Stop" : "Auto-Play"}
              </button>
            </div>
            
            <div className="mt-4">
              <div className="flex justify-between text-[10px] font-bold text-slate-400">
                <span>Speed</span>
                <span>{playbackSpeed}ms</span>
              </div>
              <input
                type="range"
                min={100}
                max={2000}
                step={100}
                value={playbackSpeed}
                onChange={(e) => onPlaybackSpeedChange(Number(e.target.value))}
                className="mt-2 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-slate-900"
              />
            </div>
          </div>
        </div>

        <div className="mt-8 space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400 px-1">
            Algorithm Parameters
          </h3>

          <div className="mt-5 space-y-5">
            <div className="rounded-[22px] border border-slate-200/50 bg-white/60 p-4 shadow-sm">
              <div className="space-y-4">
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Population Size
                  </label>
                  <input
                    type="number"
                    min={10}
                    max={500}
                    value={populationSize}
                    onChange={(e) => onPopulationSizeChange(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Max Generations
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={500}
                    value={maxGenerations}
                    onChange={(e) => onMaxGenerationsChange(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Mutation Rate
                  </label>
                  <div className="mt-2 flex items-center gap-3">
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.01}
                      value={mutationRate}
                      onChange={(e) => onMutationRateChange(Number(e.target.value))}
                      className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-slate-200 accent-indigo-600"
                    />
                    <span className="text-sm font-bold text-slate-700 w-10">
                      {Math.round(mutationRate * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
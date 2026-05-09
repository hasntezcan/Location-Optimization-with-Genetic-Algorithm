"use client";

import { useState, useEffect } from "react";

type ControlPanelProps = {
  lockerCount: number;
  onLockerCountChange: (value: number) => void;
  populationSize: number;
  onPopulationSizeChange: (value: number) => void;
  maxGenerations: number;
  onMaxGenerationsChange: (value: number) => void;
  mutationRate: number;
  onMutationRateChange: (value: number) => void;
  crossoverRate: number;
  onCrossoverRateChange: (value: number) => void;
  archiveSize: number;
  onArchiveSizeChange: (value: number) => void;
  randomSeed: string;
  onRandomSeedChange: (value: string) => void;
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
  mcdaPreference: number;
  onMcdaPreferenceChange: (value: number) => void;
  onRunMcda: () => void;
  paretoSolutionCount: number;
  isOptimizing?: boolean;
  isCurrentSolutionPareto?: boolean;
  isBestF1?: boolean;
  isBestF2?: boolean;
};

/**
 * Manages a text input backed by a numeric state.
 * Prevents leading-zero glitch by storing raw text locally
 * and only committing the parsed value on blur.
 */
function useNumericInput(
  externalValue: number,
  onChange: (v: number) => void,
  min: number,
  max: number
) {
  const [text, setText] = useState(externalValue.toString());

  // Sync when external value changes (e.g. after optimization resets)
  useEffect(() => {
    setText(externalValue.toString());
  }, [externalValue]);

  const handleChange = (raw: string) => {
    // Allow empty string while editing and keep only positive numeric input.
    const cleaned = raw.replace(/[^0-9]/g, "");
    setText(cleaned);
    
    // Call onChange immediately if the value is within bounds
    if (cleaned !== "" && !isNaN(Number(cleaned))) {
      const val = Number(cleaned);
      if (val >= min && val <= max) {
        onChange(val);
      }
    }
  };

  const handleBlur = () => {
    if (text === "" || isNaN(Number(text))) {
      const clamped = Math.max(min, Math.min(max, min));
      setText(clamped.toString());
      onChange(clamped);
    } else {
      const val = Number(text);
      if (val < min || val > max) {
        const clamped = Math.max(min, Math.min(max, val));
        setText(clamped.toString());
        onChange(clamped);
      }
    }
  };

  return { text, handleChange, handleBlur };
}

export function ControlPanel({
  lockerCount,
  onLockerCountChange,
  populationSize,
  onPopulationSizeChange,
  maxGenerations,
  onMaxGenerationsChange,
  mutationRate,
  onMutationRateChange,
  crossoverRate,
  onCrossoverRateChange,
  archiveSize,
  onArchiveSizeChange,
  randomSeed,
  onRandomSeedChange,
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
  mcdaPreference = 50,
  onMcdaPreferenceChange,
  onRunMcda,
  paretoSolutionCount = 0,
  isOptimizing = false,
  isCurrentSolutionPareto = false,
  isBestF1 = false,
  isBestF2 = false,
}: ControlPanelProps) {

  const lockerInput = useNumericInput(lockerCount, onLockerCountChange, 1, 20);
  const popInput = useNumericInput(populationSize, onPopulationSizeChange, 10, 300);
  const genInput = useNumericInput(maxGenerations, onMaxGenerationsChange, 1, 5000);
  const archInput = useNumericInput(archiveSize, onArchiveSizeChange, 5, 300);

  const [showAdvanced, setShowAdvanced] = useState(false);
  const safeMcdaPreference = Number.isFinite(mcdaPreference) ? mcdaPreference : 50;
  const safeGenerationCount = Math.max(0, generationCount);
  const safeCurrentGeneration =
    safeGenerationCount > 0
      ? Math.max(0, Math.min(currentGeneration, safeGenerationCount - 1))
      : 0;
  const accessibilityWeight = 100 - safeMcdaPreference;
  const inequityWeight = safeMcdaPreference;
  const canRunMcda = paretoSolutionCount > 0 && !isOptimizing;

  return (
    <aside className="flex h-full flex-col overflow-hidden rounded-[30px] border border-slate-200/60 bg-white p-4 shadow-sm">
      <div className="min-h-0 flex-1 overflow-y-auto pr-2 custom-scrollbar">
        <div>
          <span className="inline-flex rounded-full border border-slate-200/70 bg-white/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            Controls
          </span>
        </div>

          <div className="mt-5 space-y-6">
          <div className="rounded-[22px] border border-slate-200/50 bg-white/60 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Locker Count (k)
                </label>
                <div className="text-[9px] text-slate-400 mt-0.5">min 1, max 20 lockers</div>
              </div>
              <span className="rounded-lg bg-indigo-600 px-2 py-1 text-[11px] font-bold text-white">
                Active: {lockerCount}
              </span>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <input
                type="text"
                inputMode="numeric"
                value={lockerInput.text}
                onChange={(e) => lockerInput.handleChange(e.target.value)}
                onBlur={lockerInput.handleBlur}
                disabled={isOptimizing}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
              />
                      <button
                        type="button"
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
            <div className="flex items-start justify-between gap-3">
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  MCDA Decision Selector
                </label>
                <p className="mt-2 text-[11px] leading-5 text-slate-500">
                  Current Solution browses archive solutions sequentially. MCDA selects the best Pareto solution according to the selected Accessibility-Inequity preference.
                </p>
              </div>
              <span className="shrink-0 rounded-lg bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">
                {paretoSolutionCount} Pareto
              </span>
            </div>

            <div className="mt-4">
              <div className="grid min-h-4 grid-cols-2 gap-3 text-[10px] font-bold tabular-nums text-slate-500">
                <span className="whitespace-nowrap text-left">Accessibility: {accessibilityWeight}%</span>
                <span className="whitespace-nowrap text-right">Inequity: {inequityWeight}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={safeMcdaPreference}
                onChange={(e) => onMcdaPreferenceChange(Number(e.target.value))}
                disabled={isOptimizing || paretoSolutionCount === 0}
                className="mt-3 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-emerald-600 disabled:opacity-50"
              />
              <div className="mt-2 flex justify-between text-[9px] font-semibold uppercase tracking-wider text-slate-400">
                <span>Accessibility</span>
                <span>Equal</span>
                <span>Inequity</span>
              </div>
            </div>

            <button
              type="button"
              onClick={(event) => {
                event.preventDefault();
                event.currentTarget.blur();
                onRunMcda();
              }}
              disabled={!canRunMcda}
              className={`mt-4 h-10 w-full rounded-xl text-xs font-bold text-white shadow-md transition ${
                canRunMcda
                  ? "bg-emerald-600 hover:bg-emerald-700"
                  : "cursor-not-allowed bg-slate-400"
              }`}
            >
              Run MCDA
            </button>
            <p className="mt-2 min-h-[14px] text-[10px] text-slate-400">
              {paretoSolutionCount === 0
                ? "Run optimization to generate Pareto solutions before using MCDA."
                : ""}
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
                    BEST ACCESSIBILITY
                  </span>
                )}
                {isBestF2 && (
                  <span className="rounded-lg bg-emerald-600 px-2 py-1 text-[10px] font-bold text-white shadow-sm">
                    BEST INEQUITY
                  </span>
                )}
                {isCurrentSolutionPareto && !isBestF1 && !isBestF2 && (
                  <span className="rounded-lg bg-emerald-500 px-2 py-1 text-[10px] font-bold text-white animate-pulse">
                    PARETO
                  </span>
                )}
                <span className="rounded-lg bg-slate-900 px-2 py-1 text-[11px] font-bold text-white">
                  #{safeCurrentGeneration + 1}
                </span>
              </div>
            </div>

            <div className="mt-4 flex items-center gap-3">
              <button
                type="button"
                onClick={onPrevGeneration}
                disabled={safeCurrentGeneration === 0}
                aria-label="Previous solution"
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
              >
                ←
              </button>
              
              <input
                type="range"
                min={0}
                max={Math.max(0, safeGenerationCount - 1)}
                value={safeCurrentGeneration}
                onChange={(e) => onGenerationChange(Number(e.target.value))}
                className={`h-1.5 flex-1 cursor-pointer appearance-none rounded-full transition-colors ${
                  isCurrentSolutionPareto ? "bg-emerald-200 accent-emerald-600" : "bg-slate-200 accent-slate-900"
                }`}
              />

              <button
                type="button"
                onClick={onNextGeneration}
                disabled={safeCurrentGeneration >= safeGenerationCount - 1}
                aria-label="Next solution"
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
                type="button"
                onClick={onTogglePlayback}
                aria-label={isPlaying ? "Stop playback" : "Start auto-play"}
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
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex w-full items-center justify-between px-1 text-left"
          >
            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">
              Advanced Developer Options
            </h3>
            <span className="text-slate-400">
              {showAdvanced ? "▲" : "▼"}
            </span>
          </button>

          {showAdvanced && (
            <div className="mt-5 space-y-5 animate-in fade-in slide-in-from-top-2 duration-200">
              <div className="rounded-[22px] border border-slate-200/50 bg-white/60 p-4 shadow-sm">
                <div className="space-y-4">
                  <div>
                    <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Population Size
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={popInput.text}
                      onChange={(e) => popInput.handleChange(e.target.value)}
                      onBlur={popInput.handleBlur}
                      disabled={isOptimizing}
                      className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Max Generations
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={genInput.text}
                      onChange={(e) => genInput.handleChange(e.target.value)}
                      onBlur={genInput.handleBlur}
                      disabled={isOptimizing}
                      className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
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
                        disabled={isOptimizing}
                        className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-slate-200 accent-indigo-600 disabled:opacity-50"
                      />
                      <span className="text-sm font-bold text-slate-700 w-10">
                        {Math.round(mutationRate * 100)}%
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Crossover Rate
                    </label>
                    <div className="mt-2 flex items-center gap-3">
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.01}
                        value={crossoverRate}
                        onChange={(e) => onCrossoverRateChange(Number(e.target.value))}
                        disabled={isOptimizing}
                        className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-slate-200 accent-indigo-600 disabled:opacity-50"
                      />
                      <span className="text-sm font-bold text-slate-700 w-10">
                        {Math.round(crossoverRate * 100)}%
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Archive Size
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={archInput.text}
                      onChange={(e) => archInput.handleChange(e.target.value)}
                      onBlur={archInput.handleBlur}
                      disabled={isOptimizing}
                      className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Random Seed (Optional)
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={randomSeed}
                      onChange={(e) => onRandomSeedChange(e.target.value.replace(/[^0-9]/g, ""))}
                      placeholder="Auto (Random)"
                      disabled={isOptimizing}
                      className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

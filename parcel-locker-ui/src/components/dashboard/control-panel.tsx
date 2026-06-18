"use client";

import { useState, useEffect, useRef } from "react";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  SlidersHorizontal,
} from "lucide-react";

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

const panelCardClass =
  "rounded-lg border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.05)]";
const baseInputClass =
  "h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400";
const stackedInputClass = `mt-2 ${baseInputClass}`;
const iconButtonClass =
  "flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40";

function moveCaretToEnd(input: HTMLInputElement) {
  window.requestAnimationFrame(() => {
    const end = input.value.length;
    input.setSelectionRange(end, end);
  });
}

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

  return { text, handleChange, handleBlur, moveCaretToEnd };
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

  const lockerInput = useNumericInput(lockerCount, onLockerCountChange, 1, 30);
  const popInput = useNumericInput(populationSize, onPopulationSizeChange, 10, 300);
  const genInput = useNumericInput(maxGenerations, onMaxGenerationsChange, 1, 5000);
  const archInput = useNumericInput(archiveSize, onArchiveSizeChange, 5, 300);

  const [showAdvanced, setShowAdvanced] = useState(false);
  const advancedPanelRef = useRef<HTMLDivElement>(null);
  const safeMcdaPreference = Number.isFinite(mcdaPreference) ? mcdaPreference : 50;
  const safeGenerationCount = Math.max(0, generationCount);
  const safeCurrentGeneration =
    safeGenerationCount > 0
      ? Math.max(0, Math.min(currentGeneration, safeGenerationCount - 1))
      : 0;
  const accessibilityWeight = 100 - safeMcdaPreference;
  const inequityWeight = safeMcdaPreference;
  const canRunMcda = paretoSolutionCount > 0 && !isOptimizing;

  useEffect(() => {
    if (!showAdvanced) return;

    const timeoutId = window.setTimeout(() => {
      advancedPanelRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
        inline: "nearest",
      });
    }, 40);

    return () => window.clearTimeout(timeoutId);
  }, [showAdvanced]);

  return (
    <aside className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/80 p-3 shadow-sm">
      <div className="min-h-0 flex-1 overflow-y-auto pr-2 custom-scrollbar">
        <div className="flex items-center justify-between gap-3">
          <span className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 shadow-sm">
            <SlidersHorizontal size={14} />
            Planlama Ayarları
          </span>
        </div>

        <div className="mt-5 space-y-6">
          <div className={panelCardClass}>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Kaç dolap yerleştirilecek?
                </label>
                <div className="text-[9px] text-slate-400 mt-0.5">Planlamak istediğiniz yeni dolap sayısını girin.</div>
              </div>
              <span className="rounded-lg bg-indigo-600 px-2 py-1 text-[11px] font-bold text-white">
                Seçili: {lockerCount}
              </span>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <input
                type="text"
                inputMode="numeric"
                value={lockerInput.text}
                onChange={(e) => lockerInput.handleChange(e.target.value)}
                onFocus={(e) => lockerInput.moveCaretToEnd(e.currentTarget)}
                onClick={(e) => lockerInput.moveCaretToEnd(e.currentTarget)}
                onBlur={lockerInput.handleBlur}
                disabled={isOptimizing}
                className={`${baseInputClass} text-center tabular-nums`}
              />
              <button
                type="button"
                onClick={onShowResults}
                disabled={isOptimizing}
                className={`h-10 whitespace-nowrap rounded-lg px-4 text-xs font-bold text-white shadow-sm transition ${
                  isOptimizing
                    ? "bg-slate-400 cursor-not-allowed"
                    : "bg-indigo-600 hover:bg-indigo-700"
                }`}
              >
                {isOptimizing ? "Öneriler hazırlanıyor..." : "Konum önerilerini oluştur"}
              </button>
            </div>
            <p className="mt-2 text-[10px] text-slate-400">
              * Dolap sayısını değiştirdikten sonra yeni öneriler oluşturabilirsiniz.
            </p>
          </div>

          <div className={panelCardClass}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Öncelik Seçimi
                </label>
                <p className="mt-2 text-[11px] leading-5 text-slate-500">
                  Alternatif öneriler arasından işletme önceliğinize en uygun sonucu seçin.
                </p>
              </div>
              <span className="shrink-0 rounded-lg bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">
                {paretoSolutionCount} alternatif
              </span>
            </div>

            <div className="mt-4">
              <div className="grid min-h-4 grid-cols-2 gap-3 text-[10px] font-bold tabular-nums text-slate-500">
                <span className="whitespace-nowrap text-left">Yakınlık önceliği: {accessibilityWeight}%</span>
                <span className="whitespace-nowrap text-right">Denge önceliği: {inequityWeight}%</span>
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
                <span>Müşteriye Yakınlık</span>
                <span>Dengeli</span>
                <span>Bölgesel Denge</span>
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
              className={`mt-4 h-10 w-full rounded-lg text-xs font-bold text-white shadow-sm transition ${
                canRunMcda
                  ? "bg-emerald-600 hover:bg-emerald-700"
                  : "cursor-not-allowed bg-slate-400"
              }`}
            >
              En uygun öneriyi seç
            </button>
            <p className="mt-2 min-h-[14px] text-[10px] text-slate-400">
              {paretoSolutionCount === 0
                ? "Öncelik seçimini kullanmak için önce konum önerilerini oluşturun."
                : ""}
            </p>
          </div>

          <div className={panelCardClass}>
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Öneri Alternatifleri
              </label>
              <div className="flex flex-wrap items-center justify-end gap-2">
                {isBestF1 && (
                  <span className="rounded-lg bg-blue-500 px-2 py-1 text-[10px] font-bold text-white shadow-sm">
                    YAKINLIK ODAKLI
                  </span>
                )}
                {isBestF2 && (
                  <span className="rounded-lg bg-emerald-600 px-2 py-1 text-[10px] font-bold text-white shadow-sm">
                    DENGE ODAKLI
                  </span>
                )}
                {isCurrentSolutionPareto && !isBestF1 && !isBestF2 && (
                  <span className="rounded-lg bg-emerald-500 px-2 py-1 text-[10px] font-bold text-white animate-pulse">
                    ÖNE ÇIKAN
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
                aria-label="Önceki öneri"
                className={iconButtonClass}
              >
                <ChevronLeft size={16} />
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
                aria-label="Sonraki öneri"
                className={iconButtonClass}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          <div className={panelCardClass}>
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Alternatifleri Otomatik Gez
              </label>
              <button
                type="button"
                onClick={onTogglePlayback}
                aria-label={isPlaying ? "Otomatik oynatmayı durdur" : "Otomatik oynatmayı başlat"}
                className={`flex h-10 w-28 items-center justify-center gap-2 rounded-lg text-xs font-bold transition ${
                  isPlaying 
                    ? "bg-rose-500 text-white shadow-[0_4px_12px_rgba(244,63,94,0.3)]" 
                    : "bg-emerald-500 text-white shadow-[0_4px_12px_rgba(16,185,129,0.3)]"
                }`}
              >
                {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                {isPlaying ? "Durdur" : "Oynat"}
              </button>
            </div>
            
            <div className="mt-4">
              <div className="flex justify-between text-[10px] font-bold text-slate-400">
                <span>Hız</span>
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

        <div className="mt-8 space-y-4" ref={advancedPanelRef}>
          <button
            type="button"
            onClick={() => setShowAdvanced((prev) => !prev)}
            className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-3 text-left shadow-sm transition hover:border-indigo-200 hover:bg-indigo-50/30"
            aria-expanded={showAdvanced}
          >
            <div>
              <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">
                Gelişmiş Teknik Ayarlar
              </h3>
              <p className="mt-1 text-[10px] font-medium normal-case tracking-normal text-slate-400">
                Bu alan yalnızca teknik test ve ince ayar için kullanılır.
              </p>
            </div>
            <ChevronDown
              size={16}
              className={`text-slate-400 transition-transform ${showAdvanced ? "rotate-180" : ""}`}
            />
          </button>

          {showAdvanced && (
            <div className="mt-5 space-y-5 animate-in fade-in slide-in-from-top-2 duration-200">
              <div className={panelCardClass}>
                <div className="space-y-4">
                  <div>
                    <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Popülasyon boyutu
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={popInput.text}
                      onChange={(e) => popInput.handleChange(e.target.value)}
                      onFocus={(e) => popInput.moveCaretToEnd(e.currentTarget)}
                      onClick={(e) => popInput.moveCaretToEnd(e.currentTarget)}
                      onBlur={popInput.handleBlur}
                      disabled={isOptimizing}
                      className={`${stackedInputClass} text-center tabular-nums`}
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Maksimum nesil sayısı
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={genInput.text}
                      onChange={(e) => genInput.handleChange(e.target.value)}
                      onFocus={(e) => genInput.moveCaretToEnd(e.currentTarget)}
                      onClick={(e) => genInput.moveCaretToEnd(e.currentTarget)}
                      onBlur={genInput.handleBlur}
                      disabled={isOptimizing}
                      className={`${stackedInputClass} text-center tabular-nums`}
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Mutasyon oranı
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
                      Çaprazlama oranı
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
                      Arşiv boyutu
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={archInput.text}
                      onChange={(e) => archInput.handleChange(e.target.value)}
                      onFocus={(e) => archInput.moveCaretToEnd(e.currentTarget)}
                      onClick={(e) => archInput.moveCaretToEnd(e.currentTarget)}
                      onBlur={archInput.handleBlur}
                      disabled={isOptimizing}
                      className={`${stackedInputClass} text-center tabular-nums`}
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Rastgelelik tohumu (opsiyonel)
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={randomSeed}
                      onChange={(e) => onRandomSeedChange(e.target.value.replace(/[^0-9]/g, ""))}
                      placeholder="Otomatik (rastgele)"
                      disabled={isOptimizing}
                      className={`${stackedInputClass} text-center tabular-nums`}
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

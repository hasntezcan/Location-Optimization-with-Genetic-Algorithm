"use client";

type ControlPanelProps = {
  lockerCount: number;
  onLockerCountChange: (value: number) => void;
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
};

export function ControlPanel({
  lockerCount,
  onLockerCountChange,
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
}: ControlPanelProps) {
  return (
    <aside className="flex h-full flex-col rounded-[30px] border border-white/60 bg-white/55 p-5 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
      <div>
        <span className="inline-flex rounded-full border border-slate-200/70 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          Controls
        </span>

        <h2 className="mt-4 text-[26px] font-semibold tracking-tight text-slate-900">
          Parcel locker input
        </h2>

        <p className="mt-3 text-sm leading-7 text-slate-600">
          Set the locker count and play the fake genetic algorithm generations.
        </p>
      </div>

      <div className="mt-8 rounded-[24px] border border-slate-200/50 bg-white/60 p-4">
        <label
          htmlFor="locker-count"
          className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500"
        >
          Parcel locker count
        </label>

        <div className="mt-3 relative">
          <input
            id="locker-count"
            type="number"
            min={1}
            max={100}
            value={lockerCount}
            onChange={(e) => onLockerCountChange(Number(e.target.value))}
            className="h-14 w-full rounded-2xl border border-slate-200/70 bg-white/85 px-4 text-base font-medium text-slate-900 outline-none transition duration-300 placeholder:text-slate-400 focus:border-sky-300 focus:bg-white focus:shadow-[0_0_0_4px_rgba(125,211,252,0.18)]"
          />
        </div>
      </div>

      <button
        onClick={onShowResults}
        className="group relative mt-6 h-14 overflow-hidden rounded-2xl border border-slate-900/80 bg-[linear-gradient(135deg,#0f172a_0%,#172554_45%,#0f172a_100%)] px-5 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(15,23,42,0.22)] transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_18px_35px_rgba(15,23,42,0.28)]"
      >
        <span className="absolute inset-0 rounded-2xl opacity-0 transition duration-300 group-hover:opacity-100">
          <span className="button-beam absolute inset-[-2px] rounded-[18px]" />
        </span>

        <span className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.28),_transparent_45%)] opacity-70" />
        <span className="relative z-10">Build fake generations</span>
      </button>

      <div className="mt-8 rounded-[24px] border border-slate-200/50 bg-gradient-to-br from-white/70 to-slate-50/80 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          Generation playback
        </p>

        <div className="mt-4 flex items-center gap-2">
          <button
            onClick={onPrevGeneration}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"
          >
            Prev
          </button>

          <button
            onClick={onTogglePlayback}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white"
          >
            {isPlaying ? "Pause" : "Play"}
          </button>

          <button
            onClick={onNextGeneration}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"
          >
            Next
          </button>
        </div>

        <div className="mt-5">
          <div className="flex items-center justify-between text-xs font-medium text-slate-500">
            <span>Generation</span>
            <span>
              {generationCount > 0 ? currentGeneration + 1 : 0} / {generationCount}
            </span>
          </div>

          <input
            type="range"
            min={0}
            max={Math.max(generationCount - 1, 0)}
            value={currentGeneration}
            onChange={(e) => onGenerationChange(Number(e.target.value))}
            className="mt-3 w-full"
          />
        </div>

        <div className="mt-5">
          <label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Playback speed
          </label>

          <select
            value={playbackSpeed}
            onChange={(e) => onPlaybackSpeedChange(Number(e.target.value))}
            className="mt-3 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
          >
            <option value={1200}>Slow</option>
            <option value={700}>Normal</option>
            <option value={350}>Fast</option>
            <option value={180}>Stress test</option>
          </select>
        </div>
      </div>
    </aside>
  );
}
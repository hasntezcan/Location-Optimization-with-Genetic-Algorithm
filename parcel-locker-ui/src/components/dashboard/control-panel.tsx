"use client";

import { useState } from "react";

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
  const [populationSize, setPopulationSize] = useState(100);
  const [archiveSize, setArchiveSize] = useState(50);
  const [maxGenerations, setMaxGenerations] = useState(200);
  const [crossoverRate, setCrossoverRate] = useState(0.9);
  const [mutationRate, setMutationRate] = useState(0.05);
  const [randomSeed, setRandomSeed] = useState(42);
  const [lambdaValue, setLambdaValue] = useState(0.5);
  const [beta, setBeta] = useState(2);
  const [snapshotInterval, setSnapshotInterval] = useState(10);

  const [tournamentSize, setTournamentSize] = useState(2);
  const [excludeForbiddenPoints, setExcludeForbiddenPoints] = useState(true);
  const [initializationMode, setInitializationMode] = useState("random");
  const [fitnessScalingMode, setFitnessScalingMode] = useState("global");
  const [distanceMatrixMode, setDistanceMatrixMode] = useState("precomputed");

  const [referencePoint, setReferencePoint] = useState("1.1, 1.1");
  const [useGlobalNormalization, setUseGlobalNormalization] = useState(true);

  const [snapshotIndividualType, setSnapshotIndividualType] = useState("best-archive");
  const [simultaneousSolutions, setSimultaneousSolutions] = useState(1);
  const [visualizationMode, setVisualizationMode] = useState("lockers-only");

  return (
    <aside className="flex h-full min-h-0 flex-col overflow-hidden rounded-[30px] border border-white/60 bg-white/55 p-4 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl lg:max-h-[calc(100vh-290px)]">
      <div className="min-h-0 flex-1 overflow-y-auto pr-2">
        <div>
          <span className="inline-flex rounded-full border border-slate-200/70 bg-white/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            Controls
          </span>

          <h2 className="mt-3 text-[22px] font-semibold tracking-tight text-slate-900">
            Parcel locker input
          </h2>

          <p className="mt-2 text-sm leading-6 text-slate-600">
            Set the locker count and play the fake genetic algorithm generations.
          </p>
        </div>

        <div className="mt-6 rounded-[22px] border border-slate-200/50 bg-white/60 p-4">
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
              className="h-12 w-full rounded-2xl border border-slate-200/70 bg-white/85 px-4 text-base font-medium text-slate-900 outline-none transition duration-300 placeholder:text-slate-400 focus:border-sky-300 focus:bg-white focus:shadow-[0_0_0_4px_rgba(125,211,252,0.18)]"
            />
          </div>
        </div>

        <button
          onClick={onShowResults}
          className="group relative mt-5 h-12 w-full overflow-hidden rounded-2xl border border-slate-900/80 bg-[linear-gradient(135deg,#0f172a_0%,#172554_45%,#0f172a_100%)] px-5 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(15,23,42,0.22)] transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_18px_35px_rgba(15,23,42,0.28)]"
        >
          <span className="absolute inset-0 rounded-2xl opacity-0 transition duration-300 group-hover:opacity-100">
            <span className="button-beam absolute inset-[-2px] rounded-[18px]" />
          </span>

          <span className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.28),_transparent_45%)] opacity-70" />
          <span className="relative z-10">Build fake generations</span>
        </button>

        <div className="mt-6 rounded-[22px] border border-slate-200/50 bg-gradient-to-br from-white/70 to-slate-50/80 p-4">
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

          <div className="mt-4">
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

          <div className="mt-4">
            <label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Playback speed
            </label>

            <select
              value={playbackSpeed}
              onChange={(e) => onPlaybackSpeedChange(Number(e.target.value))}
              className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
            >
              <option value={1200}>Slow</option>
              <option value={700}>Normal</option>
              <option value={350}>Fast</option>
              <option value={180}>Stress test</option>
            </select>
          </div>
        </div>

        <div className="mt-6 rounded-[22px] border border-slate-200/50 bg-white/60 p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Test area
              </p>
              <h3 className="mt-1.5 text-base font-semibold text-slate-900">
                GA / SPEA2 parameters
              </h3>
            </div>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Mock inputs
            </span>
          </div>

          <div className="mt-5 space-y-5">
            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Core parameters
              </p>

              <div className="mt-3 grid grid-cols-1 gap-3">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Population size
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={populationSize}
                    onChange={(e) => setPopulationSize(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Archive size
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={archiveSize}
                    onChange={(e) => setArchiveSize(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Max generations
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={maxGenerations}
                    onChange={(e) => setMaxGenerations(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Crossover rate
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.01}
                    value={crossoverRate}
                    onChange={(e) => setCrossoverRate(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Mutation rate
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.01}
                    value={mutationRate}
                    onChange={(e) => setMutationRate(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Random seed
                  </label>
                  <input
                    type="number"
                    value={randomSeed}
                    onChange={(e) => setRandomSeed(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Lambda
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.01}
                    value={lambdaValue}
                    onChange={(e) => setLambdaValue(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Beta
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    value={beta}
                    onChange={(e) => setBeta(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Snapshot interval
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={snapshotInterval}
                    onChange={(e) => setSnapshotInterval(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>
              </div>
            </section>

            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Advanced settings
              </p>

              <div className="mt-3 grid grid-cols-1 gap-3">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Tournament size
                  </label>
                  <input
                    type="number"
                    min={2}
                    value={tournamentSize}
                    onChange={(e) => setTournamentSize(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Forbidden points
                  </label>
                  <select
                    value={excludeForbiddenPoints ? "exclude" : "include"}
                    onChange={(e) => setExcludeForbiddenPoints(e.target.value === "exclude")}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  >
                    <option value="exclude">Exclude forbidden points</option>
                    <option value="include">Include all points</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Initialization mode
                  </label>
                  <select
                    value={initializationMode}
                    onChange={(e) => setInitializationMode(e.target.value)}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  >
                    <option value="random">Random</option>
                    <option value="filtered">Filtered</option>
                    <option value="seeded">Seeded</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Fitness scaling
                  </label>
                  <select
                    value={fitnessScalingMode}
                    onChange={(e) => setFitnessScalingMode(e.target.value)}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  >
                    <option value="global">Global normalization</option>
                    <option value="local">Per-run normalization</option>
                    <option value="none">No scaling</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Distance matrix mode
                  </label>
                  <select
                    value={distanceMatrixMode}
                    onChange={(e) => setDistanceMatrixMode(e.target.value)}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  >
                    <option value="precomputed">Precomputed NxN matrix</option>
                    <option value="decay">Decay matrix</option>
                    <option value="runtime">Runtime calculation</option>
                  </select>
                </div>
              </div>
            </section>

            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Hypervolume settings
              </p>

              <div className="mt-3 grid grid-cols-1 gap-3">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Reference point (W)
                  </label>
                  <input
                    type="text"
                    value={referencePoint}
                    onChange={(e) => setReferencePoint(e.target.value)}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                    placeholder="1.1, 1.1"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Objective normalization
                  </label>
                  <select
                    value={useGlobalNormalization ? "global" : "custom"}
                    onChange={(e) => setUseGlobalNormalization(e.target.value === "global")}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  >
                    <option value="global">Use global normalization</option>
                    <option value="custom">Custom / flexible</option>
                  </select>
                </div>
              </div>
            </section>

            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Map animation settings
              </p>

              <div className="mt-3 grid grid-cols-1 gap-3">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Snapshot individual type
                  </label>
                  <select
                    value={snapshotIndividualType}
                    onChange={(e) => setSnapshotIndividualType(e.target.value)}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  >
                    <option value="best-archive">Best archive solution</option>
                    <option value="pareto-sample">Pareto front sample</option>
                    <option value="population-sample">Population sample</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Simultaneous solutions
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={simultaneousSolutions}
                    onChange={(e) => setSimultaneousSolutions(Number(e.target.value))}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Visualization mode
                  </label>
                  <select
                    value={visualizationMode}
                    onChange={(e) => setVisualizationMode(e.target.value)}
                    className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700"
                  >
                    <option value="lockers-only">Lockers only</option>
                    <option value="lockers-demand">Lockers + demand heat</option>
                    <option value="lockers-coverage">Lockers + coverage area</option>
                  </select>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </aside>
  );
}
import type { GenerationSnapshot, Locker } from "@/lib/types";

type LockerDetailPanelProps = {
  locker: Locker;
  generation: GenerationSnapshot;
};

export function LockerDetailPanel({
  locker,
  generation,
}: LockerDetailPanelProps) {
  return (
    <aside className="flex h-full flex-col rounded-[30px] border border-white/60 bg-white/55 p-5 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
      <div>
        <span className="inline-flex rounded-full border border-slate-200/70 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          Selected locker
        </span>

        <h2 className="mt-4 text-[26px] font-semibold tracking-tight text-slate-900">
          {locker.name}
        </h2>

        <p className="mt-3 text-sm leading-7 text-slate-600">
          Location details and active generation metrics for the selected parcel locker.
        </p>
      </div>

      <div className="mt-8 rounded-[24px] border border-slate-200/50 bg-gradient-to-br from-white/75 to-slate-50/85 p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Overview
        </p>

        <div className="mt-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-slate-500">Neighborhood</p>
            <p className="mt-1 text-xl font-semibold tracking-tight text-slate-900">
              {locker.neighborhood}
            </p>
          </div>

          <div className="rounded-2xl border border-sky-100 bg-sky-50/80 px-3 py-2 text-right">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-700">
              Generation
            </p>
            <p className="mt-1 text-sm font-medium text-slate-800">
              {generation.generation + 1}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-4">
        <div className="rounded-[24px] border border-slate-200/50 bg-white/65 p-4 transition duration-300 hover:bg-white/80 hover:shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            Latitude
          </p>
          <p className="mt-3 text-xl font-semibold tracking-tight text-slate-900">
            {locker.lat}
          </p>
        </div>

        <div className="rounded-[24px] border border-slate-200/50 bg-white/65 p-4 transition duration-300 hover:bg-white/80 hover:shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            Longitude
          </p>
          <p className="mt-3 text-xl font-semibold tracking-tight text-slate-900">
            {locker.lng}
          </p>
        </div>

        <div className="rounded-[24px] border border-slate-200/50 bg-white/65 p-4 transition duration-300 hover:bg-white/80 hover:shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            Accessibility
          </p>
          <p className="mt-3 text-xl font-semibold tracking-tight text-slate-900">
            {generation.metrics.accessibility}
          </p>
        </div>

        <div className="rounded-[24px] border border-slate-200/50 bg-white/65 p-4 transition duration-300 hover:bg-white/80 hover:shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            Equity
          </p>
          <p className="mt-3 text-xl font-semibold tracking-tight text-slate-900">
            {generation.metrics.equity}
          </p>
        </div>

        <div className="rounded-[24px] border border-slate-200/50 bg-white/65 p-4 transition duration-300 hover:bg-white/80 hover:shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            Fitness
          </p>
          <p className="mt-3 text-xl font-semibold tracking-tight text-slate-900">
            {generation.metrics.fitness}
          </p>
        </div>
      </div>
    </aside>
  );
}
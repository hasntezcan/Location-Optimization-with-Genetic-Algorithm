"use client";

import type { Locker } from "@/lib/types";

type LockerStripProps = {
  lockers: Locker[];
  selectedLockerId: string | null;
  onSelectLocker: (locker: Locker | null) => void;
  isPareto?: boolean;
};

export function LockerStrip({
  lockers,
  selectedLockerId,
  onSelectLocker,
  isPareto,
}: LockerStripProps) {
  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {lockers.map((locker, index) => {
        const isSelected = locker.id === selectedLockerId;

        return (
          <button
            key={locker.id}
            onClick={() => onSelectLocker(isSelected ? null : locker)}
            className={`group relative min-w-[190px] overflow-hidden rounded-[24px] border px-4 py-4 text-left transition duration-300 ${
              isSelected
                ? isPareto 
                  ? "border-emerald-500 bg-[linear-gradient(135deg,#064e3b_0%,#065f46_48%,#064e3b_100%)] text-white shadow-[0_16px_32px_rgba(5,150,105,0.18)]"
                  : "border-slate-900/80 bg-[linear-gradient(135deg,#0f172a_0%,#172554_48%,#0f172a_100%)] text-white shadow-[0_16px_32px_rgba(15,23,42,0.18)]"
                : "border-white/70 bg-white/65 text-slate-900 shadow-[0_10px_24px_rgba(15,23,42,0.05)] backdrop-blur-xl hover:-translate-y-0.5 hover:border-sky-200 hover:bg-white/85 hover:shadow-[0_16px_30px_rgba(56,189,248,0.10)]"
            }`}
          >
            <span
              className={`absolute inset-0 transition duration-300 ${
                isSelected
                  ? "bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.16),_transparent_42%)]"
                  : "bg-[radial-gradient(circle_at_top_right,_rgba(186,230,253,0.35),_transparent_45%)] opacity-0 group-hover:opacity-100"
              }`}
            />

            <div className="relative z-10 flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold tracking-tight">{locker.name}</p>
                <p
                  className={`mt-1 text-xs font-medium ${
                    isSelected ? "text-slate-200" : "text-slate-500"
                  }`}
                >
                  {locker.neighborhood}
                </p>
              </div>

              <div
                className={`flex h-9 w-9 items-center justify-center rounded-full border text-xs font-semibold transition ${
                  isSelected
                    ? "border-white/20 bg-white/10 text-white"
                    : "border-slate-200/80 bg-white/80 text-slate-600 group-hover:border-sky-200 group-hover:text-sky-700"
                }`}
              >
                {String(index + 1).padStart(2, "0")}
              </div>
            </div>

            <div className="relative z-10 mt-4 flex items-center justify-between">
              <span
                className={`text-[11px] font-semibold uppercase tracking-[0.18em] ${
                  isSelected ? "text-slate-300" : "text-slate-400"
                }`}
              >
                Önerilen dolap
              </span>

              <span
                className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold transition ${
                  isSelected
                    ? "bg-white/12 text-white"
                    : "bg-slate-100/90 text-slate-600 group-hover:bg-sky-50 group-hover:text-sky-700"
                }`}
              >
                {isSelected ? "Seçili" : "Görüntüle"}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

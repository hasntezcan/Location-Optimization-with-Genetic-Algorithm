import type { ArchiveSolution, Locker } from "@/lib/types";

type LockerDetailPanelProps = {
  locker: Locker;
  solution: ArchiveSolution;
  onClose: () => void;
};

export function LockerDetailPanel({
  locker,
  solution,
  onClose,
}: LockerDetailPanelProps) {
  const hasValidCoordinates =
    Number.isFinite(locker.lat) && Number.isFinite(locker.lng);
  const mapsUrl = hasValidCoordinates
    ? `https://www.google.com/maps/search/?api=1&query=${locker.lat},${locker.lng}`
    : null;

  return (
    <aside className="flex h-full flex-col overflow-hidden rounded-[30px] border border-white/60 bg-white/55 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
      <div className="flex items-center justify-between p-5 pb-2">
        <span className="inline-flex rounded-full border border-slate-200/70 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          Seçili öneri noktası
        </span>
        <button 
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-white shadow-lg transition hover:bg-slate-800 hover:scale-110"
          title="Alternatiflere dön"
        >
          <span className="text-lg">✕</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 pb-6 custom-scrollbar">
        <div>
          <h2 className="mt-4 text-[26px] font-semibold tracking-tight text-slate-900">
            {locker.name}
          </h2>

          <p className="mt-3 text-sm leading-7 text-slate-600">
            Bu önerideki konum bilgileri ve karar metrikleri.
          </p>
        </div>

        <div className="mt-8 rounded-[24px] border border-slate-200/50 bg-gradient-to-br from-white/75 to-slate-50/85 p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Genel bakış
          </p>

          <div className="mt-4 flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-500">Mahalle</p>
              <p className="mt-1 text-xl font-semibold tracking-tight text-slate-900">
                {locker.neighborhood}
              </p>
            </div>

            <div className="rounded-2xl border border-sky-100 bg-sky-50/80 px-3 py-2 text-right">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-700">
                Öneri No
              </p>
              <p className="mt-1 text-sm font-medium text-slate-800">
                #{solution.id}
              </p>
            </div>
          </div>

          <div className="mt-5">
            {mapsUrl ? (
              <a
                href={mapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex w-full items-center justify-center rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-800 shadow-[0_10px_24px_rgba(14,165,233,0.08)] transition hover:border-sky-300 hover:bg-sky-100"
              >
                Google Haritalar&apos;da görüntüle
              </a>
            ) : (
              <div className="rounded-2xl border border-slate-200 bg-white/70 px-4 py-3 text-sm font-medium text-slate-500">
                Konum koordinatları bulunamadı
              </div>
            )}
          </div>
        </div>

        {hasValidCoordinates ? (
          <div className="mt-4 rounded-[20px] border border-slate-200/40 bg-white/45 px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Koordinatlar
            </p>
            <p className="mt-2 break-words text-xs font-medium tabular-nums text-slate-500">
              {locker.lat.toFixed(6)}, {locker.lng.toFixed(6)}
            </p>
          </div>
        ) : null}

        <div className="mt-6 grid gap-4">
          <div className="rounded-[24px] border border-slate-200/50 bg-white/65 p-4 transition duration-300 hover:bg-white/80 hover:shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Müşteriye yakınlık
            </p>
            <p className="mt-3 text-xl font-semibold tracking-tight text-slate-900">
              {solution.metrics.accessibility.toFixed(4)}
            </p>
          </div>

          <div className="rounded-[24px] border border-slate-200/50 bg-white/65 p-4 transition duration-300 hover:bg-white/80 hover:shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Bölgesel denge
            </p>
            <p className="mt-3 text-xl font-semibold tracking-tight text-slate-900">
              {solution.metrics.equity.toFixed(4)}
            </p>
          </div>

          <div className="rounded-[24px] border border-slate-200/50 bg-white/65 p-4 transition duration-300 hover:bg-white/80 hover:shadow-[0_10px_24px_rgba(15,23,42,0.05)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Öneri skoru
            </p>
            <p className="mt-3 text-xl font-semibold tracking-tight text-slate-900">
              {solution.metrics.fitness.toFixed(4)}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}

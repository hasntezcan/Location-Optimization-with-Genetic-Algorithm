"use client";
import { memo, useEffect, useMemo, useRef } from "react";

import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  Pane,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type {
  CandidatePoint,
  ArchiveSolution,
  Locker,
} from "@/lib/types";
import type { CircleMarker as LeafletCircleMarker } from "leaflet";

const TARGET_SELECTION_ZOOM = 14;

const boundaryStyle = () => ({
  color: "#0f172a",
  weight: 2,
  fillColor: "#cbd5e1",
  fillOpacity: 0.06,
});

function FlyToLocker({ locker }: { locker: Locker | null }) {
  const map = useMap();
  const lastFocusedRef = useRef<string | null>(null);
  const lockerId = locker?.id;
  const lockerLat = locker?.lat;
  const lockerLng = locker?.lng;

  useEffect(() => {
    if (
      !lockerId ||
      typeof lockerLat !== "number" ||
      typeof lockerLng !== "number" ||
      !Number.isFinite(lockerLat) ||
      !Number.isFinite(lockerLng)
    ) {
      return;
    }

    const focusKey = `${lockerId}:${lockerLat}:${lockerLng}`;
    if (lastFocusedRef.current === focusKey) return;
    lastFocusedRef.current = focusKey;

    const target: [number, number] = [lockerLat, lockerLng];
    const targetZoom = Math.max(map.getZoom(), TARGET_SELECTION_ZOOM);

    map.flyTo(target, targetZoom, { duration: 0.8 });
  }, [lockerId, lockerLat, lockerLng, map]);

  return null;
}

const BoundaryLayer = memo(function BoundaryLayer({
  boundary,
}: {
  boundary: GeoJSON.FeatureCollection | null;
}) {
  if (!boundary) return null;

  return <GeoJSON data={boundary} pane="boundary" style={boundaryStyle} />;
});

const ExistingLockerMarkers = memo(function ExistingLockerMarkers({
  candidates,
}: {
  candidates: CandidatePoint[];
}) {
  return (
    <>
      {candidates.map((candidate) => (
        <CircleMarker
          key={`existing-${candidate.id}`}
          center={[candidate.lat, candidate.lng]}
          radius={candidate.existingLockerCount > 1 ? 7 : 5}
          pane="existingLockers"
          pathOptions={{
            color: "#9f1239",
            fillColor: "#e11d48",
            fillOpacity: 0.85,
            weight: 1.5,
          }}
        >
          <Popup>
            <div className="locker-popup space-y-1">
              <p className="text-[13px] font-semibold text-rose-700 leading-tight">
                Mevcut dolap
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
                {candidate.neighborhood}
              </p>
              <div className="grid grid-cols-2 gap-1.5 pt-1">
                <div className="rounded-lg bg-rose-50 px-2 py-1.5 text-center">
                  <p className="text-[8px] font-semibold uppercase tracking-wider text-rose-400">Toplam sayı</p>
                  <p className="text-[10px] font-bold text-rose-700">{candidate.existingLockerCount}</p>
                </div>
                <div className="rounded-lg bg-slate-50 px-2 py-1.5 text-center">
                  <p className="text-[8px] font-semibold uppercase tracking-wider text-slate-400">Aday ID</p>
                  <p className="text-[10px] font-medium text-slate-700">{candidate.id}</p>
                </div>
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  );
});

const CandidateMarkers = memo(function CandidateMarkers({
  candidates,
  activeIds,
}: {
  candidates: CandidatePoint[];
  activeIds: Set<string>;
}) {
  return (
    <>
      {candidates.map((candidate) => {
        if (!Number.isFinite(candidate.lat) || !Number.isFinite(candidate.lng)) return null;
        const isActive = activeIds.has(candidate.id);
        if (isActive) return null;

        return (
          <CircleMarker
            key={`candidate-${candidate.id}`}
            center={[candidate.lat, candidate.lng]}
            radius={2}
            pane="candidates"
            pathOptions={{
              color: "#94a3b8",
              fillColor: "#94a3b8",
              fillOpacity: 0.18,
              weight: 0,
            }}
          />
        );
      })}
    </>
  );
});

type LockerMapProps = {
  candidates: CandidatePoint[];
  boundary: GeoJSON.FeatureCollection | null;
  lockers: Locker[];
  selectedLocker: Locker | null;
  onSelectLocker: (locker: Locker | null) => void;
  currentGeneration: ArchiveSolution;
};

export function LockerMap({
  candidates,
  boundary,
  lockers,
  selectedLocker,
  onSelectLocker,
  currentGeneration,
}: LockerMapProps) {
  const lockerMarkerRefs = useRef(new Map<string, LeafletCircleMarker>());
  const safeLockers = useMemo(
    () => lockers.filter((locker) => Number.isFinite(locker.lat) && Number.isFinite(locker.lng)),
    [lockers]
  );
  const safeSelectedLocker =
    selectedLocker && Number.isFinite(selectedLocker.lat) && Number.isFinite(selectedLocker.lng)
      ? selectedLocker
      : null;
  const activeIds = useMemo(
    () => new Set(safeLockers.map((locker) => locker.id)),
    [safeLockers]
  );
  const selectedLockerId = safeSelectedLocker?.id ?? null;

  const existingLockerCandidates = useMemo(() => {
    return candidates.filter(
      (candidate) =>
        candidate.existingLockerCount > 0 &&
        Number.isFinite(candidate.lat) &&
        Number.isFinite(candidate.lng)
    );
  }, [candidates]);

  useEffect(() => {
    lockerMarkerRefs.current.forEach((marker) => marker.closePopup());

    if (!selectedLockerId) return;

    lockerMarkerRefs.current.get(selectedLockerId)?.openPopup();
  }, [selectedLockerId]);

  if (typeof window === "undefined") {
    return (
      <div className="h-full min-h-[350px] rounded-[30px] border border-white/60 bg-white/55 p-3 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
        <div className="flex h-full items-center justify-center rounded-[26px] border border-slate-200/40 bg-white/55">
          <p className="text-sm text-slate-500">Harita yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-[350px] rounded-[30px] border border-white/60 bg-white/55 p-3 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
      <div className="relative h-full overflow-hidden rounded-[26px] border border-slate-200/40 bg-white/55">
        <div className="pointer-events-none absolute inset-x-0 top-0 z-[500] h-24 bg-gradient-to-b from-white/50 to-transparent" />

        <div className="absolute bottom-4 left-4 z-[600] max-w-[200px] rounded-2xl border border-white/70 bg-white/72 px-4 py-3 shadow-[0_10px_25px_rgba(15,23,42,0.08)] backdrop-blur-xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Seçili öneri
          </p>
          <div className="mt-1 flex items-center gap-2">
            <p className="text-sm font-semibold text-slate-900">
              Öneri #{currentGeneration.id}
            </p>
            {currentGeneration.isPareto && (
              <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                Uygun alternatif
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-600">
            {safeLockers.length} önerilen dolap
          </p>
          <div className="mt-2 flex flex-col gap-1">
            <div className="flex items-center gap-1.5"><div className="h-2.5 w-2.5 rounded-full bg-blue-600 border border-blue-900/30"></div><span className="text-[9px] text-slate-500">Önerilen dolap</span></div>
            <div className="flex items-center gap-1.5"><div className="h-2.5 w-2.5 rounded-full bg-rose-500 border border-rose-800/30"></div><span className="text-[9px] text-slate-500">Mevcut dolap</span></div>
            <div className="flex items-center gap-1.5"><div className="h-2 w-2 rounded-full bg-slate-400/30"></div><span className="text-[9px] text-slate-500">Aday nokta</span></div>
          </div>
        </div>

        {safeSelectedLocker ? (
          <div className="absolute bottom-4 right-4 z-[600] max-w-[180px] rounded-2xl border border-white/70 bg-white/72 px-4 py-3 shadow-[0_10px_25px_rgba(15,23,42,0.08)] backdrop-blur-xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Seçili öneri noktası
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-900">
              {safeSelectedLocker.name}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {safeSelectedLocker.neighborhood}
            </p>
          </div>
        ) : null}

        <MapContainer
          center={[40.9833, 29.0667]}
          zoom={13}
          scrollWheelZoom
          preferCanvas={true}
          className="h-full w-full"
        >
          <Pane name="boundary" style={{ zIndex: 200 }} />
          <Pane name="candidates" style={{ zIndex: 300 }} />
          <Pane name="existingLockers" style={{ zIndex: 400 }} />
          <Pane name="active" style={{ zIndex: 500 }} />

          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

          <FlyToLocker locker={safeSelectedLocker} />

          <BoundaryLayer boundary={boundary} />

          <ExistingLockerMarkers candidates={existingLockerCandidates} />

          <CandidateMarkers candidates={candidates} activeIds={activeIds} />

          {safeLockers.map((locker, index) => {
            const isSelected = locker.id === safeSelectedLocker?.id;

            return (
              <CircleMarker
                key={locker.id}
                ref={(marker) => {
                  if (marker) {
                    lockerMarkerRefs.current.set(locker.id, marker);
                  } else {
                    lockerMarkerRefs.current.delete(locker.id);
                  }
                }}
                center={[locker.lat, locker.lng]}
                radius={isSelected ? 10 : 7}
                pane="active"
                eventHandlers={{ click: () => onSelectLocker(locker) }}
                pathOptions={{
                  color: isSelected ? "#020617" : "#1e3a8a",
                  fillColor: isSelected ? "#020617" : "#2563eb",
                  fillOpacity: 0.95,
                  weight: isSelected ? 3 : 2,
                }}
              >
                <Popup>
                  <div className="locker-popup space-y-1">
                    <p className="text-[13px] font-semibold text-slate-900 leading-tight">
                      {locker.name}
                    </p>
                    <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
                      {locker.neighborhood}
                    </p>
                    <div className="grid grid-cols-3 gap-1.5 pt-1">
                      <div className="rounded-lg bg-slate-50 px-2 py-1.5 text-center">
                        <p className="text-[8px] font-semibold uppercase tracking-wider text-slate-400">Enlem</p>
                        <p className="text-[10px] font-medium text-slate-700 mt-0.5">{locker.lat.toFixed(4)}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-2 py-1.5 text-center">
                        <p className="text-[8px] font-semibold uppercase tracking-wider text-slate-400">Boylam</p>
                        <p className="text-[10px] font-medium text-slate-700 mt-0.5">{locker.lng.toFixed(4)}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-2 py-1.5 text-center">
                        <p className="text-[8px] font-semibold uppercase tracking-wider text-slate-400">Sıra</p>
                        <p className="text-[10px] font-medium text-slate-700 mt-0.5">{String(index + 1).padStart(2, "0")}</p>
                      </div>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}

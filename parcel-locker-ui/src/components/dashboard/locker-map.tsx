"use client";

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
  GenerationSnapshot,
  Locker,
} from "@/lib/types";

function FlyToLocker({ locker }: { locker: Locker }) {
  const map = useMap();
  map.flyTo([locker.lat, locker.lng], 14, { duration: 1.1 });
  return null;
}

type LockerMapProps = {
  candidates: CandidatePoint[];
  boundary: GeoJSON.FeatureCollection | null;
  lockers: Locker[];
  selectedLocker: Locker;
  onSelectLocker: (locker: Locker) => void;
  currentGeneration: GenerationSnapshot;
  previousGeneration: GenerationSnapshot | null;
};

export function LockerMap({
  candidates,
  boundary,
  lockers,
  selectedLocker,
  onSelectLocker,
  currentGeneration,
  previousGeneration,
}: LockerMapProps) {
  const activeIds = new Set(lockers.map((locker) => locker.id));
  const previousIds = new Set(
    previousGeneration?.lockers.map((locker) => locker.id) ?? []
  );

  return (
    <div className="h-full rounded-[30px] border border-white/60 bg-white/55 p-3 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
      <div className="relative h-full overflow-hidden rounded-[26px] border border-slate-200/40 bg-white/55">
        <div className="pointer-events-none absolute inset-x-0 top-0 z-[500] h-24 bg-gradient-to-b from-white/50 to-transparent" />

        <div className="absolute bottom-4 left-4 z-[600] rounded-2xl border border-white/70 bg-white/72 px-4 py-3 shadow-[0_10px_25px_rgba(15,23,42,0.08)] backdrop-blur-xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Active generation
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-900">
            Generation {currentGeneration.generation + 1}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {lockers.length} visible lockers
          </p>
        </div>

        <div className="absolute bottom-4 right-4 z-[600] rounded-2xl border border-white/70 bg-white/72 px-4 py-3 shadow-[0_10px_25px_rgba(15,23,42,0.08)] backdrop-blur-xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Active selection
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-900">
            {selectedLocker.name}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {selectedLocker.neighborhood}
          </p>
        </div>

        <MapContainer
          center={[40.9833, 29.0667]}
          zoom={13}
          scrollWheelZoom
          preferCanvas={true}
          className="h-full w-full"
        >
          <Pane name="boundary" style={{ zIndex: 200 }} />
          <Pane name="candidates" style={{ zIndex: 300 }} />
          <Pane name="previous" style={{ zIndex: 400 }} />
          <Pane name="active" style={{ zIndex: 500 }} />

          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

          <FlyToLocker locker={selectedLocker} />

          {boundary ? (
            <GeoJSON
              data={boundary}
              pane="boundary"
              style={() => ({
                color: "#0f172a",
                weight: 2,
                fillColor: "#cbd5e1",
                fillOpacity: 0.06,
              })}
            />
          ) : null}

          {candidates.map((candidate) => {
            const isActive = activeIds.has(candidate.id);
            const isPrevious = previousIds.has(candidate.id);

            if (isActive || isPrevious) return null;

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

          {previousGeneration?.lockers.map((locker) => {
            const stillActive = activeIds.has(locker.id);
            if (stillActive) return null;

            return (
              <CircleMarker
                key={`previous-${locker.id}`}
                center={[locker.lat, locker.lng]}
                radius={7}
                pane="previous"
                pathOptions={{
                  color: "#cbd5e1",
                  fillColor: "#cbd5e1",
                  fillOpacity: 0.2,
                  weight: 1,
                }}
              />
            );
          })}

          {lockers.map((locker, index) => {
            const isSelected = locker.id === selectedLocker.id;
            const existedBefore = previousIds.has(locker.id);

            return (
              <CircleMarker
                key={locker.id}
                center={[locker.lat, locker.lng]}
                radius={isSelected ? 10 : 7}
                pane="active"
                eventHandlers={{ click: () => onSelectLocker(locker) }}
                pathOptions={{
                  color: isSelected ? "#020617" : "#1e3a8a",
                  fillColor: isSelected ? "#020617" : existedBefore ? "#2563eb" : "#7c3aed",
                  fillOpacity: 0.95,
                  weight: isSelected ? 3 : 2,
                }}
              >
                <Popup>
                  <div className="min-w-[200px] space-y-3 py-1">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {locker.name}
                      </p>
                      <p className="mt-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                        {locker.neighborhood}
                      </p>
                    </div>

                    <div className="grid gap-2">
                      <div className="rounded-xl border border-slate-200/80 bg-slate-50/80 px-3 py-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                          Latitude
                        </p>
                        <p className="mt-1 text-sm font-medium text-slate-800">
                          {locker.lat}
                        </p>
                      </div>

                      <div className="rounded-xl border border-slate-200/80 bg-slate-50/80 px-3 py-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                          Longitude
                        </p>
                        <p className="mt-1 text-sm font-medium text-slate-800">
                          {locker.lng}
                        </p>
                      </div>

                      <div className="rounded-xl border border-slate-200/80 bg-slate-50/80 px-3 py-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                          State
                        </p>
                        <p className="mt-1 text-sm font-medium text-slate-800">
                          {existedBefore ? "Persisting from previous generation" : "New in this generation"}
                        </p>
                      </div>

                      <div className="rounded-xl border border-slate-200/80 bg-slate-50/80 px-3 py-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                          Order
                        </p>
                        <p className="mt-1 text-sm font-medium text-slate-800">
                          {String(index + 1).padStart(2, "0")}
                        </p>
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
"use client";
import { useMemo } from "react";

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

function FlyToLocker({ locker }: { locker: Locker | null }) {
  const map = useMap();

  if (locker) {
    map.flyTo([locker.lat, locker.lng], 14, { duration: 1.1 });
  }

  return null;
}

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
  const activeIds = new Set(lockers.map((locker) => locker.id));

  // Cluster existing lockers by neighborhood so they don't look like a grid
  const existingClusters = useMemo(() => {
    const clusters: Record<string, { latSum: number; lngSum: number; count: number; lockerCount: number; pop: number }> = {};
    
    candidates.forEach((c) => {
      if (c.lockerCount > 0) {
        if (!clusters[c.neighborhood]) {
          clusters[c.neighborhood] = { latSum: 0, lngSum: 0, count: 0, lockerCount: 0, pop: 0 };
        }
        clusters[c.neighborhood].latSum += c.lat;
        clusters[c.neighborhood].lngSum += c.lng;
        clusters[c.neighborhood].count += 1;
        clusters[c.neighborhood].lockerCount += c.lockerCount;
        clusters[c.neighborhood].pop += c.population;
      }
    });

    return Object.entries(clusters).map(([neighborhood, data]) => ({
      id: `existing-cluster-${neighborhood}`,
      neighborhood,
      lat: data.latSum / data.count,
      lng: data.lngSum / data.count,
      lockerCount: data.lockerCount,
      population: data.pop,
      gridPoints: data.count
    }));
  }, [candidates]);

  return (
    <div className="h-full min-h-[350px] rounded-[30px] border border-white/60 bg-white/55 p-3 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
      <div className="relative h-full overflow-hidden rounded-[26px] border border-slate-200/40 bg-white/55">
        <div className="pointer-events-none absolute inset-x-0 top-0 z-[500] h-24 bg-gradient-to-b from-white/50 to-transparent" />

        <div className="absolute bottom-4 left-4 z-[600] max-w-[200px] rounded-2xl border border-white/70 bg-white/72 px-4 py-3 shadow-[0_10px_25px_rgba(15,23,42,0.08)] backdrop-blur-xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Archive solution
          </p>
          <div className="mt-1 flex items-center gap-2">
            <p className="text-sm font-semibold text-slate-900">
              Solution #{currentGeneration.id}
            </p>
            {currentGeneration.isPareto && (
              <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                Pareto Front
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-600">
            {lockers.length} visible lockers
          </p>
          <div className="mt-2 flex flex-col gap-1">
            <div className="flex items-center gap-1.5"><div className="h-2.5 w-2.5 rounded-full bg-blue-600 border border-blue-900/30"></div><span className="text-[9px] text-slate-500">Proposed</span></div>
            <div className="flex items-center gap-1.5"><div className="h-2.5 w-2.5 rounded-full bg-rose-500 border border-rose-800/30"></div><span className="text-[9px] text-slate-500">Existing</span></div>
            <div className="flex items-center gap-1.5"><div className="h-2 w-2 rounded-full bg-slate-400/30"></div><span className="text-[9px] text-slate-500">Candidates</span></div>
          </div>
        </div>

        {selectedLocker ? (
          <div className="absolute bottom-4 right-4 z-[600] max-w-[180px] rounded-2xl border border-white/70 bg-white/72 px-4 py-3 shadow-[0_10px_25px_rgba(15,23,42,0.08)] backdrop-blur-xl">
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

          {existingClusters.map((cluster) => (
            <CircleMarker
              key={cluster.id}
              center={[cluster.lat, cluster.lng]}
              radius={5}
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
                    Existing Lockers
                  </p>
                  <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
                    {cluster.neighborhood}
                  </p>
                  <div className="grid grid-cols-2 gap-1.5 pt-1">
                    <div className="rounded-lg bg-rose-50 px-2 py-1.5 text-center">
                      <p className="text-[8px] font-semibold uppercase tracking-wider text-rose-400">Total Count</p>
                      <p className="text-[10px] font-bold text-rose-700">{cluster.lockerCount}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 px-2 py-1.5 text-center">
                      <p className="text-[8px] font-semibold uppercase tracking-wider text-slate-400">Grid Area</p>
                      <p className="text-[10px] font-medium text-slate-700">{cluster.gridPoints} cells</p>
                    </div>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          {candidates.map((candidate) => {
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

          {lockers.map((locker, index) => {
            const isSelected = locker.id === selectedLocker?.id;

            return (
              <CircleMarker
                key={locker.id}
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
                        <p className="text-[8px] font-semibold uppercase tracking-wider text-slate-400">Lat</p>
                        <p className="text-[10px] font-medium text-slate-700 mt-0.5">{locker.lat.toFixed(4)}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-2 py-1.5 text-center">
                        <p className="text-[8px] font-semibold uppercase tracking-wider text-slate-400">Lng</p>
                        <p className="text-[10px] font-medium text-slate-700 mt-0.5">{locker.lng.toFixed(4)}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-2 py-1.5 text-center">
                        <p className="text-[8px] font-semibold uppercase tracking-wider text-slate-400">Order</p>
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

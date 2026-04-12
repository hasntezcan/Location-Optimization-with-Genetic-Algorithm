"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { ControlPanel } from "@/components/dashboard/control-panel";
import { LockerDetailPanel } from "@/components/dashboard/locker-detail-panel";
import { LockerStrip } from "@/components/dashboard/locker-strip";
import { buildFakeGenerationRun } from "@/lib/ga-mock";
import type { CandidatePoint, GenerationSnapshot, Locker } from "@/lib/types";

const LockerMap = dynamic(
  () => import("@/components/dashboard/locker-map").then((mod) => mod.LockerMap),
  { ssr: false }
);

function generationToUiLockers(snapshot: GenerationSnapshot | null): Locker[] {
  if (!snapshot) return [];

  return snapshot.lockers.map((locker, index) => ({
    id: locker.id,
    name: `Locker ${String(index + 1).padStart(2, "0")}`,
    lat: locker.lat,
    lng: locker.lng,
    neighborhood: locker.neighborhood,
  }));
}

export default function HomePage() {
  const [inputLockerCount, setInputLockerCount] = useState(4);
  const [activeLockerCount, setActiveLockerCount] = useState(4);

  const [candidates, setCandidates] = useState<CandidatePoint[]>([]);
  const [boundary, setBoundary] = useState<any | null>(null);

  const [generations, setGenerations] = useState<GenerationSnapshot[]>([]);
  const [currentGenerationIndex, setCurrentGenerationIndex] = useState(0);

  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(700);

  const [selectedLocker, setSelectedLocker] = useState<Locker | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [candidateResponse, boundaryResponse] = await Promise.all([
          fetch("/mock/candidate-points.json"),
          fetch("/mock/kadikoy_boundary.geojson"),
        ]);

        if (!candidateResponse.ok) {
          throw new Error(`Candidate fetch failed: ${candidateResponse.status}`);
        }

        if (!boundaryResponse.ok) {
          throw new Error(`Boundary fetch failed: ${boundaryResponse.status}`);
        }

        const candidateData: CandidatePoint[] = await candidateResponse.json();
        const boundaryData = await boundaryResponse.json();

        setCandidates(candidateData);
        setBoundary(boundaryData);
      } catch (error) {
        console.error("Failed to load mock data:", error);
      }
    }

    loadData();
  }, []);

  useEffect(() => {
    if (!candidates.length) return;

    const run = buildFakeGenerationRun(candidates, activeLockerCount, 120);
    setGenerations(run);
    setCurrentGenerationIndex(0);
    setIsPlaying(false);
  }, [candidates, activeLockerCount]);

  useEffect(() => {
    if (!isPlaying || generations.length <= 1) return;

    const timer = window.setInterval(() => {
      setCurrentGenerationIndex((prev) => {
        if (prev >= generations.length - 1) return 0;
        return prev + 1;
      });
    }, playbackSpeed);

    return () => window.clearInterval(timer);
  }, [isPlaying, playbackSpeed, generations.length]);

  const currentGeneration = generations[currentGenerationIndex] ?? null;
  const previousGeneration =
    currentGenerationIndex > 0 ? generations[currentGenerationIndex - 1] : null;

  const lockersForDisplay = useMemo(
    () => generationToUiLockers(currentGeneration),
    [currentGeneration]
  );

  useEffect(() => {
    if (!lockersForDisplay.length) {
      setSelectedLocker(null);
      return;
    }

    setSelectedLocker((prev) => {
      if (!prev) return null;
      return lockersForDisplay.find((locker) => locker.id === prev.id) ?? null;
    });
  }, [lockersForDisplay]);

  const handleShowResults = () => {
    const clamped = Math.max(1, Math.min(inputLockerCount, 100));
    setInputLockerCount(clamped);
    setActiveLockerCount(clamped);
    setCurrentGenerationIndex(0);
    setIsPlaying(false);
    setSelectedLocker(null);
  };

  const handleNextGeneration = () => {
    setCurrentGenerationIndex((prev) =>
      prev >= generations.length - 1 ? generations.length - 1 : prev + 1
    );
  };

  const handlePrevGeneration = () => {
    setCurrentGenerationIndex((prev) => (prev <= 0 ? 0 : prev - 1));
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top,_#ffffff_0%,_#f8fafc_45%,_#eef2f7_100%)] px-4 py-4 text-slate-900 sm:px-5 lg:px-6">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-[8%] top-[6%] h-40 w-40 rounded-full bg-sky-100/50 blur-3xl" />
        <div className="absolute right-[10%] top-[10%] h-56 w-56 rounded-full bg-indigo-100/40 blur-3xl" />
        <div className="absolute bottom-[8%] left-[22%] h-52 w-52 rounded-full bg-cyan-100/30 blur-3xl" />
      </div>

      <div className="relative mx-auto flex max-w-[1500px] flex-col gap-4">
        <header className="rounded-[30px] border border-white/60 bg-white/65 px-6 py-7 shadow-[0_10px_32px_rgba(15,23,42,0.05)] backdrop-blur-xl sm:px-8 sm:py-8">
          <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
            <span className="inline-flex items-center rounded-full border border-slate-200/70 bg-white/80 px-4 py-1.5 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500 shadow-sm">
              Parcel Locker Dashboard
            </span>

            <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl lg:text-[52px] lg:leading-[1.05]">
              Locker placement panel
            </h1>

            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-[15px]">
              Control the locker count, inspect parcel locker positions on the map, and review
              the selected locker&apos;s location details in a cleaner decision-support interface.
            </p>
          </div>
        </header>

        <section className="rounded-[30px] border border-white/60 bg-white/55 p-3 shadow-[0_12px_32px_rgba(15,23,42,0.05)] backdrop-blur-xl sm:p-4">
          <div className="rounded-[24px] border border-slate-200/50 bg-white/50 p-2.5 sm:p-3">
            <LockerStrip
              lockers={lockersForDisplay}
              selectedLockerId={selectedLocker?.id ?? ""}
              onSelectLocker={setSelectedLocker}
            />
          </div>

          <div className="mt-4 grid grid-cols-12 gap-4 lg:min-h-[calc(100vh-290px)]">
            <div className="col-span-12 lg:col-span-3 lg:h-[calc(100vh-290px)]">
              <ControlPanel
                lockerCount={inputLockerCount}
                onLockerCountChange={setInputLockerCount}
                onShowResults={handleShowResults}
                currentGeneration={currentGenerationIndex}
                generationCount={generations.length}
                isPlaying={isPlaying}
                playbackSpeed={playbackSpeed}
                onTogglePlayback={() => setIsPlaying((prev) => !prev)}
                onPrevGeneration={handlePrevGeneration}
                onNextGeneration={handleNextGeneration}
                onGenerationChange={setCurrentGenerationIndex}
                onPlaybackSpeedChange={setPlaybackSpeed}
              />
            </div>

            <div className="col-span-12 lg:col-span-6 lg:h-[calc(100vh-290px)]">
              {currentGeneration ? (
                <LockerMap
                  candidates={candidates}
                  boundary={boundary}
                  lockers={lockersForDisplay}
                  selectedLocker={selectedLocker}
                  onSelectLocker={setSelectedLocker}
                  currentGeneration={currentGeneration}
                  previousGeneration={previousGeneration}
                />
              ) : (
                <div className="flex h-full min-h-[420px] items-center justify-center rounded-[30px] border border-white/60 bg-white/55 p-6 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
                  <p className="text-sm text-slate-500">Loading generation data...</p>
                </div>
              )}
            </div>

            <div className="col-span-12 lg:col-span-3 lg:h-[calc(100vh-290px)]">
              {selectedLocker && currentGeneration ? (
                <LockerDetailPanel
                  locker={selectedLocker}
                  generation={currentGeneration}
                />
              ) : (
                <div className="flex h-full min-h-[320px] items-center justify-center rounded-[30px] border border-white/60 bg-white/55 p-6 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl lg:h-[calc(100vh-290px)]">
                  <p className="text-sm text-slate-500">No locker selected yet.</p>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
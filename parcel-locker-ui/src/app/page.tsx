"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { ControlPanel } from "@/components/dashboard/control-panel";
import { LockerDetailPanel } from "@/components/dashboard/locker-detail-panel";
import { LockerStrip } from "@/components/dashboard/locker-strip";
import type { CandidatePoint, ArchiveSolution, Locker } from "@/lib/types";
import { 
  ScatterChart, 
  Scatter, 
  Line,
  XAxis, 
  YAxis, 
  ZAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from 'recharts';

const LockerMap = dynamic(
  () => import("@/components/dashboard/locker-map").then((mod) => mod.LockerMap),
  { ssr: false }
);

function solutionToUiLockers(solution: ArchiveSolution | null): Locker[] {
  if (!solution) return [];

  return solution.lockers.map((locker, index) => ({
    id: locker.id,
    name: `Locker ${String(index + 1).padStart(2, "0")}`,
    lat: locker.lat,
    lng: locker.lng,
    neighborhood: locker.neighborhood,
    score: locker.score,
    source: locker.source,
  }));
}

interface ChartPoint {
  id: number;
  x: number;
  y: number;
  isPareto?: boolean;
  isBestF1?: boolean;
  isBestF2?: boolean;
  isSelected: boolean;
  size: number;
}

export default function HomePage() {
  const [inputLockerCount, setInputLockerCount] = useState(8);
  const [populationSize, setPopulationSize] = useState(100);
  const [maxGenerations, setMaxGenerations] = useState(30);
  const [mutationRate, setMutationRate] = useState(0.1);

  const [, setActiveLockerCount] = useState(8);

  const [candidates, setCandidates] = useState<CandidatePoint[]>([]);
  const [boundary, setBoundary] = useState<GeoJSON.FeatureCollection | null>(null);

  const [archiveSolutions, setArchiveSolutions] = useState<ArchiveSolution[]>([]);
  const [currentSolutionIndex, setCurrentSolutionIndex] = useState(0);

  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(700);

  const [selectedLocker, setSelectedLocker] = useState<Locker | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info', text: string } | null>(null);
  const [isPlotModalOpen, setIsPlotModalOpen] = useState(false);
  const [plotTimestamp, setPlotTimestamp] = useState(Date.now());

  const loadData = async () => {
    try {
      const [candidateResponse, boundaryResponse, archiveResponse] = await Promise.all([
        fetch("/mock/candidate-points.json"),
        fetch("/mock/kadikoy_boundary.geojson"),
        fetch("/mock/ga-results.json"),
      ]);

      if (!candidateResponse.ok) throw new Error("Candidate fetch failed");
      if (!boundaryResponse.ok) throw new Error("Boundary fetch failed");
      if (!archiveResponse.ok) throw new Error("Archive fetch failed");

      const candidateData: CandidatePoint[] = await candidateResponse.json();
      const boundaryData = (await boundaryResponse.json()) as GeoJSON.FeatureCollection;
      const archiveData: ArchiveSolution[] = await archiveResponse.json();

      setCandidates(candidateData);
      setBoundary(boundaryData);
      setArchiveSolutions(archiveData);
    } catch (error) {
      console.error("Failed to load data:", error);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!isPlaying || archiveSolutions.length <= 1) return;

    const timer = window.setInterval(() => {
      setCurrentSolutionIndex((prev) => {
        if (prev >= archiveSolutions.length - 1) return 0;
        return prev + 1;
      });
    }, playbackSpeed);

    return () => window.clearInterval(timer);
  }, [isPlaying, playbackSpeed, archiveSolutions.length]);

  const currentSolution = archiveSolutions[currentSolutionIndex] ?? null;

  const chartData = useMemo<ChartPoint[]>(() => {
    return archiveSolutions.map((sol) => ({
      id: sol.id,
      x: sol.metrics.accessibility,
      y: sol.metrics.equity,
      isPareto: sol.isPareto,
      isBestF1: sol.isBestF1,
      isBestF2: sol.isBestF2,
      isSelected: sol.id === currentSolution?.id,
      size: sol.id === currentSolution?.id ? 300 : 100
    }));
  }, [archiveSolutions, currentSolution]);

  const paretoLineData = useMemo(() => {
    return chartData
      .filter(p => p.isPareto)
      .sort((a, b) => a.x - b.x);
  }, [chartData]);

  const lockersForDisplay = useMemo(
    () => solutionToUiLockers(currentSolution),
    [currentSolution]
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

  const handleShowResults = async () => {
    const clamped = Math.max(1, Math.min(inputLockerCount, 100));
    setInputLockerCount(clamped);
    setIsOptimizing(true);
    setStatusMessage({ type: 'info', text: 'Optimization started. Please wait...' });
    
    try {
      const response = await fetch("/api/run-ga", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          k: clamped,
          populationSize,
          maxGenerations,
          mutationRate
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.details || "Optimization failed");
      }

      // Reload data after successful optimization
      await loadData();
      setPlotTimestamp(Date.now());
      
      setActiveLockerCount(clamped);
      setCurrentSolutionIndex(0);
      setIsPlaying(false);
      setSelectedLocker(null);
      
      setStatusMessage({ type: 'success', text: `Optimization completed for k=${clamped}!` });
      
      // Clear success message after 5 seconds
      setTimeout(() => setStatusMessage(null), 5000);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      console.error("Optimization error:", message);
      setStatusMessage({ type: 'error', text: `Error: ${message}` });
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleNextSolution = () => {
    setCurrentSolutionIndex((prev) =>
      prev >= archiveSolutions.length - 1 ? archiveSolutions.length - 1 : prev + 1
    );
  };

  const handlePrevSolution = () => {
    setCurrentSolutionIndex((prev) => (prev <= 0 ? 0 : prev - 1));
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

            {statusMessage && (
              <div className={`mt-6 w-full max-w-md rounded-2xl border px-4 py-3 text-sm font-medium shadow-sm animate-in fade-in slide-in-from-top-4 duration-300 ${
                statusMessage.type === 'success' 
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700' 
                  : statusMessage.type === 'error'
                  ? 'border-rose-200 bg-rose-50 text-rose-700'
                  : 'border-blue-200 bg-blue-50 text-blue-700'
              }`}>
                <div className="flex items-center gap-3">
                  {statusMessage.type === 'success' && <span className="text-lg">✓</span>}
                  {statusMessage.type === 'error' && <span className="text-lg">⚠</span>}
                  {statusMessage.type === 'info' && <span className="text-lg">ℹ</span>}
                  <p>{statusMessage.text}</p>
                </div>
              </div>
            )}
          </div>
        </header>

        <section className="rounded-[30px] border border-white/60 bg-white/55 p-3 shadow-[0_12px_32px_rgba(15,23,42,0.05)] backdrop-blur-xl sm:p-4">
          <div className="rounded-[24px] border border-slate-200/50 bg-white/50 p-2.5 sm:p-3">
            <LockerStrip
              lockers={lockersForDisplay}
              selectedLockerId={selectedLocker?.id ?? ""}
              onSelectLocker={setSelectedLocker}
              isPareto={currentSolution?.isPareto}
            />
          </div>

          <div className="mt-4 grid grid-cols-12 gap-4 lg:min-h-[calc(100vh-290px)]">
            <div className="col-span-12 lg:col-span-3 lg:h-[calc(100vh-290px)]">
              <ControlPanel
                lockerCount={inputLockerCount}
                onLockerCountChange={setInputLockerCount}
                populationSize={populationSize}
                onPopulationSizeChange={setPopulationSize}
                maxGenerations={maxGenerations}
                onMaxGenerationsChange={setMaxGenerations}
                mutationRate={mutationRate}
                onMutationRateChange={setMutationRate}
                onShowResults={handleShowResults}
                currentGeneration={currentSolutionIndex}
                generationCount={archiveSolutions.length}
                isPlaying={isPlaying}
                playbackSpeed={playbackSpeed}
                onTogglePlayback={() => setIsPlaying((prev) => !prev)}
                onPrevGeneration={handlePrevSolution}
                onNextGeneration={handleNextSolution}
                onGenerationChange={setCurrentSolutionIndex}
                onPlaybackSpeedChange={setPlaybackSpeed}
                isOptimizing={isOptimizing}
                isCurrentSolutionPareto={currentSolution?.isPareto}
                isBestF1={currentSolution?.isBestF1}
                isBestF2={currentSolution?.isBestF2}
              />
            </div>

            <div className="col-span-12 lg:col-span-6 lg:h-[calc(100vh-290px)]">
              {currentSolution ? (
                <LockerMap
                  candidates={candidates}
                  boundary={boundary}
                  lockers={lockersForDisplay}
                  selectedLocker={selectedLocker}
                  onSelectLocker={setSelectedLocker}
                  currentGeneration={currentSolution}
                />
              ) : (
                <div className="flex h-full min-h-[420px] items-center justify-center rounded-[30px] border border-white/60 bg-white/55 p-6 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
                  <p className="text-sm text-slate-500">Loading solution data...</p>
                </div>
              )}
            </div>

            <div className="col-span-12 lg:col-span-3 lg:h-[calc(100vh-290px)]">
              {selectedLocker && currentSolution ? (
                <LockerDetailPanel
                  locker={selectedLocker}
                  solution={currentSolution}
                  onClose={() => setSelectedLocker(null)}
                />
              ) : (
                <div className="flex flex-col h-full gap-4">
                  <div className="flex h-1/2 min-h-[250px] items-center justify-center rounded-[30px] border border-white/60 bg-white/55 p-4 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl">
                    <div className="w-full h-full flex flex-col">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Archive Plot</span>
                        <div className="flex gap-2">
                           <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-indigo-400 border-t border-dashed border-indigo-400"></div><span className="text-[9px] text-slate-500">Pareto</span></div>
                           <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-blue-500"></div><span className="text-[9px] text-slate-500">Dist</span></div>
                           <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-emerald-600"></div><span className="text-[9px] text-slate-500">Cost</span></div>
                        </div>
                      </div>
                      <div className="flex-1 min-h-0">
                        <ResponsiveContainer width="100%" height="100%">
                          <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: -10 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                            <XAxis 
                              type="number" 
                              dataKey="x" 
                              name="Distance" 
                              unit="" 
                              fontSize={10}
                              domain={['auto', 'auto']}
                              tickCount={5}
                              label={{ value: 'Distance', position: 'insideBottom', offset: -10, fontSize: 10 }}
                            />
                            <YAxis 
                              type="number" 
                              dataKey="y" 
                              name="Cost" 
                              unit="" 
                              fontSize={10}
                              domain={['auto', 'auto']}
                              tickCount={5}
                              label={{ value: 'Cost', angle: -90, position: 'insideLeft', offset: 10, fontSize: 10 }}
                            />
                            <ZAxis type="number" dataKey="size" range={[50, 400]} />
                            <Tooltip 
                              cursor={{ strokeDasharray: '3 3' }}
                              content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                  const data = payload[0].payload as ChartPoint;
                                  return (
                                    <div className="rounded-lg border border-slate-200 bg-white p-2 shadow-md text-[10px]">
                                      <div className="flex items-center justify-between gap-4 mb-1">
                                        <p className="font-bold">Solution #{data.id + 1}</p>
                                        {data.isSelected && <span className="text-[8px] bg-slate-900 text-white px-1 rounded">SELECTED</span>}
                                      </div>
                                      <p>Dist: {data.x.toFixed(4)}</p>
                                      <p>Cost: {data.y.toFixed(4)}</p>
                                      {data.isBestF1 && <p className="text-blue-500 font-bold">Best Distance</p>}
                                      {data.isBestF2 && <p className="text-emerald-600 font-bold">Best Cost</p>}
                                      {data.isPareto && <p className="text-emerald-500">Pareto Optimal</p>}
                                    </div>
                                  );
                                }
                                return null;
                              }}
                            />
                            <Line
                              type="monotone"
                              data={paretoLineData}
                              dataKey="y"
                              stroke="#818cf8"
                              strokeDasharray="5 5"
                              dot={false}
                              activeDot={false}
                              legendType="none"
                              connectNulls
                            />
                            <Scatter 
                              name="Solutions" 
                              data={chartData} 
                              onClick={(data: unknown) => {
                                const id = (data as Partial<ChartPoint> | null)?.id;
                                if (typeof id !== "number") return;
                                const index = archiveSolutions.findIndex(s => s.id === id);
                                if (index !== -1) setCurrentSolutionIndex(index);
                              }}
                            >
                              {chartData.map((entry, index) => {
                                let fill = "#94a3b8"; // Default gray
                                let stroke = "none";
                                let strokeWidth = 0;
                                
                                if (entry.isSelected) {
                                  stroke = "#0f172a";
                                  strokeWidth = 3;
                                }
                                
                                if (entry.isBestF1) fill = "#3b82f6"; // Blue
                                else if (entry.isBestF2) fill = "#059669"; // Emerald
                                else if (entry.isPareto) fill = "#10b981"; // Light Emerald
                                
                                return (
                                  <Cell 
                                    key={`cell-${index}`} 
                                    fill={fill}
                                    stroke={stroke}
                                    strokeWidth={strokeWidth}
                                    className={`cursor-pointer transition-all duration-200 hover:opacity-80 ${entry.isSelected ? 'animate-pulse' : ''}`}
                                  />
                                );
                              })}
                            </Scatter>
                          </ScatterChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                  <div className="flex h-1/2 min-h-[250px] items-center justify-center rounded-[30px] border border-white/60 bg-white/55 p-2 shadow-[0_12px_35px_rgba(15,23,42,0.06)] backdrop-blur-xl overflow-hidden">
                    <div className="w-full h-full flex flex-col p-2">
                       <div className="flex items-center justify-between mb-2">
                         <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Static Analysis Plot</span>
                         <span className="text-[9px] text-indigo-600 font-semibold bg-indigo-50 px-1.5 py-0.5 rounded animate-pulse">Click to expand</span>
                       </div>
                       <div 
                         className="flex-1 relative rounded-xl overflow-hidden border border-slate-200 cursor-zoom-in group"
                         onClick={() => setIsPlotModalOpen(true)}
                       >
                         <img 
                           src={`/mock/archive_comparison_latest.png?t=${plotTimestamp}`} 
                           alt="GA Analysis" 
                           className="absolute inset-0 w-full h-full object-contain bg-white transition-transform duration-300 group-hover:scale-105"
                           onError={(e) => {
                             (e.target as HTMLImageElement).style.display = 'none';
                           }}
                         />
                         <div className="absolute inset-0 bg-slate-900/0 group-hover:bg-slate-900/5 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                           <span className="bg-white/90 px-3 py-1.5 rounded-full text-[10px] font-bold shadow-lg">VIEW FULLSCREEN</span>
                         </div>
                       </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* Fullscreen Image Modal */}
      {isPlotModalOpen && (
        <div 
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-900/90 backdrop-blur-md p-4 sm:p-8 animate-in fade-in duration-300"
          onClick={() => setIsPlotModalOpen(false)}
        >
          <div className="relative w-full h-full max-w-7xl flex flex-col items-center justify-center">
            <button 
              className="absolute -top-4 -right-4 sm:top-0 sm:right-0 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white text-slate-900 shadow-xl transition hover:bg-slate-100 hover:scale-110"
              onClick={(e) => {
                e.stopPropagation();
                setIsPlotModalOpen(false);
              }}
            >
              <span className="text-xl font-bold">✕</span>
            </button>
            <div 
              className="w-full h-full rounded-2xl overflow-hidden border border-white/20 shadow-2xl bg-white"
              onClick={(e) => e.stopPropagation()}
            >
              <img 
                 src={`/mock/archive_comparison_latest.png?t=${plotTimestamp}`} 
                 alt="GA Analysis Fullscreen" 
                 className="w-full h-full object-contain"
               />
            </div>
            <div className="mt-4 text-center">
              <p className="text-white/70 text-sm font-medium">Static Analysis Plot - Full View</p>
              <p className="text-white/40 text-xs mt-1">Click anywhere outside or use the close button to return</p>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

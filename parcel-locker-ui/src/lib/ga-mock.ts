import type {
  CandidatePoint,
  GenerationLocker,
  GenerationSnapshot,
} from "@/lib/types";

function normalize(value: number, min: number, max: number) {
  if (max === min) return 0;
  return (value - min) / (max - min);
}

function average(values: number[]) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function weightedPickMany<T>(
  items: T[],
  count: number,
  getWeight: (item: T) => number
): T[] {
  const pool = [...items];
  const result: T[] = [];

  while (pool.length && result.length < count) {
    const total = pool.reduce((sum, item) => sum + Math.max(0.0001, getWeight(item)), 0);
    let r = Math.random() * total;
    let pickedIndex = 0;

    for (let i = 0; i < pool.length; i++) {
      r -= Math.max(0.0001, getWeight(pool[i]));
      if (r <= 0) {
        pickedIndex = i;
        break;
      }
    }

    result.push(pool[pickedIndex]);
    pool.splice(pickedIndex, 1);
  }

  return result;
}

export function buildFakeGenerationRun(
  candidates: CandidatePoint[],
  lockerCount: number,
  generationCount = 120
): GenerationSnapshot[] {
  const allowed = candidates.filter((candidate) => !candidate.isForbidden);

  const populationMin = Math.min(...allowed.map((c) => c.population));
  const populationMax = Math.max(...allowed.map((c) => c.population));

  const transitValues = allowed.map((c) => c.poiTransport + c.poiBusStop);
  const transitMin = Math.min(...transitValues);
  const transitMax = Math.max(...transitValues);

  const poiValues = allowed.map(
    (c) =>
      c.poiAtm +
      c.poiBank +
      c.poiHospital +
      c.poiSchool +
      c.poiUniversity +
      c.poiPostOffice
  );
  const poiMin = Math.min(...poiValues);
  const poiMax = Math.max(...poiValues);

  const scored = allowed.map((candidate) => {
    const transit = candidate.poiTransport + candidate.poiBusStop;
    const poiTotal =
      candidate.poiAtm +
      candidate.poiBank +
      candidate.poiHospital +
      candidate.poiSchool +
      candidate.poiUniversity +
      candidate.poiPostOffice;

    const score =
      0.5 * normalize(candidate.population, populationMin, populationMax) +
      0.3 * normalize(transit, transitMin, transitMax) +
      0.2 * normalize(poiTotal, poiMin, poiMax);

    return {
      ...candidate,
      baseScore: score,
    };
  });

  const byId = new Map(scored.map((candidate) => [candidate.id, candidate]));

  let previous: GenerationLocker[] = [];
  const snapshots: GenerationSnapshot[] = [];

  for (let generation = 0; generation < generationCount; generation++) {
    const eliteCount = Math.max(1, Math.floor(lockerCount * 0.3));
    const crossoverCount = Math.max(1, Math.floor(lockerCount * 0.5));
    const mutationCount = Math.max(0, lockerCount - eliteCount - crossoverCount);

    const elites =
      generation === 0
        ? weightedPickMany(scored, eliteCount, (candidate) => candidate.baseScore + 0.05)
        : previous
            .slice()
            .sort((a, b) => b.score - a.score)
            .slice(0, eliteCount)
            .map((locker) => byId.get(locker.id)!)
            .filter(Boolean);

    const eliteIds = new Set(elites.map((candidate) => candidate.id));

    const remainingPool = scored.filter((candidate) => !eliteIds.has(candidate.id));

    const crossovers = weightedPickMany(
      remainingPool,
      crossoverCount,
      (candidate) => candidate.baseScore * (1 + generation / generationCount)
    );

    const usedIds = new Set([...eliteIds, ...crossovers.map((candidate) => candidate.id)]);

    const mutations = weightedPickMany(
      scored.filter((candidate) => !usedIds.has(candidate.id)),
      mutationCount,
      (candidate) => 0.2 + Math.random() * candidate.baseScore
    );

    const current: GenerationLocker[] = [
      ...elites.map((candidate) => ({
        id: candidate.id,
        lat: candidate.lat,
        lng: candidate.lng,
        neighborhood: candidate.neighborhood,
        score: candidate.baseScore + generation * 0.002 + Math.random() * 0.02,
        source: "elite" as const,
      })),
      ...crossovers.map((candidate) => ({
        id: candidate.id,
        lat: candidate.lat,
        lng: candidate.lng,
        neighborhood: candidate.neighborhood,
        score: candidate.baseScore + generation * 0.003 + Math.random() * 0.03,
        source: "crossover" as const,
      })),
      ...mutations.map((candidate) => ({
        id: candidate.id,
        lat: candidate.lat,
        lng: candidate.lng,
        neighborhood: candidate.neighborhood,
        score: candidate.baseScore + Math.random() * 0.04,
        source: "mutation" as const,
      })),
    ];

    const meanScore = average(current.map((locker) => locker.score));
    const distinctNeighborhoods = new Set(current.map((locker) => locker.neighborhood)).size;

    snapshots.push({
      generation,
      lockers: current,
      metrics: {
        accessibility: Number((1.2 - meanScore * 0.5 - generation * 0.002).toFixed(3)),
        equity: Number((0.9 - (distinctNeighborhoods / lockerCount) * 0.25 - generation * 0.001).toFixed(3)),
        fitness: Number((meanScore + generation * 0.002).toFixed(3)),
      },
    });

    previous = current;
  }

  return snapshots;
}
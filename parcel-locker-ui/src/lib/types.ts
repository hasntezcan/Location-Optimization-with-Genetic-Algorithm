export type Locker = {
  id: string;
  name: string;
  lat: number;
  lng: number;
  neighborhood: string;
  score?: number;
  source?: GenerationSource;
};

export type CandidatePoint = {
  id: string;
  lat: number;
  lng: number;
  neighborhood: string;
  population: number;
  poiAtm: number;
  poiBank: number;
  poiHospital: number;
  poiSchool: number;
  poiUniversity: number;
  poiPostOffice: number;
  poiTransport: number;
  poiBusStop: number;
  isForbidden: boolean;
  nearbyLockerCount: number;
  existingLockerCount: number;
};

export type ArchiveSolution = {
  id: number;
  lockers: GenerationLocker[];
  scenario?: SolutionScenario;
  isPareto?: boolean;
  isBestF1?: boolean;
  isBestF2?: boolean;
  metrics: {
    accessibility: number;
    equity: number;
    fitness: number;
    norm_f1?: number;
    norm_f2?: number;
  };
};

export type GenerationSource = "elite" | "crossover" | "mutation";

export type GenerationLocker = {
  id: string;
  lat: number;
  lng: number;
  neighborhood: string;
  score: number;
  source: GenerationSource;
};

export type SolutionScenario = {
  includeExistingLockers: boolean;
  existingPhysicalLockerCount: number;
  existingLockerCandidateCount: number;
  effectiveFixedFacilityIdsCount: number;
  newFacilityCount: number;
  totalPhysicalLockerCount: number;
  totalEffectiveFacilityCandidateCount: number;
};

export type GenerationSnapshot = {
  generation: number;
  lockers: GenerationLocker[];
  metrics: {
    accessibility: number;
    equity: number;
    fitness: number;
  };
};

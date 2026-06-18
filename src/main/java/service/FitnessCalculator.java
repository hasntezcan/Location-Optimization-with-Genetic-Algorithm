package service;

import model.CandidatePoint;
import model.CandidateRepository;
import model.Individual;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;

/**
 * Computes raw objective values for individuals in the parcel locker
 * optimization problem.
 *
 * <p>This class is responsible only for problem-specific objective evaluation.
 * It does not perform SPEA2 dominance, density, archive handling, or selection.</p>
 */
public class FitnessCalculator {

    private final double[][] distanceMatrix;
    private final CandidateRepository repository;
    private final double totalSystemDemand;
    private final double beta;
    private final List<Integer> fixedFacilityIds;
    private final List<Integer> fixedFacilityIndexes;
    private final double[] nearestFixedFacilityCostByCandidateIndex;

    /**
     * Lambda parameter controlling the influence of POI score on demand.
     * <p>
     * When {@code useDynamicDemand} is {@code true}, each grid point's demand
     * is computed as {@code population × (1 + lambda × poiScore)} instead of
     * reading the pre-computed {@code demandScore} from the CSV.
     * </p>
     */
    private final double lambda;

    /**
     * Whether to compute demand dynamically using the lambda formula.
     * <p>
     * {@code false}: use pre-computed {@code getDemandScore()} from CSV (default, used by Main and ParameterAnalyzer).
     * {@code true}: compute {@code population × (1 + lambda × poiScore)} (available for future experiments).
     * </p>
     */
    private final boolean useDynamicDemand;

    /**
     * Creates a fitness calculator that reads demand from the pre-computed
     * {@code demandScore} column in the CSV.
     *
     * <p>This constructor is used by {@link app.Main} and preserves full
     * backward compatibility.</p>
     *
     * @param distanceMatrix precomputed candidate-to-candidate distance matrix
     * @param repository candidate repository synchronized with the matrix indexing
     * @param beta distance-decay exponent
     * @throws IllegalArgumentException if the matrix or repository is invalid,
     *                                  or if {@code beta <= 0}
     * @throws IllegalStateException if the total system demand is not positive
     */
    public FitnessCalculator(double[][] distanceMatrix, CandidateRepository repository, double beta) {
        this(distanceMatrix, repository, beta, Collections.emptyList(), 0.0, false);
    }

    /**
     * Creates a fitness calculator with optional fixed existing facilities.
     *
     * <p>The fixed IDs are evaluated together with each individual's chromosome,
     * but they are never written into or used to mutate the chromosome itself.</p>
     *
     * @param distanceMatrix precomputed candidate-to-candidate distance matrix
     * @param repository candidate repository synchronized with the matrix indexing
     * @param beta distance-decay exponent
     * @param fixedFacilityIds existing facility candidate IDs
     */
    public FitnessCalculator(double[][] distanceMatrix, CandidateRepository repository,
                             double beta, List<Integer> fixedFacilityIds) {
        this(distanceMatrix, repository, beta, fixedFacilityIds, 0.0, false);
    }

    /**
     * Creates a fitness calculator that computes demand dynamically using the
     * lambda formula: {@code demand = population × (1 + lambda × poiScore)}.
     *
     * <p>This constructor is available for future lambda-sensitivity
     * experiments without re-running the Python preprocessing. The current
     * {@link app.ParameterAnalyzer} grid does not use it.</p>
     *
     * @param distanceMatrix precomputed candidate-to-candidate distance matrix
     * @param repository candidate repository synchronized with the matrix indexing
     * @param beta distance-decay exponent
     * @param lambda POI influence weight (e.g. 0.4, 0.5, 0.6)
     * @throws IllegalArgumentException if the matrix or repository is invalid,
     *                                  or if {@code beta <= 0} or {@code lambda < 0}
     * @throws IllegalStateException if the total system demand is not positive
     */
    public FitnessCalculator(double[][] distanceMatrix, CandidateRepository repository,
                             double beta, double lambda) {
        this(distanceMatrix, repository, beta, Collections.emptyList(), lambda, true);
    }

    /**
     * Internal master constructor.
     */
    private FitnessCalculator(double[][] distanceMatrix, CandidateRepository repository,
                              double beta, List<Integer> fixedFacilityIds,
                              double lambda, boolean useDynamicDemand) {
        if (distanceMatrix == null || distanceMatrix.length == 0) {
            throw new IllegalArgumentException("Distance matrix cannot be null or empty.");
        }
        if (repository == null) {
            throw new IllegalArgumentException("Repository cannot be null.");
        }
        if (beta <= 0) {
            throw new IllegalArgumentException("Beta must be greater than 0.");
        }
        if (lambda < 0) {
            throw new IllegalArgumentException("Lambda must be non-negative.");
        }

        this.distanceMatrix = distanceMatrix;
        this.repository = repository;
        this.beta = beta;
        this.lambda = lambda;
        this.useDynamicDemand = useDynamicDemand;
        this.fixedFacilityIds = normalizeFixedFacilityIds(fixedFacilityIds);
        this.fixedFacilityIndexes = Collections.unmodifiableList(
                toMatrixIndexes(this.fixedFacilityIds, "Fixed facility ID"));
        this.nearestFixedFacilityCostByCandidateIndex = precomputeNearestFixedFacilityCosts();
        this.totalSystemDemand = calculateTotalDemand();

        if (this.totalSystemDemand <= 0) {
            throw new IllegalStateException("Total system demand must be greater than 0.");
        }
    }

    private List<Integer> normalizeFixedFacilityIds(List<Integer> inputIds) {
        if (inputIds == null || inputIds.isEmpty()) {
            return Collections.emptyList();
        }

        return Collections.unmodifiableList(new ArrayList<>(new LinkedHashSet<>(inputIds)));
    }

    /**
     * Computes the total system demand across all candidate grid points.
     *
     * @return total demand
     */
    private double calculateTotalDemand() {
        return repository.getAllCandidatesSorted().stream()
                .mapToDouble(this::getDemand)
                .sum();
    }

    /**
     * Returns the demand for a single grid point, using either the pre-computed
     * CSV value or the dynamic lambda formula depending on the constructor used.
     *
     * @param grid candidate grid point
     * @return demand value
     */
    private double getDemand(CandidatePoint grid) {
        if (useDynamicDemand) {
            return grid.getPopulation() * (1.0 + lambda * grid.getPoiScore());
        }
        return grid.getDemandScore();
    }

    /**
     * Validates that the given individual exists and has a non-empty chromosome.
     *
     * @param individual individual to validate
     * @throws IllegalArgumentException if the individual or chromosome is invalid
     */
    private void validateIndividual(Individual individual) {
        if (individual == null) {
            throw new IllegalArgumentException("Individual cannot be null.");
        }
        if (individual.getChromosome() == null || individual.getChromosome().isEmpty()) {
            throw new IllegalArgumentException("Individual chromosome cannot be null or empty.");
        }
    }

    /**
     * Finds the nearest selected locker for the given grid point and returns
     * the corresponding distance cost {@code (distance_km)^beta}.
     *
     * <p>The precomputed distance matrix stores values in metres. This method
     * converts the distance to kilometres before applying the decay exponent
     * so that objective values remain in a numerically manageable range.</p>
     *
     * @param grid demand grid point
     * @param lockerIds selected locker candidate IDs
     * @return distance cost to the nearest selected locker in kilometre-based units
     * @throws IllegalStateException if a grid or locker ID cannot be mapped
     *                               to a matrix index
     */
    private double findDistanceCostToNearestLockerIndex(int gridIndex, List<Integer> lockerIndexes) {
        double minDistanceMetres = Double.MAX_VALUE;

        for (int lockerIndex : lockerIndexes) {
            double currentDistance = distanceMatrix[gridIndex][lockerIndex];
            if (currentDistance < minDistanceMetres) {
                minDistanceMetres = currentDistance;
            }
        }

        return distanceCostFromMetres(minDistanceMetres);
    }

    private List<Integer> toMatrixIndexes(List<Integer> candidateIds, String label) {
        List<Integer> indexes = new ArrayList<>();
        if (candidateIds == null) {
            return indexes;
        }

        for (int candidateId : candidateIds) {
            int index = repository.getIndexById(candidateId);
            if (index < 0) {
                throw new IllegalArgumentException(label + " not found in repository index map: " + candidateId);
            }
            indexes.add(index);
        }
        return indexes;
    }

    private double[] precomputeNearestFixedFacilityCosts() {
        double[] costs = new double[distanceMatrix.length];
        if (fixedFacilityIndexes.isEmpty()) {
            Arrays.fill(costs, Double.POSITIVE_INFINITY);
            return costs;
        }

        for (int gridIndex = 0; gridIndex < distanceMatrix.length; gridIndex++) {
            costs[gridIndex] = findDistanceCostToNearestLockerIndex(gridIndex, fixedFacilityIndexes);
        }
        return costs;
    }

    private double distanceCostFromMetres(double distanceMetres) {
        double distanceKm = distanceMetres / 1000.0;
        return Math.pow(distanceKm, beta);
    }

    private int getGridIndex(CandidatePoint grid) {
        int gridIndex = repository.getIndexById(grid.getId());
        if (gridIndex < 0) {
            throw new IllegalStateException("Grid ID not found in repository index map: " + grid.getId());
        }
        return gridIndex;
    }

    /**
     * Evaluates the first objective value (f1), representing accessibility.
     *
     * <p>The objective is the demand-weighted average distance cost from all
     * demand grid points to their nearest selected locker.</p>
     *
     * @param individual individual to evaluate
     */
    public void evaluateF1(Individual individual) {
        validateIndividual(individual);

        double weightedDistanceSum = 0.0;
        List<CandidatePoint> allGrids = repository.getAllCandidatesSorted();
        List<Integer> lockerIndexes = toMatrixIndexes(individual.getChromosome(), "Locker ID");

        for (CandidatePoint grid : allGrids) {
            int gridIndex = getGridIndex(grid);
            double newRecommendedCost = findDistanceCostToNearestLockerIndex(gridIndex, lockerIndexes);
            double distanceCost = Math.min(
                    nearestFixedFacilityCostByCandidateIndex[gridIndex],
                    newRecommendedCost);
            weightedDistanceSum += getDemand(grid) * distanceCost;
        }

        double f1Score = weightedDistanceSum / totalSystemDemand;
        individual.setObjective1(f1Score);
    }

    /**
     * Evaluates the second objective value (f2), representing equity.
     *
     * <p>This objective is computed as the coefficient of variation (CV) of
     * mahalle-level weighted mean accessibility costs. CV is defined as
     * {@code standardDeviation / mean} and produces a dimensionless ratio
     * that is independent of the distance unit. Lower values indicate more
     * even service quality across neighborhoods.</p>
     *
     * @param individual individual to evaluate
     */
    public void evaluateF2(Individual individual) {
        validateIndividual(individual);

        List<CandidatePoint> allGrids = repository.getAllCandidatesSorted();
        List<Integer> lockerIndexes = toMatrixIndexes(individual.getChromosome(), "Locker ID");

        Map<String, Double> mahalleWeightedCostSum = new HashMap<>();
        Map<String, Double> mahalleDemandSum = new HashMap<>();

        for (CandidatePoint grid : allGrids) {
            String mahalle = grid.getMahalleNameTurkish();
            if (mahalle == null || mahalle.isBlank()) {
                throw new IllegalStateException("Mahalle name is null or blank for grid ID: " + grid.getId());
            }

            double demand = getDemand(grid);
            int gridIndex = getGridIndex(grid);
            double newRecommendedCost = findDistanceCostToNearestLockerIndex(gridIndex, lockerIndexes);
            double distanceCost = Math.min(
                    nearestFixedFacilityCostByCandidateIndex[gridIndex],
                    newRecommendedCost);

            mahalleWeightedCostSum.merge(mahalle, demand * distanceCost, Double::sum);
            mahalleDemandSum.merge(mahalle, demand, Double::sum);
        }

        Map<String, Double> mahalleMeanCost = new HashMap<>();
        for (String mahalle : mahalleWeightedCostSum.keySet()) {
            double weightedCostSum = mahalleWeightedCostSum.get(mahalle);
            double demandSum = mahalleDemandSum.getOrDefault(mahalle, 0.0);

            if (demandSum <= 0) {
                throw new IllegalStateException("Demand sum must be > 0 for mahalle: " + mahalle);
            }

            mahalleMeanCost.put(mahalle, weightedCostSum / demandSum);
        }

        double meanOfMahalleMeans = mahalleMeanCost.values().stream()
                .mapToDouble(Double::doubleValue)
                .average()
                .orElseThrow(() -> new IllegalStateException("No mahalle mean costs could be computed."));

        double variance = mahalleMeanCost.values().stream()
                .mapToDouble(value -> {
                    double diff = value - meanOfMahalleMeans;
                    return diff * diff;
                })
                .average()
                .orElse(0.0);

        double standardDeviation = Math.sqrt(variance);
        double cv = (meanOfMahalleMeans > 0)
                ? standardDeviation / meanOfMahalleMeans
                : 0.0;

        individual.setObjective2(cv);
    }

    /**
     * Evaluates both raw objectives of a single individual.
     *
     * @param individual individual to evaluate
     */
    public void evaluateObjectives(Individual individual) {
        evaluateF1(individual);
        evaluateF2(individual);
    }

    /**
     * Evaluates both raw objectives of all individuals in the population.
     *
     * @param population population to evaluate
     * @throws IllegalArgumentException if the population is null
     */
    public void evaluatePopulationObjectives(List<Individual> population) {
        if (population == null) {
            throw new IllegalArgumentException("Population cannot be null.");
        }

        for (Individual individual : population) {
            evaluateObjectives(individual);
        }
    }
}

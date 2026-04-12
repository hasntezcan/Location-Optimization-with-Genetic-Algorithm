package service;

import model.CandidatePoint;
import model.CandidateRepository;
import model.Individual;

import java.util.HashMap;
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

    /**
     * Creates a fitness calculator with the given distance matrix,
     * candidate repository, and distance-decay exponent.
     *
     * @param distanceMatrix precomputed candidate-to-candidate distance matrix
     * @param repository candidate repository synchronized with the matrix indexing
     * @param beta distance-decay exponent
     * @throws IllegalArgumentException if the matrix or repository is invalid,
     *                                  or if {@code beta <= 0}
     * @throws IllegalStateException if the total system demand is not positive
     */
    public FitnessCalculator(double[][] distanceMatrix, CandidateRepository repository, double beta) {
        if (distanceMatrix == null || distanceMatrix.length == 0) {
            throw new IllegalArgumentException("Distance matrix cannot be null or empty.");
        }
        if (repository == null) {
            throw new IllegalArgumentException("Repository cannot be null.");
        }
        if (beta <= 0) {
            throw new IllegalArgumentException("Beta must be greater than 0.");
        }

        this.distanceMatrix = distanceMatrix;
        this.repository = repository;
        this.beta = beta;
        this.totalSystemDemand = calculateTotalDemand();

        if (this.totalSystemDemand <= 0) {
            throw new IllegalStateException("Total system demand must be greater than 0.");
        }
    }

    /**
     * Computes the total system demand across all candidate grid points.
     *
     * @return total demand
     */
    private double calculateTotalDemand() {
        return repository.getAllCandidatesSorted().stream()
                .mapToDouble(CandidatePoint::getDemandScore)
                .sum();
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
     * the corresponding distance cost {@code distance^beta}.
     *
     * @param grid demand grid point
     * @param lockerIds selected locker candidate IDs
     * @return distance cost to the nearest selected locker
     * @throws IllegalStateException if a grid or locker ID cannot be mapped
     *                               to a matrix index
     */
    private double findDistanceCostToNearestLocker(CandidatePoint grid, List<Integer> lockerIds) {
        int gridIndex = repository.getIndexById(grid.getId());
        if (gridIndex < 0) {
            throw new IllegalStateException("Grid ID not found in repository index map: " + grid.getId());
        }

        double minDistance = Double.MAX_VALUE;

        for (int lockerId : lockerIds) {
            int lockerIndex = repository.getIndexById(lockerId);
            if (lockerIndex < 0) {
                throw new IllegalStateException("Locker ID not found in repository index map: " + lockerId);
            }

            double currentDistance = distanceMatrix[gridIndex][lockerIndex];
            if (currentDistance < minDistance) {
                minDistance = currentDistance;
            }
        }

        return Math.pow(minDistance, beta);
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
        List<Integer> lockerIds = individual.getChromosome();

        for (CandidatePoint grid : allGrids) {
            double distanceCost = findDistanceCostToNearestLocker(grid, lockerIds);
            weightedDistanceSum += grid.getDemandScore() * distanceCost;
        }

        double f1Score = weightedDistanceSum / totalSystemDemand;
        individual.setObjective1(f1Score);
    }

    /**
     * Evaluates the second objective value (f2), representing equity.
     *
     * <p>This objective is computed as the variance of mahalle-level weighted
     * mean accessibility costs. Lower values indicate more even service quality
     * across neighborhoods.</p>
     *
     * @param individual individual to evaluate
     */
    public void evaluateF2(Individual individual) {
        validateIndividual(individual);

        List<CandidatePoint> allGrids = repository.getAllCandidatesSorted();
        List<Integer> lockerIds = individual.getChromosome();

        Map<String, Double> mahalleWeightedCostSum = new HashMap<>();
        Map<String, Double> mahalleDemandSum = new HashMap<>();

        for (CandidatePoint grid : allGrids) {
            String mahalle = grid.getMahalleNameTurkish();
            if (mahalle == null || mahalle.isBlank()) {
                throw new IllegalStateException("Mahalle name is null or blank for grid ID: " + grid.getId());
            }

            double demand = grid.getDemandScore();
            double distanceCost = findDistanceCostToNearestLocker(grid, lockerIds);

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

        individual.setObjective2(variance);
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
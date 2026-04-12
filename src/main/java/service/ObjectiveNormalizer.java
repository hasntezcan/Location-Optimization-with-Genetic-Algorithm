package service;

import model.Individual;

import java.util.List;

/**
 * Normalizes objective values for multi-objective evaluation.
 *
 * <p>This class supports two different normalization modes:</p>
 *
 * <ul>
 *     <li><b>Dynamic normalization:</b> bounds are computed from the given population.</li>
 *     <li><b>Fixed-bound normalization:</b> externally supplied bounds are used.</li>
 * </ul>
 *
 * <p>The dynamic mode is useful inside the algorithm during evaluation and
 * density estimation. The fixed-bound mode is useful for final assessment,
 * where different generations must be compared in the same coordinate system.</p>
 */
public class ObjectiveNormalizer {

    /**
     * Normalizes the objective values of the given population using bounds
     * computed from that same population.
     *
     * @param population population whose objective values will be normalized
     * @throws IllegalArgumentException if the population is null or empty
     * @throws IllegalStateException if any individual has missing raw objectives
     */
    public void normalizePopulationObjectives(List<Individual> population) {
        if (population == null || population.isEmpty()) {
            throw new IllegalArgumentException("Population cannot be null or empty.");
        }

        double minF1 = Double.POSITIVE_INFINITY;
        double maxF1 = Double.NEGATIVE_INFINITY;
        double minF2 = Double.POSITIVE_INFINITY;
        double maxF2 = Double.NEGATIVE_INFINITY;

        for (Individual individual : population) {
            validateObjectives(individual);

            double f1 = individual.getObjective1();
            double f2 = individual.getObjective2();

            if (f1 < minF1) {
                minF1 = f1;
            }
            if (f1 > maxF1) {
                maxF1 = f1;
            }
            if (f2 < minF2) {
                minF2 = f2;
            }
            if (f2 > maxF2) {
                maxF2 = f2;
            }
        }

        normalizePopulationObjectives(population, minF1, maxF1, minF2, maxF2);
    }

    /**
     * Normalizes the objective values of the given population using externally
     * supplied fixed bounds.
     *
     * <p>Values are clamped into the {@code [0, 1]} interval so that later
     * assessment metrics such as hypervolume remain numerically stable.</p>
     *
     * @param population population whose objective values will be normalized
     * @param minObjective1 minimum bound for objective 1
     * @param maxObjective1 maximum bound for objective 1
     * @param minObjective2 minimum bound for objective 2
     * @param maxObjective2 maximum bound for objective 2
     * @throws IllegalArgumentException if the population is null or empty,
     *                                  or if a max bound is smaller than a min bound
     * @throws IllegalStateException if any individual has missing raw objectives
     */
    public void normalizePopulationObjectives(List<Individual> population,
                                              double minObjective1,
                                              double maxObjective1,
                                              double minObjective2,
                                              double maxObjective2) {
        if (population == null || population.isEmpty()) {
            throw new IllegalArgumentException("Population cannot be null or empty.");
        }

        if (maxObjective1 < minObjective1) {
            throw new IllegalArgumentException("maxObjective1 cannot be smaller than minObjective1.");
        }

        if (maxObjective2 < minObjective2) {
            throw new IllegalArgumentException("maxObjective2 cannot be smaller than minObjective2.");
        }

        for (Individual individual : population) {
            validateObjectives(individual);

            double normalizedF1 = normalizeAndClamp(
                    individual.getObjective1(),
                    minObjective1,
                    maxObjective1
            );

            double normalizedF2 = normalizeAndClamp(
                    individual.getObjective2(),
                    minObjective2,
                    maxObjective2
            );

            individual.setNormalizedObjective1(normalizedF1);
            individual.setNormalizedObjective2(normalizedF2);
        }
    }

    /**
     * Validates that an individual has both raw objectives assigned.
     *
     * @param individual individual to validate
     * @throws IllegalArgumentException if the individual is null
     * @throws IllegalStateException if any raw objective is missing
     */
    private void validateObjectives(Individual individual) {
        if (individual == null) {
            throw new IllegalArgumentException("Individual cannot be null.");
        }

        if (individual.getObjective1() == null) {
            throw new IllegalStateException("Objective1 is null.");
        }

        if (individual.getObjective2() == null) {
            throw new IllegalStateException("Objective2 is null.");
        }
    }

    /**
     * Applies min-max normalization and clamps the result to the {@code [0, 1]}
     * interval.
     *
     * <p>If {@code max == min}, the method returns {@code 0.0}.</p>
     *
     * @param value raw objective value
     * @param min lower bound
     * @param max upper bound
     * @return normalized and clamped value
     */
    private double normalizeAndClamp(double value, double min, double max) {
        if (Double.compare(max, min) == 0) {
            return 0.0;
        }

        double normalized = (value - min) / (max - min);

        if (normalized < 0.0) {
            return 0.0;
        }

        if (normalized > 1.0) {
            return 1.0;
        }

        return normalized;
    }
}
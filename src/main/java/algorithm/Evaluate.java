package algorithm;

import algorithm.helper.Dominance;
import model.Individual;
import service.FitnessCalculator;
import service.ObjectiveNormalizer;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Evaluates a merged SPEA2 population consisting of the current population
 * and the archive.
 *
 * <p>This class is responsible for the full evaluation pipeline of a SPEA2
 * generation step. It computes raw objectives, normalizes them, assigns
 * dominance-based strength and raw fitness values, estimates density in the
 * normalized objective space, and finally computes the total SPEA2 fitness.</p>
 */
public class Evaluate {

    private final FitnessCalculator fitnessCalculator;
    private final ObjectiveNormalizer objectiveNormalizer;
    private final Dominance dominance;

    /**
     * Creates an evaluation component with the required dependencies.
     *
     * @param fitnessCalculator raw objective calculator
     * @param objectiveNormalizer objective normalizer
     * @param dominance dominance comparison helper
     * @throws IllegalArgumentException if any dependency is {@code null}
     */
    public Evaluate(FitnessCalculator fitnessCalculator,
                    ObjectiveNormalizer objectiveNormalizer,
                    Dominance dominance) {
        if (fitnessCalculator == null) {
            throw new IllegalArgumentException("FitnessCalculator cannot be null.");
        }
        if (objectiveNormalizer == null) {
            throw new IllegalArgumentException("ObjectiveNormalizer cannot be null.");
        }
        if (dominance == null) {
            throw new IllegalArgumentException("Dominance cannot be null.");
        }

        this.fitnessCalculator = fitnessCalculator;
        this.objectiveNormalizer = objectiveNormalizer;
        this.dominance = dominance;
    }

    /**
     * Runs the full SPEA2 evaluation pipeline on the merged set of individuals.
     *
     * <p>The input population and archive are merged into a single list. The
     * returned list contains the same individual objects after objective and
     * fitness values have been assigned.</p>
     *
     * @param population current population
     * @param archive current archive
     * @return merged and fully evaluated individual list
     * @throws IllegalArgumentException if {@code population} is {@code null}
     */
    public List<Individual> run(List<Individual> population, List<Individual> archive) {
        if (population == null) {
            throw new IllegalArgumentException("Population cannot be null.");
        }

        List<Individual> merged = merge(population, archive);

        evaluateObjectives(merged);
        normalizeObjectives(merged);
        assignStrength(merged);
        assignRawFitness(merged);
        assignDensity(merged);
        assignTotalFitness(merged);

        return merged;
    }

    /**
     * Merges the population and archive into a single list.
     *
     * @param population current population
     * @param archive current archive, may be {@code null}
     * @return merged individual list
     */
    private List<Individual> merge(List<Individual> population, List<Individual> archive) {
        List<Individual> merged = new ArrayList<>(population);

        if (archive != null && !archive.isEmpty()) {
            merged.addAll(archive);
        }

        return merged;
    }

    /**
     * Evaluates raw objective values for all individuals.
     *
     * @param individuals individuals to evaluate
     */
    private void evaluateObjectives(List<Individual> individuals) {
        fitnessCalculator.evaluatePopulationObjectives(individuals);
    }

    /**
     * Normalizes objective values for all individuals.
     *
     * @param individuals individuals to normalize
     */
    private void normalizeObjectives(List<Individual> individuals) {
        objectiveNormalizer.normalizePopulationObjectives(individuals);
    }

    /**
     * Assigns the SPEA2 strength value to each individual.
     *
     * <p>The strength of an individual is the number of individuals it dominates
     * in the merged set.</p>
     *
     * @param individuals merged individual list
     */
    private void assignStrength(List<Individual> individuals) {
        for (Individual individual : individuals) {
            individual.setStrength(0);
        }

        for (int i = 0; i < individuals.size(); i++) {
            Individual current = individuals.get(i);
            int strength = 0;

            for (int j = 0; j < individuals.size(); j++) {
                if (i == j) {
                    continue;
                }

                if (dominance.dominates(current, individuals.get(j))) {
                    strength++;
                }
            }

            current.setStrength(strength);
        }
    }

    /**
     * Assigns the SPEA2 raw fitness value to each individual.
     *
     * <p>The raw fitness of an individual is the sum of the strength values
     * of all individuals that dominate it.</p>
     *
     * @param individuals merged individual list
     */
    private void assignRawFitness(List<Individual> individuals) {
        for (Individual individual : individuals) {
            individual.setRawFitness(0);
        }

        for (int i = 0; i < individuals.size(); i++) {
            Individual current = individuals.get(i);
            int rawFitness = 0;

            for (int j = 0; j < individuals.size(); j++) {
                if (i == j) {
                    continue;
                }

                Individual other = individuals.get(j);
                if (dominance.dominates(other, current)) {
                    rawFitness += other.getStrength();
                }
            }

            current.setRawFitness(rawFitness);
        }
    }

    /**
     * Assigns the SPEA2 density value to each individual.
     *
     * <p>Density is computed using the distance to the k-th nearest neighbor
     * in the normalized objective space, where k is chosen as the integer part
     * of the square root of the merged sample size.</p>
     *
     * <p>The density formula is:</p>
     *
     * <pre>
     * density = 1 / (sigma_k + 2)
     * </pre>
     *
     * @param individuals merged individual list
     */
    private void assignDensity(List<Individual> individuals) {
        int size = individuals.size();

        if (size <= 1) {
            for (Individual individual : individuals) {
                individual.setDensity(0.0);
            }
            return;
        }

        int k = (int) Math.sqrt(size);
        if (k < 1) {
            k = 1;
        }

        int effectiveK = Math.min(k, size - 1);

        for (int i = 0; i < size; i++) {
            Individual current = individuals.get(i);
            List<Double> distances = new ArrayList<>();

            for (int j = 0; j < size; j++) {
                if (i == j) {
                    continue;
                }

                Individual other = individuals.get(j);
                distances.add(distanceInNormalizedObjectiveSpace(current, other));
            }

            Collections.sort(distances);

            double sigmaK = distances.get(effectiveK - 1);
            double densityValue = 1.0 / (sigmaK + 2.0);

            current.setDensity(densityValue);
        }
    }

    /**
     * Assigns the final SPEA2 fitness value to each individual.
     *
     * <p>The total fitness is the sum of raw fitness and density.</p>
     *
     * @param individuals merged individual list
     */
    private void assignTotalFitness(List<Individual> individuals) {
        for (Individual individual : individuals) {
            double totalFitness = individual.getRawFitness() + individual.getDensity();
            individual.setTotalFitness(totalFitness);
        }
    }

    /**
     * Computes the Euclidean distance between two individuals in the normalized
     * objective space.
     *
     * @param a first individual
     * @param b second individual
     * @return normalized objective-space distance
     * @throws IllegalStateException if normalized objective values are missing
     */
    private double distanceInNormalizedObjectiveSpace(Individual a, Individual b) {
        if (a.getNormalizedObjective1() == null || a.getNormalizedObjective2() == null) {
            throw new IllegalStateException("Normalized objectives are missing for the first individual.");
        }

        if (b.getNormalizedObjective1() == null || b.getNormalizedObjective2() == null) {
            throw new IllegalStateException("Normalized objectives are missing for the second individual.");
        }

        double dx = a.getNormalizedObjective1() - b.getNormalizedObjective1();
        double dy = a.getNormalizedObjective2() - b.getNormalizedObjective2();

        return Math.sqrt(dx * dx + dy * dy);
    }
}
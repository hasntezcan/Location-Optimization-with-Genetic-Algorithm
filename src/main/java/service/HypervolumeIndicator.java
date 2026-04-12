package service;

import algorithm.helper.Pareto;
import model.Individual;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Computes the 2D hypervolume indicator in normalized objective space for a
 * bi-objective minimization problem.
 *
 * <p>This implementation assumes that normalized objective values are already
 * available and lie in the {@code [0, 1]} interval. A fixed reference point
 * slightly outside that interval, such as {@code (1.1, 1.1)}, is recommended.</p>
 */
public class HypervolumeIndicator {

    private final Pareto pareto;
    private final double referenceObjective1;
    private final double referenceObjective2;

    /**
     * Creates a normalized-space hypervolume indicator.
     *
     * @param pareto helper used to extract the non-dominated subset
     * @param referenceObjective1 reference point value for objective 1
     * @param referenceObjective2 reference point value for objective 2
     * @throws IllegalArgumentException if the Pareto helper is null
     *                                  or if reference coordinates are not positive
     */
    public HypervolumeIndicator(Pareto pareto,
                                double referenceObjective1,
                                double referenceObjective2) {
        if (pareto == null) {
            throw new IllegalArgumentException("Pareto cannot be null.");
        }

        if (referenceObjective1 <= 0.0 || referenceObjective2 <= 0.0) {
            throw new IllegalArgumentException("Reference point coordinates must be greater than 0.");
        }

        this.pareto = pareto;
        this.referenceObjective1 = referenceObjective1;
        this.referenceObjective2 = referenceObjective2;
    }

    /**
     * Computes the hypervolume of the unique non-dominated subset.
     *
     * @param individuals evaluated individuals with normalized objectives assigned
     * @return hypervolume value
     * @throws IllegalArgumentException if the input list is null or empty
     * @throws IllegalStateException if normalized objective values are missing
     */
    public double compute(List<Individual> individuals) {
        if (individuals == null || individuals.isEmpty()) {
            throw new IllegalArgumentException("Individual list cannot be null or empty.");
        }

        List<Individual> nonDominated = pareto.getNonDominated(individuals);
        List<Individual> uniqueNonDominated = deduplicateByChromosome(nonDominated);

        validateNormalizedObjectives(uniqueNonDominated);

        uniqueNonDominated.sort(Comparator.comparingDouble(Individual::getNormalizedObjective1));

        double hypervolume = 0.0;
        double currentUpperF2 = referenceObjective2;

        for (Individual individual : uniqueNonDominated) {
            double f1 = individual.getNormalizedObjective1();
            double f2 = individual.getNormalizedObjective2();

            if (f1 > referenceObjective1 || f2 > referenceObjective2) {
                throw new IllegalStateException(
                        "Reference point must be dominated by all normalized points."
                );
            }

            if (f2 < currentUpperF2) {
                double width = referenceObjective1 - f1;
                double height = currentUpperF2 - f2;
                hypervolume += width * height;
                currentUpperF2 = f2;
            }
        }

        return hypervolume;
    }

    /**
     * Computes the hypervolume ratio relative to the full reference rectangle.
     *
     * @param individuals evaluated individuals with normalized objectives assigned
     * @return hypervolume ratio
     */
    public double computeRatio(List<Individual> individuals) {
        double hypervolume = compute(individuals);
        double totalReferenceArea = referenceObjective1 * referenceObjective2;
        return hypervolume / totalReferenceArea;
    }

    /**
     * Returns the reference point value for objective 1.
     *
     * @return reference objective 1
     */
    public double getReferenceObjective1() {
        return referenceObjective1;
    }

    /**
     * Returns the reference point value for objective 2.
     *
     * @return reference objective 2
     */
    public double getReferenceObjective2() {
        return referenceObjective2;
    }

    /**
     * Deduplicates individuals using canonical chromosome equality.
     *
     * @param individuals input individuals
     * @return unique individuals preserving first occurrence order
     */
    private List<Individual> deduplicateByChromosome(List<Individual> individuals) {
        List<Individual> unique = new ArrayList<>();
        Set<String> seen = new HashSet<>();

        for (Individual individual : individuals) {
            String key = individual.getChromosome().toString();
            if (seen.add(key)) {
                unique.add(individual);
            }
        }

        return unique;
    }

    /**
     * Validates that normalized objective values are present.
     *
     * @param individuals individuals to validate
     * @throws IllegalStateException if normalized objective values are missing
     */
    private void validateNormalizedObjectives(List<Individual> individuals) {
        for (Individual individual : individuals) {
            if (individual.getNormalizedObjective1() == null) {
                throw new IllegalStateException("Normalized objective1 is missing.");
            }

            if (individual.getNormalizedObjective2() == null) {
                throw new IllegalStateException("Normalized objective2 is missing.");
            }
        }
    }
}
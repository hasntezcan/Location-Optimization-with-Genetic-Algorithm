package algorithm.helper;

import model.Individual;

/**
 * Provides dominance comparison for individuals in a bi-objective
 * minimization problem.
 *
 * <p>An individual {@code a} dominates individual {@code b} if it is
 * no worse in all objectives and strictly better in at least one
 * objective.</p>
 */
public class Dominance {

    /**
     * Returns whether individual {@code a} dominates individual {@code b}.
     *
     * <p>This implementation assumes that both objectives are minimized.</p>
     *
     * @param a first individual
     * @param b second individual
     * @return {@code true} if {@code a} dominates {@code b}; {@code false} otherwise
     * @throws IllegalArgumentException if either individual is {@code null}
     * @throws IllegalStateException if any raw objective value is missing
     */
    public boolean dominates(Individual a, Individual b) {
        validateIndividual(a, "first");
        validateIndividual(b, "second");

        double a1 = a.getObjective1();
        double a2 = a.getObjective2();
        double b1 = b.getObjective1();
        double b2 = b.getObjective2();

        boolean noWorseInAll = a1 <= b1 && a2 <= b2;
        boolean betterInAtLeastOne = a1 < b1 || a2 < b2;

        return noWorseInAll && betterInAtLeastOne;
    }

    /**
     * Validates that an individual exists and has evaluated raw objectives.
     *
     * @param individual individual to validate
     * @param positionLabel textual label used in exception messages
     * @throws IllegalArgumentException if the individual is {@code null}
     * @throws IllegalStateException if any raw objective value is missing
     */
    private void validateIndividual(Individual individual, String positionLabel) {
        if (individual == null) {
            throw new IllegalArgumentException("The " + positionLabel + " individual cannot be null.");
        }

        if (individual.getObjective1() == null) {
            throw new IllegalStateException(
                    "Objective1 is null for the " + positionLabel + " individual."
            );
        }

        if (individual.getObjective2() == null) {
            throw new IllegalStateException(
                    "Objective2 is null for the " + positionLabel + " individual."
            );
        }
    }
}
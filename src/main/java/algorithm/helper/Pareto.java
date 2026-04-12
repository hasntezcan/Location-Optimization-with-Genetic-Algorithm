package algorithm.helper;

import model.Individual;

import java.util.ArrayList;
import java.util.List;

/**
 * Extracts Pareto-optimal individuals from a population.
 *
 * <p>This helper identifies the non-dominated subset of a given individual list
 * under a bi-objective minimization setting. Dominance checks are delegated to
 * the {@link Dominance} helper.</p>
 */
public class Pareto {

    private final Dominance dominance;

    /**
     * Creates a Pareto helper with the given dominance comparator.
     *
     * @param dominance dominance helper
     * @throws IllegalArgumentException if {@code dominance} is {@code null}
     */
    public Pareto(Dominance dominance) {
        if (dominance == null) {
            throw new IllegalArgumentException("Dominance cannot be null.");
        }

        this.dominance = dominance;
    }

    /**
     * Returns the non-dominated subset of the given individual list.
     *
     * <p>An individual is included in the result if no other individual in the
     * same list dominates it.</p>
     *
     * @param individuals input individual list
     * @return non-dominated individuals
     * @throws IllegalArgumentException if {@code individuals} is {@code null}
     */
    public List<Individual> getNonDominated(List<Individual> individuals) {
        if (individuals == null) {
            throw new IllegalArgumentException("Individual list cannot be null.");
        }

        List<Individual> nonDominated = new ArrayList<>();

        for (int i = 0; i < individuals.size(); i++) {
            Individual current = individuals.get(i);

            if (!isDominated(current, individuals, i)) {
                nonDominated.add(current);
            }
        }

        return nonDominated;
    }

    /**
     * Returns whether the given individual is dominated by any other individual
     * in the provided list.
     *
     * @param target individual to test
     * @param individuals reference population
     * @param targetIndex index of the target individual in the list
     * @return {@code true} if the target is dominated; {@code false} otherwise
     */
    private boolean isDominated(Individual target, List<Individual> individuals, int targetIndex) {
        for (int i = 0; i < individuals.size(); i++) {
            if (i == targetIndex) {
                continue;
            }

            if (dominance.dominates(individuals.get(i), target)) {
                return true;
            }
        }

        return false;
    }
}
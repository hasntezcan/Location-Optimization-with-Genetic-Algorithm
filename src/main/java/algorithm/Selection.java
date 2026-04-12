package algorithm;

import model.Individual;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Performs parent selection for the genetic algorithm using binary tournament
 * selection on the current archive.
 *
 * <p>The tournament comparison is based on SPEA2 total fitness, where lower
 * values are better. If two individuals have the same total fitness, raw
 * fitness is used as a tie-breaker. If they are still equal, density is used
 * as the final tie-breaker.</p>
 */
public class Selection {

    private final Random random;

    /**
     * Creates a selection component with a default random number generator.
     */
    public Selection() {
        this.random = new Random();
    }

    /**
     * Creates a selection component with a fixed random seed.
     *
     * @param seed random seed
     */
    public Selection(long seed) {
        this.random = new Random(seed);
    }

    /**
     * Selects a mating pool from the given archive using repeated binary
     * tournament selection.
     *
     * @param archive current archive used as the parent source
     * @param matingPoolSize number of parents to select
     * @return selected mating pool
     * @throws IllegalArgumentException if the archive is null or empty,
     *                                  or if {@code matingPoolSize <= 0}
     */
    public List<Individual> run(List<Individual> archive, int matingPoolSize) {
        if (archive == null || archive.isEmpty()) {
            throw new IllegalArgumentException("Archive cannot be null or empty.");
        }

        if (matingPoolSize <= 0) {
            throw new IllegalArgumentException("Mating pool size must be greater than 0.");
        }

        validateArchiveIndividuals(archive);

        List<Individual> matingPool = new ArrayList<>();

        for (int i = 0; i < matingPoolSize; i++) {
            Individual parent = binaryTournament(archive);
            matingPool.add(parent);
        }

        return matingPool;
    }

    /**
     * Runs one binary tournament on the archive and returns the selected winner.
     *
     * @param archive archive used for tournament selection
     * @return tournament winner
     */
    private Individual binaryTournament(List<Individual> archive) {
        int firstIndex = random.nextInt(archive.size());
        int secondIndex = random.nextInt(archive.size());

        while (archive.size() > 1 && secondIndex == firstIndex) {
            secondIndex = random.nextInt(archive.size());
        }

        Individual first = archive.get(firstIndex);
        Individual second = archive.get(secondIndex);

        return chooseBetter(first, second);
    }

    /**
     * Returns the better individual between two candidates.
     *
     * <p>Smaller total fitness is preferred. If total fitness values are equal,
     * smaller raw fitness is preferred. If raw fitness is also equal, smaller
     * density is preferred.</p>
     *
     * @param first first candidate
     * @param second second candidate
     * @return better candidate
     */
    private Individual chooseBetter(Individual first, Individual second) {
        if (first.getTotalFitness() < second.getTotalFitness()) {
            return first;
        }

        if (first.getTotalFitness() > second.getTotalFitness()) {
            return second;
        }

        if (first.getRawFitness() < second.getRawFitness()) {
            return first;
        }

        if (first.getRawFitness() > second.getRawFitness()) {
            return second;
        }

        if (first.getDensity() < second.getDensity()) {
            return first;
        }

        if (first.getDensity() > second.getDensity()) {
            return second;
        }

        return first;
    }

    /**
     * Validates that all archive individuals have the required SPEA2 fitness
     * fields assigned before selection.
     *
     * @param archive archive to validate
     * @throws IllegalStateException if any individual has missing fitness values
     */
    private void validateArchiveIndividuals(List<Individual> archive) {
        for (Individual individual : archive) {
            if (individual == null) {
                throw new IllegalStateException("Archive contains a null individual.");
            }

            if (Double.isNaN(individual.getTotalFitness()) || Double.isInfinite(individual.getTotalFitness())) {
                throw new IllegalStateException("Archive contains an individual with invalid total fitness.");
            }
        }
    }
}
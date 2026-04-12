import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * Creates the initial population for the genetic algorithm.
 * Each generated {@link Individual} contains a random chromosome made of
 * unique candidate point IDs.
 */
public class PopulationInitializer {

    private final Random random;

    /**
     * Creates a population initializer with a default random number generator.
     */
    public PopulationInitializer() {
        this.random = new Random();
    }

    /**
     * Initializes a population with randomly generated individuals.
     * Each individual contains exactly {@code k} candidate IDs selected from the
     * given candidate ID list without duplicates inside the same chromosome.
     *
     * @param candidateIds available candidate point IDs
     * @param k number of selected candidate points in each chromosome
     * @param populationSize number of individuals to create
     * @return initialized population
     * @throws IllegalArgumentException if {@code candidateIds} is null or empty,
     *                                  {@code k} is not positive,
     *                                  {@code populationSize} is not positive,
     *                                  or {@code k} is greater than the number of candidate IDs
     */
    public List<Individual> initializePopulation(List<Integer> candidateIds, int k, int populationSize) {
        if (candidateIds == null || candidateIds.isEmpty()) {
            throw new IllegalArgumentException("Candidate ID list cannot be null or empty.");
        }

        if (k <= 0) {
            throw new IllegalArgumentException("k must be greater than 0.");
        }

        if (populationSize <= 0) {
            throw new IllegalArgumentException("Population size must be greater than 0.");
        }

        if (k > candidateIds.size()) {
            throw new IllegalArgumentException("k cannot be greater than the number of available candidate IDs.");
        }

        List<Individual> population = new ArrayList<>();

        for (int i = 0; i < populationSize; i++) {
            List<Integer> chromosome = generateRandomChromosome(candidateIds, k);
            population.add(new Individual(chromosome));
        }

        return population;
    }

    /**
     * Generates a random chromosome by shuffling the available candidate IDs and
     * taking the first {@code k} IDs.
     *
     * @param candidateIds available candidate point IDs
     * @param k number of selected candidate points in the chromosome
     * @return random chromosome containing {@code k} candidate IDs
     */
    private List<Integer> generateRandomChromosome(List<Integer> candidateIds, int k) {
        List<Integer> shuffledIds = new ArrayList<>(candidateIds);
        Collections.shuffle(shuffledIds, random);

        return new ArrayList<>(shuffledIds.subList(0, k));
    }
}

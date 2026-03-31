import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

public class PopulationInitializer {

    private final Random random;

    public PopulationInitializer() {
        this.random = new Random();
    }

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

    private List<Integer> generateRandomChromosome(List<Integer> candidateIds, int k) {
        List<Integer> shuffledIds = new ArrayList<>(candidateIds);
        Collections.shuffle(shuffledIds, random);

        return new ArrayList<>(shuffledIds.subList(0, k));
    }
}
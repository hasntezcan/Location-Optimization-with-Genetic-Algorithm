import java.io.IOException;
import java.util.List;

public class Main {

    public static void main(String[] args) {
        CandidateRepository repository = new CandidateRepository();
        CsvLoader loader = new CsvLoader();
        PopulationInitializer initializer = new PopulationInitializer();

        try {
            loader.loadCandidates("data/candidate_points.csv", repository);

            System.out.println("Total candidates loaded: " + repository.size());

            int k = 5;
            int populationSize = 100;

            List<Integer> candidateIds = repository.getAllCandidateIds();
            List<Individual> population = initializer.initializePopulation(candidateIds, k, populationSize);

            System.out.println("Population created: " + population.size());

            for (int i = 0; i < 100; i++) {
                System.out.println(population.get(i));
            }

        } catch (IOException e) {
            System.out.println("Error while reading CSV file: " + e.getMessage());
        } catch (IllegalArgumentException e) {
            System.out.println("Input error: " + e.getMessage());
        }
    }
}
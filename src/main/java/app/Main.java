package app;

import algorithm.Evaluate;
import algorithm.Selection;
import algorithm.Survivor;
import algorithm.Variation;
import algorithm.helper.Dominance;
import algorithm.helper.Pareto;
import algorithm.helper.Truncation;
import config.GAParameters;
import io.CsvLoader;
import io.DistanceMatrixLoader;
import model.CandidateRepository;
import model.Individual;
import service.FitnessCalculator;
import service.HypervolumeIndicator;
import service.ObjectiveNormalizer;
import service.PopulationInitializer;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Entry point of the location optimization project.
 *
 * <p>This class runs the SPEA2 workflow and evaluates the initial and final
 * archives using hypervolume in a shared normalized objective space that is
 * built from all raw objective values observed across the full run.</p>
 */
public class Main {

    /**
     * Runs the SPEA2 optimization workflow.
     *
     * @param args command-line arguments, currently unused
     */
    public static void main(String[] args) {
        long startTimeNs = System.nanoTime();

        CandidateRepository repository = new CandidateRepository();
        CsvLoader csvLoader = new CsvLoader();
        PopulationInitializer populationInitializer = new PopulationInitializer();
        DistanceMatrixLoader distanceMatrixLoader = new DistanceMatrixLoader();

        try {
            // 1. Load candidate data
            csvLoader.loadCandidates("data/candidate_points.csv", repository);
            repository.finalizeRepository();

            System.out.println("Total candidates loaded: " + repository.size());

            // 2. Load distance matrix
            double[][] distanceMatrix =
                    distanceMatrixLoader.loadDistanceMatrix("data/kadikoy_distance_meters_nxn.npy");

            if (distanceMatrix.length != repository.size()) {
                throw new IllegalStateException(
                        "Distance matrix row count (" + distanceMatrix.length +
                        ") does not match repository size (" + repository.size() + ")."
                );
            }

            if (distanceMatrix[0].length != repository.size()) {
                throw new IllegalStateException(
                        "Distance matrix column count (" + distanceMatrix[0].length +
                        ") does not match repository size (" + repository.size() + ")."
                );
            }

            System.out.println(
                    "Distance matrix loaded: " +
                    distanceMatrix.length + " x " + distanceMatrix[0].length
            );

            // 3. GA / SPEA2 parameters from central configuration
            int k = GAParameters.K;
            int populationSize = GAParameters.POPULATION_SIZE;
            int archiveSize = GAParameters.ARCHIVE_SIZE;
            int maxGenerations = GAParameters.MAX_GENERATIONS;
            double beta = GAParameters.BETA;
            double crossoverRate = GAParameters.CROSSOVER_RATE;
            double mutationRate = GAParameters.MUTATION_RATE;

            // Hypervolume reference point in normalized space
            double referenceObjective1 = GAParameters.REFERENCE_POINT_F1;
            double referenceObjective2 = GAParameters.REFERENCE_POINT_F2;

            // 4. Initialize population
            List<Integer> candidateIds = repository.getAllCandidateIds();
            List<Individual> population =
                    populationInitializer.initializePopulation(candidateIds, k, populationSize);

            List<Individual> archive = new ArrayList<>();

            System.out.println("Initial population created: " + population.size());
            System.out.println("Initial archive created: " + archive.size());

            // 5. Build dependencies
            FitnessCalculator fitnessCalculator =
                    new FitnessCalculator(distanceMatrix, repository, beta);

            ObjectiveNormalizer objectiveNormalizer = new ObjectiveNormalizer();
            Dominance dominance = new Dominance();
            Pareto pareto = new Pareto(dominance);
            Truncation truncation = new Truncation();

            Evaluate evaluate = new Evaluate(
                    fitnessCalculator,
                    objectiveNormalizer,
                    dominance
            );

            Survivor survivor = new Survivor(
                    pareto,
                    truncation
            );

            Selection selection = new Selection();
            Variation variation = new Variation();

            HypervolumeIndicator hypervolumeIndicator = new HypervolumeIndicator(
                    pareto,
                    referenceObjective1,
                    referenceObjective2
            );

            // 6. Global raw objective bounds for final assessment
            double globalMinF1 = Double.POSITIVE_INFINITY;
            double globalMaxF1 = Double.NEGATIVE_INFINITY;
            double globalMinF2 = Double.POSITIVE_INFINITY;
            double globalMaxF2 = Double.NEGATIVE_INFINITY;

            // 7. Initial evaluation and archive creation
            List<Individual> evaluated = evaluate.run(population, archive);
            double[] updatedBounds = updateGlobalObjectiveBounds(
                    globalMinF1,
                    globalMaxF1,
                    globalMinF2,
                    globalMaxF2,
                    evaluated
            );
            globalMinF1 = updatedBounds[0];
            globalMaxF1 = updatedBounds[1];
            globalMinF2 = updatedBounds[2];
            globalMaxF2 = updatedBounds[3];

            archive = survivor.run(evaluated, archiveSize);

            List<Individual> initialArchiveSnapshot = deepCopyIndividuals(archive);

            System.out.println("Generation 0 completed.");
            System.out.println("Evaluated individual count: " + evaluated.size());
            System.out.println("Archive size: " + archive.size());

            printArchive("INITIAL ARCHIVE", initialArchiveSnapshot);

            // 8. Main SPEA2 loop
            for (int generation = 1; generation <= maxGenerations; generation++) {
                List<Individual> matingPool = selection.run(archive, populationSize);

                population = variation.run(
                        matingPool,
                        candidateIds,
                        populationSize,
                        k,
                        crossoverRate,
                        mutationRate
                );

                evaluated = evaluate.run(population, archive);

                updatedBounds = updateGlobalObjectiveBounds(
                        globalMinF1,
                        globalMaxF1,
                        globalMinF2,
                        globalMaxF2,
                        evaluated
                );
                globalMinF1 = updatedBounds[0];
                globalMaxF1 = updatedBounds[1];
                globalMinF2 = updatedBounds[2];
                globalMaxF2 = updatedBounds[3];

                archive = survivor.run(evaluated, archiveSize);

                double bestF1 = archive.stream()
                        .mapToDouble(ind -> ind.getObjective1())
                        .min().orElse(Double.NaN);
                double bestF2 = archive.stream()
                        .mapToDouble(ind -> ind.getObjective2())
                        .min().orElse(Double.NaN);

                System.out.println("Generation " + generation + " completed.");
                System.out.println("Population size: " + population.size());
                System.out.println("Archive size   : " + archive.size());
                System.out.printf("  Best f1      : %.6f%n", bestF1);
                System.out.printf("  Best f2      : %.6f%n", bestF2);
                System.out.println("--------------------------------------------");
            }

            // 9. Final archive snapshot
            List<Individual> finalArchiveSnapshot = deepCopyIndividuals(archive);

            printArchive("FINAL ARCHIVE", finalArchiveSnapshot);

            // 10. Apply the same global normalization to both initial and final archives
            objectiveNormalizer.normalizePopulationObjectives(
                    initialArchiveSnapshot,
                    globalMinF1,
                    globalMaxF1,
                    globalMinF2,
                    globalMaxF2
            );

            objectiveNormalizer.normalizePopulationObjectives(
                    finalArchiveSnapshot,
                    globalMinF1,
                    globalMaxF1,
                    globalMinF2,
                    globalMaxF2
            );

            // 11. Compute comparable hypervolume values
            double initialHypervolume = hypervolumeIndicator.compute(initialArchiveSnapshot);
            double initialHypervolumeRatio = hypervolumeIndicator.computeRatio(initialArchiveSnapshot);

            double finalHypervolume = hypervolumeIndicator.compute(finalArchiveSnapshot);
            double finalHypervolumeRatio = hypervolumeIndicator.computeRatio(finalArchiveSnapshot);

            // 12. Print assessment summary
            System.out.println("============== GLOBAL ASSESSMENT BOUNDS ==============");
            System.out.println("Global min f1 : " + globalMinF1);
            System.out.println("Global max f1 : " + globalMaxF1);
            System.out.println("Global min f2 : " + globalMinF2);
            System.out.println("Global max f2 : " + globalMaxF2);

            System.out.println("============== HYPERVOLUME ==============");
            System.out.println("Reference point           : (" +
                    hypervolumeIndicator.getReferenceObjective1() + ", " +
                    hypervolumeIndicator.getReferenceObjective2() + ")");
            System.out.println("Initial hypervolume       : " + initialHypervolume);
            System.out.println("Initial hypervolume ratio : " + initialHypervolumeRatio);
            System.out.println("Final hypervolume         : " + finalHypervolume);
            System.out.println("Final hypervolume ratio   : " + finalHypervolumeRatio);
            System.out.println("Hypervolume improvement   : " + (finalHypervolume - initialHypervolume));
            System.out.println("HV ratio improvement      : " + (finalHypervolumeRatio - initialHypervolumeRatio));

            long endTimeNs = System.nanoTime();
            double runtimeSeconds = (endTimeNs - startTimeNs) / 1_000_000_000.0;

            System.out.println("============== RUNTIME ==============");
            System.out.println("Total runtime (seconds): " + runtimeSeconds);

        } catch (IOException e) {
            System.out.println("I/O error: " + e.getMessage());
        } catch (IllegalArgumentException | IllegalStateException e) {
            System.out.println("Runtime error: " + e.getMessage());
        } catch (Exception e) {
            System.out.println("Unexpected error: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Updates the global raw objective bounds using the given evaluated population.
     *
     * @param currentMinF1 current global minimum of objective 1
     * @param currentMaxF1 current global maximum of objective 1
     * @param currentMinF2 current global minimum of objective 2
     * @param currentMaxF2 current global maximum of objective 2
     * @param individuals evaluated individuals
     * @return updated bounds in the order:
     *         minF1, maxF1, minF2, maxF2
     */
    private static double[] updateGlobalObjectiveBounds(double currentMinF1,
                                                        double currentMaxF1,
                                                        double currentMinF2,
                                                        double currentMaxF2,
                                                        List<Individual> individuals) {
        for (Individual individual : individuals) {
            if (individual.getObjective1() == null || individual.getObjective2() == null) {
                throw new IllegalStateException("Raw objectives must be assigned before updating bounds.");
            }

            double f1 = individual.getObjective1();
            double f2 = individual.getObjective2();

            if (f1 < currentMinF1) {
                currentMinF1 = f1;
            }
            if (f1 > currentMaxF1) {
                currentMaxF1 = f1;
            }
            if (f2 < currentMinF2) {
                currentMinF2 = f2;
            }
            if (f2 > currentMaxF2) {
                currentMaxF2 = f2;
            }
        }

        return new double[]{currentMinF1, currentMaxF1, currentMinF2, currentMaxF2};
    }

    /**
     * Creates deep copies of the given individuals.
     *
     * @param individuals individuals to copy
     * @return deep-copied individual list
     */
    private static List<Individual> deepCopyIndividuals(List<Individual> individuals) {
        List<Individual> copies = new ArrayList<>();

        for (Individual original : individuals) {
            Individual copy = new Individual(new ArrayList<>(original.getChromosome()));
            copy.setObjective1(original.getObjective1());
            copy.setObjective2(original.getObjective2());
            copy.setNormalizedObjective1(original.getNormalizedObjective1());
            copy.setNormalizedObjective2(original.getNormalizedObjective2());
            copy.setStrength(original.getStrength());
            copy.setRawFitness(original.getRawFitness());
            copy.setDensity(original.getDensity());
            copy.setTotalFitness(original.getTotalFitness());
            copies.add(copy);
        }

        return copies;
    }

    /**
     * Prints the contents of an archive.
     *
     * @param title title to print before the archive
     * @param archive archive to print
     */
    private static void printArchive(String title, List<Individual> archive) {
        System.out.println("============== " + title + " ==============");

        for (int i = 0; i < archive.size(); i++) {
            Individual individual = archive.get(i);

            System.out.println("Archive Individual #" + (i + 1));
            System.out.println("Chromosome    : " + individual.getChromosome());
            System.out.println("f1            : " + individual.getObjective1());
            System.out.println("f2            : " + individual.getObjective2());
            System.out.println("norm f1       : " + individual.getNormalizedObjective1());
            System.out.println("norm f2       : " + individual.getNormalizedObjective2());
            System.out.println("strength      : " + individual.getStrength());
            System.out.println("raw fitness   : " + individual.getRawFitness());
            System.out.println("density       : " + individual.getDensity());
            System.out.println("total fitness : " + individual.getTotalFitness());
            System.out.println("--------------------------------------------------");
        }
    }
}
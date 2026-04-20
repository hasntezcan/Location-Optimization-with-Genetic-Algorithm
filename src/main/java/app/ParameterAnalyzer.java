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

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Performs a full-factorial parameter grid search for the SPEA2 parcel locker
 * optimization pipeline.
 *
 * <p>This class is a separate execution path that does NOT modify or override
 * the main application flow in {@link Main}. It systematically varies key
 * hyperparameters (K, mutation rate, crossover rate, population size) while
 * keeping total function evaluations constant for fair comparison.</p>
 *
 * <h3>Run with:</h3>
 * <pre>
 *   mvn compile exec:java -Dexec.mainClass=app.ParameterAnalyzer
 * </pre>
 */
public class ParameterAnalyzer {

    // ---------------------------------------------------------------
    //  Grid definitions
    // ---------------------------------------------------------------

    /** Number of locker locations per chromosome. */
    private static final int[] K_VALUES = {3, 5, 7};

    /** Mutation rate grid. */
    private static final double[] MUTATION_RATES = {0.05, 0.10, 0.20, 0.30, 0.40};

    /** Crossover rate grid. */
    private static final double[] CROSSOVER_RATES = {0.7, 0.9};

    /** Population size grid (archive size = popSize / 2). */
    private static final int[] POPULATION_SIZES = {50, 100, 200};

    /** Random seeds for repeated runs. */
    private static final long[] SEEDS = {42L, 123L, 7L};

    /**
     * Fixed total function evaluations budget.
     * <p>
     * Derived from the largest population config:
     * PopSize=200, ArchiveSize=100, Generations=50
     * → 200 + 50 × (200 + 100) = 15,200
     * </p>
     */
    private static final int TOTAL_EVALUATION_BUDGET = 15_200;

    /** Distance-decay exponent (problem constant, not tuned). */
    private static final double BETA = GAParameters.BETA;

    /** HV reference point in normalized space. */
    private static final double HV_REFERENCE = 1.1;

    /** Padding factor applied to observed bounds for HV normalization. */
    private static final double NORMALIZATION_PADDING = 0.10;

    // ---------------------------------------------------------------
    //  Output
    // ---------------------------------------------------------------

    private static final Path OUTPUT_DIRECTORY = Paths.get("output");
    private static final Path RESULTS_CSV = OUTPUT_DIRECTORY.resolve("parameter_analysis_results.csv");

    private static final String CSV_HEADER = String.join(",",
            "Run_ID",
            "Seed",
            "K",
            "Population_Size",
            "Archive_Size",
            "Max_Generations",
            "Crossover_Rate",
            "Mutation_Rate",
            "Total_Evaluations",
            "Final_HV",
            "Final_HV_Ratio",
            "Final_ND_Count",
            "Final_Best_F1",
            "Final_Best_F2",
            "Runtime_ms"
    );

    // ---------------------------------------------------------------
    //  Main entry
    // ---------------------------------------------------------------

    public static void main(String[] args) {
        try {
            Files.createDirectories(OUTPUT_DIRECTORY);

            // 1. Load shared data (loaded once, reused across all runs)
            CandidateRepository repository = new CandidateRepository();
            CsvLoader csvLoader = new CsvLoader();
            csvLoader.loadCandidates("data/candidate_points.csv", repository);
            repository.finalizeRepository();

            double[][] distanceMatrix =
                    new DistanceMatrixLoader().loadDistanceMatrix("data/kadikoy_distance_meters_nxn.npy");

            validateMatrix(distanceMatrix, repository);

            List<Integer> candidateIds = repository.getAllCandidateIds();

            System.out.println("=== SPEA2 Parameter Analysis ===");
            System.out.println("Candidates loaded     : " + repository.size());
            System.out.println("Evaluation budget     : " + TOTAL_EVALUATION_BUDGET);
            System.out.println("K values              : " + formatArray(K_VALUES));
            System.out.println("Mutation rates        : " + formatArray(MUTATION_RATES));
            System.out.println("Crossover rates       : " + formatArray(CROSSOVER_RATES));
            System.out.println("Population sizes      : " + formatArray(POPULATION_SIZES));
            System.out.println("Seeds per config      : " + SEEDS.length);

            int totalConfigs = K_VALUES.length * MUTATION_RATES.length
                    * CROSSOVER_RATES.length * POPULATION_SIZES.length;
            int totalRuns = totalConfigs * SEEDS.length;
            System.out.println("Total configurations  : " + totalConfigs);
            System.out.println("Total runs            : " + totalRuns);
            System.out.println();

            // 2. Run grid search
            List<String> resultRows = new ArrayList<>();
            int runId = 0;

            for (int k : K_VALUES) {
                for (int popSize : POPULATION_SIZES) {
                    int archiveSize = popSize / 2;
                    int maxGenerations = computeMaxGenerations(popSize, archiveSize);

                    for (double crossoverRate : CROSSOVER_RATES) {
                        for (double mutationRate : MUTATION_RATES) {
                            for (long seed : SEEDS) {
                                runId++;
                                System.out.printf(
                                        "[Run %3d/%d] K=%d  Pop=%3d  Arc=%3d  Gen=%3d  Cx=%.2f  Mut=%.2f  Seed=%d%n",
                                        runId, totalRuns, k, popSize, archiveSize,
                                        maxGenerations, crossoverRate, mutationRate, seed
                                );

                                String row = executeSingleRun(
                                        runId, seed, k, popSize, archiveSize,
                                        maxGenerations, crossoverRate, mutationRate,
                                        distanceMatrix, repository, candidateIds
                                );
                                resultRows.add(row);
                            }
                        }
                    }
                }
            }

            // 3. Write CSV
            writeCsv(resultRows);
            System.out.println();
            System.out.println("=== Analysis Complete ===");
            System.out.println("Results written to: " + RESULTS_CSV.toAbsolutePath());

        } catch (IOException e) {
            System.err.println("I/O error: " + e.getMessage());
            e.printStackTrace();
        } catch (Exception e) {
            System.err.println("Unexpected error: " + e.getMessage());
            e.printStackTrace();
        }
    }

    // ---------------------------------------------------------------
    //  Single SPEA2 run
    // ---------------------------------------------------------------

    /**
     * Executes a single SPEA2 run with the given parameters and returns a
     * CSV-formatted result row.
     */
    private static String executeSingleRun(
            int runId, long seed, int k, int populationSize, int archiveSize,
            int maxGenerations, double crossoverRate, double mutationRate,
            double[][] distanceMatrix, CandidateRepository repository,
            List<Integer> candidateIds) {

        long startNs = System.nanoTime();

        // Build seeded components
        PopulationInitializer populationInitializer = new PopulationInitializer();
        FitnessCalculator fitnessCalculator =
                new FitnessCalculator(distanceMatrix, repository, BETA);

        ObjectiveNormalizer objectiveNormalizer = new ObjectiveNormalizer();
        Dominance dominance = new Dominance();
        Pareto pareto = new Pareto(dominance);
        Truncation truncation = new Truncation();

        Evaluate evaluate = new Evaluate(fitnessCalculator, objectiveNormalizer, dominance);
        Survivor survivor = new Survivor(pareto, truncation);
        Selection selection = new Selection(seed);
        Variation variation = new Variation(seed);

        // Initialize population
        List<Individual> population =
                populationInitializer.initializePopulation(candidateIds, k, populationSize);
        List<Individual> archive = new ArrayList<>();

        // Tracking global objective bounds for this run
        double globalMinF1 = Double.POSITIVE_INFINITY;
        double globalMaxF1 = Double.NEGATIVE_INFINITY;
        double globalMinF2 = Double.POSITIVE_INFINITY;
        double globalMaxF2 = Double.NEGATIVE_INFINITY;

        // Generation 0
        List<Individual> evaluated = evaluate.run(population, archive);
        archive = survivor.run(evaluated, archiveSize);

        // Update bounds from generation 0
        double[] bounds = updateBounds(evaluated, globalMinF1, globalMaxF1, globalMinF2, globalMaxF2);
        globalMinF1 = bounds[0];
        globalMaxF1 = bounds[1];
        globalMinF2 = bounds[2];
        globalMaxF2 = bounds[3];

        // Main evolutionary loop
        for (int gen = 1; gen <= maxGenerations; gen++) {
            List<Individual> matingPool = selection.run(archive, populationSize);

            population = variation.run(
                    matingPool, candidateIds, populationSize, k,
                    crossoverRate, mutationRate
            );

            evaluated = evaluate.run(population, archive);
            archive = survivor.run(evaluated, archiveSize);

            bounds = updateBounds(evaluated, globalMinF1, globalMaxF1, globalMinF2, globalMaxF2);
            globalMinF1 = bounds[0];
            globalMaxF1 = bounds[1];
            globalMinF2 = bounds[2];
            globalMaxF2 = bounds[3];
        }

        // Compute final metrics
        long runtimeMs = (System.nanoTime() - startNs) / 1_000_000;

        // Per-run normalization with padding
        double paddedMinF1 = globalMinF1;
        double paddedMaxF1 = globalMaxF1 + NORMALIZATION_PADDING * (globalMaxF1 - globalMinF1);
        double paddedMinF2 = globalMinF2;
        double paddedMaxF2 = globalMaxF2 + NORMALIZATION_PADDING * (globalMaxF2 - globalMinF2);

        // Handle degenerate case where all values are identical
        if (Double.compare(paddedMaxF1, paddedMinF1) == 0) {
            paddedMaxF1 = paddedMinF1 + 1.0;
        }
        if (Double.compare(paddedMaxF2, paddedMinF2) == 0) {
            paddedMaxF2 = paddedMinF2 + 1.0;
        }

        // Normalize final archive for HV computation
        List<Individual> finalArchive = deepCopyIndividuals(archive);
        objectiveNormalizer.normalizePopulationObjectives(
                finalArchive, paddedMinF1, paddedMaxF1, paddedMinF2, paddedMaxF2
        );

        // Compute HV
        HypervolumeIndicator hvIndicator = new HypervolumeIndicator(pareto, HV_REFERENCE, HV_REFERENCE);

        double finalHV;
        double finalHVRatio;
        try {
            finalHV = hvIndicator.compute(finalArchive);
            finalHVRatio = hvIndicator.computeRatio(finalArchive);
        } catch (Exception e) {
            // If HV computation fails (e.g. all points identical), record NaN
            finalHV = Double.NaN;
            finalHVRatio = Double.NaN;
        }

        int finalNDCount = pareto.getNonDominated(finalArchive).size();

        double bestF1 = archive.stream()
                .mapToDouble(Individual::getObjective1)
                .min().orElse(Double.NaN);

        double bestF2 = archive.stream()
                .mapToDouble(Individual::getObjective2)
                .min().orElse(Double.NaN);

        int actualEvals = computeActualEvaluations(populationSize, archiveSize, maxGenerations);

        System.out.printf(
                "         -> HV=%.6f  ND=%d  BestF1=%.6f  BestF2=%.6f  %dms%n",
                finalHV, finalNDCount, bestF1, bestF2, runtimeMs
        );

        return formatCsvRow(
                runId, seed, k, populationSize, archiveSize, maxGenerations,
                crossoverRate, mutationRate, actualEvals,
                finalHV, finalHVRatio, finalNDCount, bestF1, bestF2, runtimeMs
        );
    }

    // ---------------------------------------------------------------
    //  Helper methods
    // ---------------------------------------------------------------

    /**
     * Computes the maximum number of generations for a given population
     * and archive size so that total evaluations equal the fixed budget.
     *
     * <p>Formula:
     * {@code totalEvals = popSize + maxGen × (popSize + archiveSize)}
     * → {@code maxGen = (budget - popSize) / (popSize + archiveSize)}
     * </p>
     */
    private static int computeMaxGenerations(int populationSize, int archiveSize) {
        return (TOTAL_EVALUATION_BUDGET - populationSize) / (populationSize + archiveSize);
    }

    /**
     * Computes the actual number of function evaluations for verification.
     */
    private static int computeActualEvaluations(int populationSize, int archiveSize, int maxGenerations) {
        return populationSize + maxGenerations * (populationSize + archiveSize);
    }

    /**
     * Updates running objective bounds from a set of evaluated individuals.
     *
     * @return array [minF1, maxF1, minF2, maxF2]
     */
    private static double[] updateBounds(
            List<Individual> individuals,
            double currentMinF1, double currentMaxF1,
            double currentMinF2, double currentMaxF2) {

        for (Individual ind : individuals) {
            double f1 = ind.getObjective1();
            double f2 = ind.getObjective2();

            if (f1 < currentMinF1) currentMinF1 = f1;
            if (f1 > currentMaxF1) currentMaxF1 = f1;
            if (f2 < currentMinF2) currentMinF2 = f2;
            if (f2 > currentMaxF2) currentMaxF2 = f2;
        }

        return new double[]{currentMinF1, currentMaxF1, currentMinF2, currentMaxF2};
    }

    /**
     * Deep-copies a list of individuals so that normalization does not
     * overwrite archive values.
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
     * Validates that the distance matrix dimensions match the repository.
     */
    private static void validateMatrix(double[][] distanceMatrix, CandidateRepository repository) {
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
    }

    // ---------------------------------------------------------------
    //  CSV output
    // ---------------------------------------------------------------

    /**
     * Writes the CSV file with header and all result rows.
     */
    private static void writeCsv(List<String> rows) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(RESULTS_CSV)) {
            writer.write(CSV_HEADER);
            writer.newLine();

            for (String row : rows) {
                writer.write(row);
                writer.newLine();
            }
        }
    }

    /**
     * Formats a single CSV row.
     */
    private static String formatCsvRow(
            int runId, long seed, int k, int populationSize, int archiveSize,
            int maxGenerations, double crossoverRate, double mutationRate,
            int totalEvaluations, double finalHV, double finalHVRatio,
            int finalNDCount, double bestF1, double bestF2, long runtimeMs) {

        return String.format(Locale.US,
                "%d,%d,%d,%d,%d,%d,%.2f,%.2f,%d,%.6f,%.6f,%d,%.6f,%.6f,%d",
                runId, seed, k, populationSize, archiveSize, maxGenerations,
                crossoverRate, mutationRate, totalEvaluations,
                finalHV, finalHVRatio, finalNDCount, bestF1, bestF2, runtimeMs
        );
    }

    // ---------------------------------------------------------------
    //  Formatting helpers
    // ---------------------------------------------------------------

    private static String formatArray(int[] arr) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < arr.length; i++) {
            if (i > 0) sb.append(", ");
            sb.append(arr[i]);
        }
        return sb.append("]").toString();
    }

    private static String formatArray(double[] arr) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < arr.length; i++) {
            if (i > 0) sb.append(", ");
            sb.append(String.format(Locale.US, "%.2f", arr[i]));
        }
        return sb.append("]").toString();
    }
}

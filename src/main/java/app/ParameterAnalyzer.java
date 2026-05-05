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
 * Performs an academically rigorous full-factorial parameter grid search for the
 * SPEA2 parcel locker optimization pipeline (V2).
 *
 * <h3>Key design principles:</h3>
 * <ol>
 *   <li><b>Fair FE Budgeting:</b> Each configuration receives the same number of
 *       function evaluations (FE), computed as {@code popSize × (maxGen + 1)}.
 *       The FE budget scales with K to ensure adequate convergence for harder
 *       problem instances.</li>
 *   <li><b>Lambda Grid:</b> The demand weighting parameter λ is included in the
 *       grid search and computed dynamically via the
 *       {@link FitnessCalculator#FitnessCalculator(double[][], CandidateRepository, double, double)}
 *       constructor.</li>
 *   <li><b>Calibration-Phase Fixed HV Bounds:</b> Before the grid search for
 *       each (K, λ) pair, a calibration phase runs multiple SPEA2 instances with
 *       standard parameters, unions all final archives, and locks the global
 *       objective bounds for HV normalization.</li>
 *   <li><b>Rich Output:</b> CSV output includes all parameter columns and
 *       comprehensive quality metrics.</li>
 * </ol>
 *
 * <h3>Run with:</h3>
 * <pre>
 *   mvn compile exec:java -Panalyze
 * </pre>
 */
public class ParameterAnalyzer {

    // ---------------------------------------------------------------
    //  Grid definitions
    // ---------------------------------------------------------------

    /** Number of locker locations per chromosome. */
    private static final int[] K_VALUES = {3, 6, 10};

    /** Lambda (POI influence weight) grid. */
    private static final double[] LAMBDA_VALUES = {0.4, 0.5, 0.6};

    /** Mutation rate grid. */
    private static final double[] MUTATION_RATES = {0.05, 0.10, 0.20, 0.30, 0.40};

    /** Crossover rate grid. */
    private static final double[] CROSSOVER_RATES = {0.7, 0.9};

    /** Population size grid (archive size = popSize / 2, matching GAParameters). */
    private static final int[] POPULATION_SIZES = {50, 100, 200};

    /** Random seeds for repeated runs. */
    private static final long[] SEEDS = {42L, 123L, 7L};

    // ---------------------------------------------------------------
    //  K-dependent Function Evaluation Budgets
    // ---------------------------------------------------------------

    /**
     * K-dependent FE budgets designed to guarantee adequate convergence.
     *
     * <p>Rationale (based on empirical convergence observations):</p>
     * <ul>
     *   <li><b>K=3:</b>  Small search space. Pop=100 needs ~300 gens → FE = 100×301 ≈ 30,000.
     *       Budget = 30,000 ensures pop=50 gets ~600 gens, pop=200 gets ~150 gens.</li>
     *   <li><b>K=6:</b>  Medium search space. Pop=100 needs ~500 gens → FE = 100×501 ≈ 50,000.
     *       Budget = 50,000 ensures pop=50 gets ~1000 gens, pop=200 gets ~250 gens.</li>
     *   <li><b>K=10:</b> Large search space. Pop=100 needs ~800+ gens → FE = 100×801 ≈ 80,000.
     *       Budget = 80,000 ensures pop=50 gets ~1600 gens, pop=200 gets ~400 gens.</li>
     * </ul>
     *
     * <p>Formula: {@code maxGenerations = (TARGET_FE / populationSize) - 1}.</p>
     */
    private static int getTargetFE(int k) {
        if (k <= 3) return 30_000;
        if (k <= 6) return 50_000;
        return 80_000;  // K >= 7
    }

    // ---------------------------------------------------------------
    //  Calibration Phase Parameters
    // ---------------------------------------------------------------

    /** Number of calibration runs per (K, Lambda) pair. */
    private static final int CALIBRATION_RUNS = 5;

    /** Population size for calibration runs. */
    private static final int CALIBRATION_POP_SIZE = 100;

    /** Archive size for calibration runs (popSize / 2, matching standard ratio). */
    private static final int CALIBRATION_ARCHIVE_SIZE = CALIBRATION_POP_SIZE / 2;

    /** Seeds for calibration runs (deterministic, diverse). */
    private static final long[] CALIBRATION_SEEDS = {1L, 2L, 3L, 4L, 5L};

    /** Margin added to calibration bounds (2% of range). */
    private static final double CALIBRATION_MARGIN = 0.02;

    // ---------------------------------------------------------------
    //  Problem Constants
    // ---------------------------------------------------------------

    /** Distance-decay exponent (problem constant, not tuned). */
    private static final double BETA = GAParameters.BETA;

    /** HV reference point in normalized space. */
    private static final double HV_REFERENCE = 1.1;

    // ---------------------------------------------------------------
    //  Output
    // ---------------------------------------------------------------

    private static final Path OUTPUT_DIRECTORY = Paths.get("output");
    private static final Path RESULTS_CSV = OUTPUT_DIRECTORY.resolve("parameter_analysis_results.csv");

    private static final String CSV_HEADER = String.join(",",
            "K",
            "Lambda",
            "PopSize",
            "ArchiveSize",
            "MaxGen",
            "MutRate",
            "CrossRate",
            "FunctionEvals",
            "Runtime_ms",
            "ND_Count",
            "Best_f1",
            "Best_f2",
            "Mean_f1",
            "Mean_f2",
            "Final_HV"
    );

    // ---------------------------------------------------------------
    //  Calibration Bounds Container
    // ---------------------------------------------------------------

    /**
     * Holds the locked normalization bounds for a specific (K, Lambda) pair.
     */
    private static class CalibrationBounds {
        final double minF1, maxF1, minF2, maxF2;

        CalibrationBounds(double minF1, double maxF1, double minF2, double maxF2) {
            this.minF1 = minF1;
            this.maxF1 = maxF1;
            this.minF2 = minF2;
            this.maxF2 = maxF2;
        }

        @Override
        public String toString() {
            return String.format(Locale.US,
                    "f1=[%.6f, %.6f]  f2=[%.6f, %.6f]",
                    minF1, maxF1, minF2, maxF2);
        }
    }

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

            List<Integer> candidateIds = repository.getSelectableCandidateIds();
            if (candidateIds.isEmpty()) {
                throw new IllegalStateException("No selectable candidates found. All candidates may be forbidden.");
            }

            // 2. Print experiment header
            System.out.println("╔══════════════════════════════════════════════════════════════╗");
            System.out.println("║           SPEA2 Parameter Analysis V2 — Grid Search         ║");
            System.out.println("╚══════════════════════════════════════════════════════════════╝");
            System.out.println();
            System.out.println("Candidates loaded     : " + repository.size());
            System.out.println("Selectable candidates : " + candidateIds.size());
            System.out.println("K values              : " + formatArray(K_VALUES));
            System.out.println("Lambda values         : " + formatArray(LAMBDA_VALUES));
            System.out.println("Mutation rates        : " + formatArray(MUTATION_RATES));
            System.out.println("Crossover rates       : " + formatArray(CROSSOVER_RATES));
            System.out.println("Population sizes      : " + formatArray(POPULATION_SIZES));
            System.out.println("Seeds per config      : " + SEEDS.length);
            System.out.println("Calibration runs/pair : " + CALIBRATION_RUNS);
            System.out.println();

            for (int k : K_VALUES) {
                System.out.printf("  FE budget for K=%-2d  : %,d%n", k, getTargetFE(k));
            }

            int totalConfigs = K_VALUES.length * LAMBDA_VALUES.length
                    * MUTATION_RATES.length * CROSSOVER_RATES.length * POPULATION_SIZES.length;
            int totalRuns = totalConfigs * SEEDS.length;
            int totalCalibrations = K_VALUES.length * LAMBDA_VALUES.length * CALIBRATION_RUNS;
            System.out.println();
            System.out.println("Total grid configs    : " + totalConfigs);
            System.out.println("Total grid runs       : " + totalRuns);
            System.out.println("Total calibration runs: " + totalCalibrations);
            System.out.println("Grand total SPEA2 runs: " + (totalRuns + totalCalibrations));
            System.out.println();

            // 3. Run the grid search with calibration
            List<String> resultRows = new ArrayList<>();
            int runId = 0;

            for (int k : K_VALUES) {
                int targetFE = getTargetFE(k);

                for (double lambda : LAMBDA_VALUES) {

                    // ===== CALIBRATION PHASE =====
                    System.out.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                    System.out.printf("  CALIBRATION PHASE — K=%d, Lambda=%.2f%n", k, lambda);
                    System.out.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

                    CalibrationBounds bounds = runCalibrationPhase(
                            k, lambda, distanceMatrix, repository, candidateIds
                    );

                    System.out.println("  LOCKED BOUNDS: " + bounds);
                    System.out.println();

                    // ===== GRID SEARCH =====
                    for (int popSize : POPULATION_SIZES) {
                        int archiveSize = popSize / 2;  // 1:2 ratio, matching GAParameters
                        int maxGenerations = (targetFE / popSize) - 1;

                        for (double crossoverRate : CROSSOVER_RATES) {
                            for (double mutationRate : MUTATION_RATES) {
                                for (long seed : SEEDS) {
                                    runId++;

                                    int functionEvals = popSize * (maxGenerations + 1);

                                    System.out.printf(
                                            "[Run %3d/%d] K=%d λ=%.1f Pop=%3d Arc=%3d Gen=%4d Cx=%.2f Mut=%.2f Seed=%d FE=%d%n",
                                            runId, totalRuns, k, lambda, popSize, archiveSize,
                                            maxGenerations, crossoverRate, mutationRate, seed,
                                            functionEvals
                                    );

                                    String row = executeSingleRun(
                                            k, lambda, popSize, archiveSize,
                                            maxGenerations, crossoverRate, mutationRate,
                                            seed, functionEvals, bounds,
                                            distanceMatrix, repository, candidateIds
                                    );
                                    resultRows.add(row);
                                }
                            }
                        }
                    }
                }
            }

            // 4. Write CSV
            writeCsv(resultRows);
            System.out.println();
            System.out.println("╔══════════════════════════════════════════════════════════════╗");
            System.out.println("║                     Analysis Complete                       ║");
            System.out.println("╚══════════════════════════════════════════════════════════════╝");
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
    //  Calibration Phase
    // ---------------------------------------------------------------

    /**
     * Runs the calibration phase for a specific (K, Lambda) pair.
     *
     * <p>This method executes {@value #CALIBRATION_RUNS} SPEA2 runs with standard
     * parameters, collects all final archive individuals, extracts the global
     * min/max for both objectives, and returns padded bounds that will be locked
     * for all subsequent grid search runs with this (K, Lambda).</p>
     *
     * @param k locker count
     * @param lambda POI influence weight
     * @param distanceMatrix distance matrix
     * @param repository candidate repository
     * @param candidateIds candidate IDs
     * @return locked calibration bounds
     */
    private static CalibrationBounds runCalibrationPhase(
            int k, double lambda,
            double[][] distanceMatrix, CandidateRepository repository,
            List<Integer> candidateIds) {

        // Use the K-specific FE budget for calibration runs too
        int calibTargetFE = getTargetFE(k);
        int calibMaxGen = (calibTargetFE / CALIBRATION_POP_SIZE) - 1;


        // Collect all individuals from all calibration runs
        List<Individual> allCalibrationIndividuals = new ArrayList<>();

        FitnessCalculator fitnessCalculator =
                new FitnessCalculator(distanceMatrix, repository, BETA, lambda);

        for (int i = 0; i < CALIBRATION_RUNS; i++) {
            long seed = CALIBRATION_SEEDS[i];

            System.out.printf("  Calibration run %d/%d (seed=%d, gen=%d)...%n",
                    i + 1, CALIBRATION_RUNS, seed, calibMaxGen);

            List<Individual> finalArchive = runSPEA2(
                    k, fitnessCalculator, candidateIds,
                    CALIBRATION_POP_SIZE, CALIBRATION_ARCHIVE_SIZE, calibMaxGen,
                    GAParameters.CROSSOVER_RATE, GAParameters.MUTATION_RATE, seed
            );

            allCalibrationIndividuals.addAll(finalArchive);
        }

        // Extract the non-dominated set from the union of all calibration archives.
        // CRITICAL: Bounds MUST be derived from the ND set only (ideal/nadir),
        // exactly as Main.java does (lines 210-216). Using ALL individuals
        // would include dominated garbage with extreme objective values,
        // making the bounds too wide and inflating HV values to near 1.0.
        Dominance dominance = new Dominance();
        Pareto pareto = new Pareto(dominance);
        List<Individual> ndUnion = pareto.getNonDominated(allCalibrationIndividuals);

        System.out.printf("  Calibration union: %d individuals → %d non-dominated%n",
                allCalibrationIndividuals.size(), ndUnion.size());

        // Compute ideal (min) and nadir (max) from the ND set only
        double idealF1 = Double.POSITIVE_INFINITY;
        double nadirF1 = Double.NEGATIVE_INFINITY;
        double idealF2 = Double.POSITIVE_INFINITY;
        double nadirF2 = Double.NEGATIVE_INFINITY;

        for (Individual ind : ndUnion) {
            double f1 = ind.getObjective1();
            double f2 = ind.getObjective2();

            if (f1 < idealF1) idealF1 = f1;
            if (f1 > nadirF1) nadirF1 = f1;
            if (f2 < idealF2) idealF2 = f2;
            if (f2 > nadirF2) nadirF2 = f2;
        }

        System.out.printf("  ND ideal: f1=%.6f  f2=%.6f%n", idealF1, idealF2);
        System.out.printf("  ND nadir: f1=%.6f  f2=%.6f%n", nadirF1, nadirF2);

        // Apply margin to the ND-based bounds
        double rangeF1 = nadirF1 - idealF1;
        double rangeF2 = nadirF2 - idealF2;

        // Handle degenerate case
        if (rangeF1 == 0) rangeF1 = 1.0;
        if (rangeF2 == 0) rangeF2 = 1.0;

        double paddedMinF1 = idealF1 - CALIBRATION_MARGIN * rangeF1;
        double paddedMaxF1 = nadirF1 + CALIBRATION_MARGIN * rangeF1;
        double paddedMinF2 = idealF2 - CALIBRATION_MARGIN * rangeF2;
        double paddedMaxF2 = nadirF2 + CALIBRATION_MARGIN * rangeF2;

        return new CalibrationBounds(paddedMinF1, paddedMaxF1, paddedMinF2, paddedMaxF2);
    }

    // ---------------------------------------------------------------
    //  Core SPEA2 Execution
    // ---------------------------------------------------------------

    /**
     * Runs a single SPEA2 execution and returns the final archive.
     *
     * <p>This method is used by both the calibration phase and the grid search.
     * It does NOT compute any assessment metrics — it only returns the raw
     * final archive.</p>
     */
    private static List<Individual> runSPEA2(
            int k, FitnessCalculator fitnessCalculator, List<Integer> candidateIds,
            int populationSize, int archiveSize, int maxGenerations,
            double crossoverRate, double mutationRate, long seed) {

        PopulationInitializer populationInitializer = new PopulationInitializer(seed);

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

        // Generation 0
        List<Individual> evaluated = evaluate.run(population, archive);
        archive = survivor.run(evaluated, archiveSize);

        // Main evolutionary loop
        for (int gen = 1; gen <= maxGenerations; gen++) {
            List<Individual> matingPool = selection.run(archive, populationSize);

            population = variation.run(
                    matingPool, candidateIds, populationSize, k,
                    crossoverRate, mutationRate
            );

            evaluated = evaluate.run(population, archive);
            archive = survivor.run(evaluated, archiveSize);
        }

        return archive;
    }

    // ---------------------------------------------------------------
    //  Single Grid Search Run
    // ---------------------------------------------------------------

    /**
     * Executes a single SPEA2 run with the given parameters, computes all
     * assessment metrics using the locked calibration bounds, and returns
     * a CSV-formatted result row.
     */
    private static String executeSingleRun(
            int k, double lambda, int populationSize, int archiveSize,
            int maxGenerations, double crossoverRate, double mutationRate,
            long seed, int functionEvals, CalibrationBounds bounds,
            double[][] distanceMatrix, CandidateRepository repository,
            List<Integer> candidateIds) {

        long startNs = System.nanoTime();

        FitnessCalculator fitnessCalculator =
                new FitnessCalculator(distanceMatrix, repository, BETA, lambda);

        List<Individual> archive = runSPEA2(
                k, fitnessCalculator, candidateIds,
                populationSize, archiveSize, maxGenerations,
                crossoverRate, mutationRate, seed
        );

        long runtimeMs = (System.nanoTime() - startNs) / 1_000_000;

        // Normalize final archive for HV computation using LOCKED bounds
        ObjectiveNormalizer objectiveNormalizer = new ObjectiveNormalizer();
        List<Individual> finalArchive = deepCopyIndividuals(archive);
        objectiveNormalizer.normalizePopulationObjectives(
                finalArchive,
                bounds.minF1, bounds.maxF1,
                bounds.minF2, bounds.maxF2
        );

        // Compute HV
        Dominance dominance = new Dominance();
        Pareto pareto = new Pareto(dominance);
        HypervolumeIndicator hvIndicator = new HypervolumeIndicator(pareto, HV_REFERENCE, HV_REFERENCE);

        double finalHV;
        try {
            finalHV = hvIndicator.compute(finalArchive);
        } catch (Exception e) {
            finalHV = Double.NaN;
        }

        // Compute ND metrics on raw (un-normalized) archive
        List<Individual> ndSet = pareto.getNonDominated(archive);
        int ndCount = ndSet.size();

        double bestF1 = ndSet.stream()
                .mapToDouble(Individual::getObjective1)
                .min().orElse(Double.NaN);

        double bestF2 = ndSet.stream()
                .mapToDouble(Individual::getObjective2)
                .min().orElse(Double.NaN);

        double meanF1 = ndSet.stream()
                .mapToDouble(Individual::getObjective1)
                .average().orElse(Double.NaN);

        double meanF2 = ndSet.stream()
                .mapToDouble(Individual::getObjective2)
                .average().orElse(Double.NaN);

        System.out.printf(
                "         -> HV=%.6f  ND=%d  BestF1=%.6f  BestF2=%.6f  %dms%n",
                finalHV, ndCount, bestF1, bestF2, runtimeMs
        );

        return formatCsvRow(
                k, lambda, populationSize, archiveSize, maxGenerations,
                mutationRate, crossoverRate, functionEvals,
                runtimeMs, ndCount, bestF1, bestF2, meanF1, meanF2, finalHV
        );
    }

    // ---------------------------------------------------------------
    //  Helper methods
    // ---------------------------------------------------------------

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
     * Formats a single CSV row with the RULE 4 columns.
     */
    private static String formatCsvRow(
            int k, double lambda, int populationSize, int archiveSize,
            int maxGenerations, double mutationRate, double crossoverRate,
            int functionEvals, long runtimeMs, int ndCount,
            double bestF1, double bestF2, double meanF1, double meanF2,
            double finalHV) {

        return String.format(Locale.US,
                "%d,%.2f,%d,%d,%d,%.2f,%.2f,%d,%d,%d,%.6f,%.6f,%.6f,%.6f,%.6f",
                k, lambda, populationSize, archiveSize, maxGenerations,
                mutationRate, crossoverRate, functionEvals,
                runtimeMs, ndCount, bestF1, bestF2, meanF1, meanF2, finalHV
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

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
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * Runs the SPEA2 parameter/statistical analysis experiment.
 *
 * <p>The full experiment is 4 K values x 18 fixed GA configurations x 20
 * shared seeds. Lambda is intentionally not part of this grid; objective
 * evaluation uses the precomputed demand values loaded from candidate_points.csv.</p>
 */
public class ParameterAnalyzer {

    private static final int[] K_VALUES = {1, 5, 10, 15};
    private static final int[] POPULATION_SIZES = {50, 100, 200};
    private static final double[] MUTATION_RATES = {0.10, 0.25, 0.40};
    private static final double[] CROSSOVER_RATES = {0.70, 0.90};
    private static final long[] SEEDS = {
            1L, 2L, 3L, 4L, 5L,
            6L, 7L, 8L, 9L, 10L,
            11L, 12L, 13L, 14L, 15L,
            16L, 17L, 18L, 19L, 20L
    };

    private static final int CALIBRATION_RUNS = 5;
    private static final int CALIBRATION_POPULATION_SIZE = 100;
    private static final int CALIBRATION_ARCHIVE_SIZE = CALIBRATION_POPULATION_SIZE / 2;
    private static final long[] CALIBRATION_SEEDS = {101L, 102L, 103L, 104L, 105L};
    private static final long[] SMOKE_CALIBRATION_SEEDS = {101L};
    private static final double CALIBRATION_MARGIN = 0.02;

    private static final int SMOKE_TARGET_FE = 200;
    private static final int SMOKE_K_LIMIT = 1;
    private static final int SMOKE_CONFIG_LIMIT = 2;
    private static final int SMOKE_SEED_LIMIT = 2;

    private static final double BETA = GAParameters.BETA;
    private static final double HV_REFERENCE = 1.1;
    private static final double HV_REFERENCE_AREA = HV_REFERENCE * HV_REFERENCE;

    private static final String DEFAULT_CANDIDATE_CSV = "data/candidate_points.csv";
    private static final String DEFAULT_DISTANCE_MATRIX = "data/kadikoy_distance_meters_nxn.npy";
    private static final String DEFAULT_OUTPUT_DIRECTORY = "output";

    private static final Path OUTPUT_DIRECTORY = resolveConfiguredPath("GA_OUTPUT_DIR", DEFAULT_OUTPUT_DIRECTORY);
    private static final Path RESULTS_CSV = OUTPUT_DIRECTORY.resolve("parameter_analysis_results.csv");
    private static final Path SMOKE_RESULTS_CSV = OUTPUT_DIRECTORY.resolve("parameter_analysis_results_smoke.csv");
    private static final Path CONFIGURATION_TABLE_CSV = OUTPUT_DIRECTORY.resolve("ga_configuration_table.csv");

    private static final String RESULTS_HEADER = String.join(",",
            "Run_ID",
            "K",
            "Task",
            "GA_ID",
            "PopulationSize",
            "ArchiveSize",
            "MaxGenerations",
            "TargetFE",
            "FunctionEvals",
            "MutationRate",
            "CrossoverRate",
            "Seed",
            "Runtime_ms",
            "Final_HV",
            "Final_HV_Ratio",
            "ND_Count",
            "Final_ND_Archive_Ratio",
            "Spacing_CV",
            "Best_f1",
            "Best_f2",
            "Mean_f1",
            "Mean_f2"
    );

    private static final String CONFIGURATION_TABLE_HEADER = String.join(",",
            "GA_ID",
            "PopulationSize",
            "ArchiveSize",
            "MutationRate",
            "CrossoverRate"
    );

    private record GAConfiguration(
            String gaId,
            int populationSize,
            int archiveSize,
            double mutationRate,
            double crossoverRate
    ) {
    }

    private record CalibrationBounds(
            double minF1,
            double maxF1,
            double minF2,
            double maxF2
    ) {
        @Override
        public String toString() {
            return String.format(Locale.US,
                    "f1=[%.6f, %.6f], f2=[%.6f, %.6f]",
                    minF1, maxF1, minF2, maxF2);
        }
    }

    public static void main(String[] args) {
        boolean smokeMode = hasArg(args, "--smoke");

        try {
            Files.createDirectories(OUTPUT_DIRECTORY);

            CandidateRepository repository = new CandidateRepository();
            CsvLoader csvLoader = new CsvLoader();
            csvLoader.loadCandidates(
                    resolveConfiguredPath("GA_CANDIDATE_CSV", DEFAULT_CANDIDATE_CSV).toString(),
                    repository
            );
            repository.finalizeRepository();

            double[][] distanceMatrix =
                    new DistanceMatrixLoader().loadDistanceMatrix(
                            resolveConfiguredPath("GA_DISTANCE_MATRIX", DEFAULT_DISTANCE_MATRIX).toString()
                    );

            validateMatrix(distanceMatrix, repository);

            List<Integer> candidateIds = repository.getSelectableCandidateIds();
            if (candidateIds.isEmpty()) {
                throw new IllegalStateException("No selectable candidates found. All candidates may be forbidden.");
            }

            List<GAConfiguration> allConfigurations = buildGAConfigurations();
            writeConfigurationTable(allConfigurations);

            int[] activeKValues = firstN(K_VALUES, smokeMode ? SMOKE_K_LIMIT : K_VALUES.length);
            List<GAConfiguration> activeConfigurations = firstN(
                    allConfigurations,
                    smokeMode ? SMOKE_CONFIG_LIMIT : allConfigurations.size()
            );
            long[] activeSeeds = firstN(SEEDS, smokeMode ? SMOKE_SEED_LIMIT : SEEDS.length);
            long[] activeCalibrationSeeds = smokeMode ? SMOKE_CALIBRATION_SEEDS : CALIBRATION_SEEDS;
            Path resultPath = smokeMode ? SMOKE_RESULTS_CSV : RESULTS_CSV;

            printExperimentHeader(
                    smokeMode,
                    repository,
                    candidateIds,
                    activeKValues,
                    activeConfigurations,
                    activeSeeds,
                    activeCalibrationSeeds
            );

            List<String> rows = new ArrayList<>();
            int runId = 0;
            int totalGridRuns = activeKValues.length * activeConfigurations.size() * activeSeeds.length;

            for (int k : activeKValues) {
                int targetFE = getTargetFE(k, smokeMode);
                CalibrationBounds bounds = runCalibrationPhase(
                        k,
                        targetFE,
                        activeCalibrationSeeds,
                        distanceMatrix,
                        repository,
                        candidateIds
                );

                System.out.println("Locked HV bounds for K=" + k + ": " + bounds);
                System.out.println();

                for (GAConfiguration configuration : activeConfigurations) {
                    int maxGenerations = getMaxGenerations(targetFE, configuration.populationSize());
                    int functionEvals = configuration.populationSize() * (maxGenerations + 1);

                    for (long seed : activeSeeds) {
                        runId++;

                        System.out.printf(Locale.US,
                                "[Run %d/%d] K=%d %s Pop=%d Arc=%d Gen=%d Mut=%.2f Cx=%.2f Seed=%d FE=%d%n",
                                runId,
                                totalGridRuns,
                                k,
                                configuration.gaId(),
                                configuration.populationSize(),
                                configuration.archiveSize(),
                                maxGenerations,
                                configuration.mutationRate(),
                                configuration.crossoverRate(),
                                seed,
                                functionEvals
                        );

                        String row = executeSingleRun(
                                runId,
                                k,
                                configuration,
                                targetFE,
                                maxGenerations,
                                functionEvals,
                                seed,
                                bounds,
                                distanceMatrix,
                                repository,
                                candidateIds
                        );
                        rows.add(row);
                    }
                }
            }

            writeResultsCsv(resultPath, rows);
            System.out.println();
            System.out.println("Analysis complete.");
            System.out.println("Results written to: " + resultPath.toAbsolutePath());
            System.out.println("GA configuration table written to: " + CONFIGURATION_TABLE_CSV.toAbsolutePath());

        } catch (IOException e) {
            System.err.println("I/O error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        } catch (Exception e) {
            System.err.println("Unexpected error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    private static List<GAConfiguration> buildGAConfigurations() {
        List<GAConfiguration> configurations = new ArrayList<>();
        int id = 1;

        for (int populationSize : POPULATION_SIZES) {
            int archiveSize = populationSize / 2;

            for (double mutationRate : MUTATION_RATES) {
                for (double crossoverRate : CROSSOVER_RATES) {
                    configurations.add(new GAConfiguration(
                            "GA" + id,
                            populationSize,
                            archiveSize,
                            mutationRate,
                            crossoverRate
                    ));
                    id++;
                }
            }
        }

        return configurations;
    }

    private static int getTargetFE(int k, boolean smokeMode) {
        if (smokeMode) {
            return SMOKE_TARGET_FE;
        }

        return switch (k) {
            case 1 -> 30_000;
            case 5 -> 50_000;
            case 10 -> 80_000;
            case 15 -> 100_000;
            default -> throw new IllegalArgumentException("Unsupported K value: " + k);
        };
    }

    private static int getMaxGenerations(int targetFE, int populationSize) {
        int maxGenerations = (targetFE / populationSize) - 1;
        if (maxGenerations < 0) {
            throw new IllegalArgumentException(
                    "TargetFE must be at least the population size. TargetFE=" +
                            targetFE + ", populationSize=" + populationSize
            );
        }
        return maxGenerations;
    }

    private static CalibrationBounds runCalibrationPhase(
            int k,
            int targetFE,
            long[] calibrationSeeds,
            double[][] distanceMatrix,
            CandidateRepository repository,
            List<Integer> candidateIds) {

        int calibrationMaxGenerations = getMaxGenerations(targetFE, CALIBRATION_POPULATION_SIZE);
        FitnessCalculator fitnessCalculator = new FitnessCalculator(distanceMatrix, repository, BETA);
        List<Individual> calibrationArchiveUnion = new ArrayList<>();

        System.out.printf(Locale.US,
                "Calibration phase for K=%d (%d run%s, targetFE=%d, pop=%d, gen=%d)%n",
                k,
                calibrationSeeds.length,
                calibrationSeeds.length == 1 ? "" : "s",
                targetFE,
                CALIBRATION_POPULATION_SIZE,
                calibrationMaxGenerations
        );

        for (int i = 0; i < calibrationSeeds.length; i++) {
            long seed = calibrationSeeds[i];
            System.out.printf(Locale.US,
                    "  Calibration %d/%d seed=%d%n",
                    i + 1,
                    calibrationSeeds.length,
                    seed
            );

            List<Individual> finalArchive = runSPEA2(
                    k,
                    fitnessCalculator,
                    candidateIds,
                    CALIBRATION_POPULATION_SIZE,
                    CALIBRATION_ARCHIVE_SIZE,
                    calibrationMaxGenerations,
                    GAParameters.CROSSOVER_RATE,
                    GAParameters.MUTATION_RATE,
                    seed
            );
            calibrationArchiveUnion.addAll(finalArchive);
        }

        Dominance dominance = new Dominance();
        Pareto pareto = new Pareto(dominance);
        List<Individual> ndUnion = pareto.getNonDominated(calibrationArchiveUnion);

        if (ndUnion.isEmpty()) {
            throw new IllegalStateException("Calibration produced no non-dominated solutions for K=" + k);
        }

        return computeBounds(ndUnion);
    }

    private static CalibrationBounds computeBounds(List<Individual> individuals) {
        double minF1 = Double.POSITIVE_INFINITY;
        double maxF1 = Double.NEGATIVE_INFINITY;
        double minF2 = Double.POSITIVE_INFINITY;
        double maxF2 = Double.NEGATIVE_INFINITY;

        for (Individual individual : individuals) {
            double f1 = individual.getObjective1();
            double f2 = individual.getObjective2();

            minF1 = Math.min(minF1, f1);
            maxF1 = Math.max(maxF1, f1);
            minF2 = Math.min(minF2, f2);
            maxF2 = Math.max(maxF2, f2);
        }

        double rangeF1 = maxF1 - minF1;
        double rangeF2 = maxF2 - minF2;

        if (Double.compare(rangeF1, 0.0) == 0) {
            rangeF1 = Math.max(Math.abs(minF1), 1.0);
        }
        if (Double.compare(rangeF2, 0.0) == 0) {
            rangeF2 = Math.max(Math.abs(minF2), 1.0);
        }

        return new CalibrationBounds(
                minF1 - CALIBRATION_MARGIN * rangeF1,
                maxF1 + CALIBRATION_MARGIN * rangeF1,
                minF2 - CALIBRATION_MARGIN * rangeF2,
                maxF2 + CALIBRATION_MARGIN * rangeF2
        );
    }

    private static List<Individual> runSPEA2(
            int k,
            FitnessCalculator fitnessCalculator,
            List<Integer> candidateIds,
            int populationSize,
            int archiveSize,
            int maxGenerations,
            double crossoverRate,
            double mutationRate,
            long seed) {

        PopulationInitializer populationInitializer = new PopulationInitializer(seed);
        ObjectiveNormalizer objectiveNormalizer = new ObjectiveNormalizer();
        Dominance dominance = new Dominance();
        Pareto pareto = new Pareto(dominance);
        Truncation truncation = new Truncation();

        Evaluate evaluate = new Evaluate(fitnessCalculator, objectiveNormalizer, dominance);
        Survivor survivor = new Survivor(pareto, truncation);
        Selection selection = new Selection(seed);
        Variation variation = new Variation(seed);

        List<Individual> population =
                populationInitializer.initializePopulation(candidateIds, k, populationSize);
        List<Individual> archive = new ArrayList<>();

        List<Individual> evaluated = evaluate.run(population, archive);
        archive = survivor.run(evaluated, archiveSize);

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
            archive = survivor.run(evaluated, archiveSize);
        }

        return archive;
    }

    private static String executeSingleRun(
            int runId,
            int k,
            GAConfiguration configuration,
            int targetFE,
            int maxGenerations,
            int functionEvals,
            long seed,
            CalibrationBounds bounds,
            double[][] distanceMatrix,
            CandidateRepository repository,
            List<Integer> candidateIds) {

        long startNs = System.nanoTime();

        FitnessCalculator fitnessCalculator = new FitnessCalculator(distanceMatrix, repository, BETA);
        List<Individual> archive = runSPEA2(
                k,
                fitnessCalculator,
                candidateIds,
                configuration.populationSize(),
                configuration.archiveSize(),
                maxGenerations,
                configuration.crossoverRate(),
                configuration.mutationRate(),
                seed
        );

        long runtimeMs = (System.nanoTime() - startNs) / 1_000_000L;

        Dominance dominance = new Dominance();
        Pareto pareto = new Pareto(dominance);
        List<Individual> ndSet = pareto.getNonDominated(archive);

        int ndCount = ndSet.size();
        double ndArchiveRatio = (double) ndCount / configuration.archiveSize();
        double finalHV = computeHypervolume(ndSet, bounds, pareto);
        double finalHVRatio = finalHV / HV_REFERENCE_AREA;
        double spacingCV = computeSpacingCV(ndSet, bounds);

        double bestF1 = ndSet.stream()
                .mapToDouble(Individual::getObjective1)
                .min()
                .orElse(Double.NaN);
        double bestF2 = ndSet.stream()
                .mapToDouble(Individual::getObjective2)
                .min()
                .orElse(Double.NaN);
        double meanF1 = ndSet.stream()
                .mapToDouble(Individual::getObjective1)
                .average()
                .orElse(Double.NaN);
        double meanF2 = ndSet.stream()
                .mapToDouble(Individual::getObjective2)
                .average()
                .orElse(Double.NaN);

        System.out.printf(Locale.US,
                "         -> HV=%.6f HV_Ratio=%.6f ND=%d Spacing_CV=%s Runtime=%dms%n",
                finalHV,
                finalHVRatio,
                ndCount,
                formatDouble(spacingCV),
                runtimeMs
        );

        return formatCsvRow(
                runId,
                k,
                configuration,
                targetFE,
                maxGenerations,
                functionEvals,
                seed,
                runtimeMs,
                finalHV,
                finalHVRatio,
                ndCount,
                ndArchiveRatio,
                spacingCV,
                bestF1,
                bestF2,
                meanF1,
                meanF2
        );
    }

    private static double computeHypervolume(
            List<Individual> ndSet,
            CalibrationBounds bounds,
            Pareto pareto) {

        if (ndSet.isEmpty()) {
            return Double.NaN;
        }

        List<Individual> normalized = deepCopyIndividuals(ndSet);
        ObjectiveNormalizer objectiveNormalizer = new ObjectiveNormalizer();
        objectiveNormalizer.normalizePopulationObjectives(
                normalized,
                bounds.minF1(),
                bounds.maxF1(),
                bounds.minF2(),
                bounds.maxF2()
        );

        HypervolumeIndicator hvIndicator = new HypervolumeIndicator(pareto, HV_REFERENCE, HV_REFERENCE);
        return hvIndicator.compute(normalized);
    }

    private static double computeSpacingCV(List<Individual> ndSet, CalibrationBounds bounds) {
        if (ndSet.size() < 2) {
            return Double.NaN;
        }

        List<Individual> normalized = deepCopyIndividuals(ndSet);
        ObjectiveNormalizer objectiveNormalizer = new ObjectiveNormalizer();
        objectiveNormalizer.normalizePopulationObjectives(
                normalized,
                bounds.minF1(),
                bounds.maxF1(),
                bounds.minF2(),
                bounds.maxF2()
        );

        normalized.sort(Comparator.comparingDouble(Individual::getNormalizedObjective1));

        List<Double> distances = new ArrayList<>();
        for (int i = 1; i < normalized.size(); i++) {
            Individual previous = normalized.get(i - 1);
            Individual current = normalized.get(i);
            double dx = current.getNormalizedObjective1() - previous.getNormalizedObjective1();
            double dy = current.getNormalizedObjective2() - previous.getNormalizedObjective2();
            distances.add(Math.sqrt(dx * dx + dy * dy));
        }

        double mean = distances.stream()
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(Double.NaN);

        if (Double.isNaN(mean) || Double.compare(mean, 0.0) == 0) {
            return Double.NaN;
        }

        double variance = distances.stream()
                .mapToDouble(distance -> {
                    double difference = distance - mean;
                    return difference * difference;
                })
                .average()
                .orElse(Double.NaN);

        return Math.sqrt(variance) / mean;
    }

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

    private static void writeResultsCsv(Path path, List<String> rows) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(path)) {
            writer.write(RESULTS_HEADER);
            writer.newLine();

            for (String row : rows) {
                writer.write(row);
                writer.newLine();
            }
        }
    }

    private static void writeConfigurationTable(List<GAConfiguration> configurations) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(CONFIGURATION_TABLE_CSV)) {
            writer.write(CONFIGURATION_TABLE_HEADER);
            writer.newLine();

            for (GAConfiguration configuration : configurations) {
                writer.write(String.format(Locale.US,
                        "%s,%d,%d,%.2f,%.2f",
                        configuration.gaId(),
                        configuration.populationSize(),
                        configuration.archiveSize(),
                        configuration.mutationRate(),
                        configuration.crossoverRate()
                ));
                writer.newLine();
            }
        }
    }

    private static String formatCsvRow(
            int runId,
            int k,
            GAConfiguration configuration,
            int targetFE,
            int maxGenerations,
            int functionEvals,
            long seed,
            long runtimeMs,
            double finalHV,
            double finalHVRatio,
            int ndCount,
            double ndArchiveRatio,
            double spacingCV,
            double bestF1,
            double bestF2,
            double meanF1,
            double meanF2) {

        return String.join(",",
                Integer.toString(runId),
                Integer.toString(k),
                "K" + k,
                configuration.gaId(),
                Integer.toString(configuration.populationSize()),
                Integer.toString(configuration.archiveSize()),
                Integer.toString(maxGenerations),
                Integer.toString(targetFE),
                Integer.toString(functionEvals),
                formatDouble(configuration.mutationRate()),
                formatDouble(configuration.crossoverRate()),
                Long.toString(seed),
                Long.toString(runtimeMs),
                formatDouble(finalHV),
                formatDouble(finalHVRatio),
                Integer.toString(ndCount),
                formatDouble(ndArchiveRatio),
                formatDouble(spacingCV),
                formatDouble(bestF1),
                formatDouble(bestF2),
                formatDouble(meanF1),
                formatDouble(meanF2)
        );
    }

    private static boolean hasArg(String[] args, String expected) {
        if (args == null) {
            return false;
        }

        for (String arg : args) {
            if (expected.equalsIgnoreCase(arg)) {
                return true;
            }
        }

        return false;
    }

    private static int[] firstN(int[] values, int limit) {
        int size = Math.min(limit, values.length);
        int[] selected = new int[size];
        System.arraycopy(values, 0, selected, 0, size);
        return selected;
    }

    private static long[] firstN(long[] values, int limit) {
        int size = Math.min(limit, values.length);
        long[] selected = new long[size];
        System.arraycopy(values, 0, selected, 0, size);
        return selected;
    }

    private static <T> List<T> firstN(List<T> values, int limit) {
        int size = Math.min(limit, values.size());
        return new ArrayList<>(values.subList(0, size));
    }

    private static String formatDouble(double value) {
        if (Double.isNaN(value)) {
            return "NaN";
        }
        if (Double.isInfinite(value)) {
            return value > 0 ? "Infinity" : "-Infinity";
        }
        return String.format(Locale.US, "%.6f", value);
    }

    private static void printExperimentHeader(
            boolean smokeMode,
            CandidateRepository repository,
            List<Integer> candidateIds,
            int[] activeKValues,
            List<GAConfiguration> activeConfigurations,
            long[] activeSeeds,
            long[] activeCalibrationSeeds) {

        System.out.println("SPEA2 parameter/statistical analysis");
        if (smokeMode) {
            System.out.println("Mode: SMOKE (reduced run count and TargetFE; writes smoke results CSV)");
        } else {
            System.out.println("Mode: FULL");
        }

        System.out.println("Candidates loaded: " + repository.size());
        System.out.println("Selectable candidates: " + candidateIds.size());
        System.out.println("K values: " + formatArray(activeKValues));
        System.out.println("GA configurations: " + activeConfigurations.size());
        System.out.println("Seeds per configuration: " + activeSeeds.length);
        System.out.println("Calibration runs per K: " + activeCalibrationSeeds.length);
        System.out.println("Demand source: precomputed candidate_points.csv demandScore");

        for (int k : activeKValues) {
            System.out.printf(Locale.US,
                    "TargetFE for K=%d: %,d%n",
                    k,
                    getTargetFE(k, smokeMode)
            );
        }

        int totalGridRuns = activeKValues.length * activeConfigurations.size() * activeSeeds.length;
        int totalCalibrationRuns = activeKValues.length * activeCalibrationSeeds.length;

        System.out.println("Grid SPEA2 runs: " + totalGridRuns);
        System.out.println("Calibration SPEA2 runs: " + totalCalibrationRuns);
        System.out.println();
    }

    private static String formatArray(int[] values) {
        StringBuilder builder = new StringBuilder("[");
        for (int i = 0; i < values.length; i++) {
            if (i > 0) {
                builder.append(", ");
            }
            builder.append(values[i]);
        }
        builder.append("]");
        return builder.toString();
    }

    private static Path resolveConfiguredPath(String envName, String defaultPath) {
        String configured = System.getenv(envName);
        if (configured == null || configured.isBlank()) {
            configured = defaultPath;
        }

        Path path = Paths.get(configured);
        if (path.isAbsolute()) {
            return path.normalize();
        }

        String projectRoot = System.getenv("PROJECT_ROOT");
        if (projectRoot != null && !projectRoot.isBlank()) {
            return Paths.get(projectRoot).resolve(path).normalize();
        }

        return path.normalize();
    }
}

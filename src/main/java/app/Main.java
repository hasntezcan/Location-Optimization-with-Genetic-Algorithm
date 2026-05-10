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

/**
 * Main SPEA2 workflow.
 *
 * <p>Assessment methodology:</p>
 * <ul>
 *   <li>Initial-to-final improvement is evaluated via ND-only raw-objective
 *       improvement metrics and the dominance-based C-metric in
 *       {@code plot_archives.py}.</li>
 *   <li>Hypervolume is kept only as a final-archive/front quality indicator.</li>
 *   <li>HV-space normalization bounds are derived solely from the final
 *       archive's non-dominated set (ideal = min, nadir = max of final ND).</li>
 * </ul>
 */
public class Main {

    private static final String DEFAULT_CANDIDATE_CSV = "data/candidate_points.csv";
    private static final String DEFAULT_DISTANCE_MATRIX = "data/kadikoy_distance_meters_nxn.npy";
    private static final String DEFAULT_OUTPUT_DIRECTORY = "output";

    public static void main(String[] args) {
        long startTimeNs = System.nanoTime();

        CandidateRepository repository = new CandidateRepository();
        CsvLoader csvLoader = new CsvLoader();
        DistanceMatrixLoader distanceMatrixLoader = new DistanceMatrixLoader();

        try {
            Path candidateCsv = resolveConfiguredPath("GA_CANDIDATE_CSV", DEFAULT_CANDIDATE_CSV);
            Path distanceMatrixPath = resolveConfiguredPath("GA_DISTANCE_MATRIX", DEFAULT_DISTANCE_MATRIX);
            Path outputDirectory = resolveConfiguredPath("GA_OUTPUT_DIR", DEFAULT_OUTPUT_DIRECTORY);

            // 3. Parameters
            int k = GAParameters.K;
            int populationSize = GAParameters.POPULATION_SIZE;
            int archiveSize = GAParameters.ARCHIVE_SIZE;
            int maxGenerations = GAParameters.MAX_GENERATIONS;
            double beta = GAParameters.BETA;
            double crossoverRate = GAParameters.CROSSOVER_RATE;
            double mutationRate = GAParameters.MUTATION_RATE;
            Long randomSeed = null;

            for (int i = 0; i < args.length; i++) {
                switch (args[i]) {
                    case "--k":
                        k = Integer.parseInt(args[++i]);
                        break;
                    case "--populationSize":
                        populationSize = Integer.parseInt(args[++i]);
                        break;
                    case "--maxGenerations":
                        maxGenerations = Integer.parseInt(args[++i]);
                        break;
                    case "--mutationRate":
                        mutationRate = Double.parseDouble(args[++i]);
                        break;
                    case "--crossoverRate":
                        crossoverRate = Double.parseDouble(args[++i]);
                        break;
                    case "--archiveSize":
                        archiveSize = Integer.parseInt(args[++i]);
                        break;
                    case "--randomSeed":
                        randomSeed = Long.parseLong(args[++i]);
                        break;
                    case "--candidateCsv":
                        candidateCsv = resolvePath(args[++i]);
                        break;
                    case "--distanceMatrix":
                        distanceMatrixPath = resolvePath(args[++i]);
                        break;
                    case "--outputDir":
                        outputDirectory = resolvePath(args[++i]);
                        break;
                }
            }

            Path initialArchiveCsv = outputDirectory.resolve("initial_archive.csv");
            Path finalArchiveCsv = outputDirectory.resolve("final_archive.csv");
            Path runMetadataJson = outputDirectory.resolve("run_metadata.json");

            Files.createDirectories(outputDirectory);

            // 1. Load candidate data
            csvLoader.loadCandidates(candidateCsv.toString(), repository);
            repository.finalizeRepository();

            System.out.println("Total candidates loaded: " + repository.size());

            // 2. Load distance matrix
            double[][] distanceMatrix = distanceMatrixLoader.loadDistanceMatrix(distanceMatrixPath.toString());

            if (distanceMatrix.length != repository.size()) {
                throw new IllegalStateException(
                        "Distance matrix row count (" + distanceMatrix.length +
                                ") does not match repository size (" + repository.size() + ").");
            }

            if (distanceMatrix[0].length != repository.size()) {
                throw new IllegalStateException(
                        "Distance matrix column count (" + distanceMatrix[0].length +
                                ") does not match repository size (" + repository.size() + ").");
            }

            System.out.println(
                    "Distance matrix loaded: " +
                            distanceMatrix.length + " x " + distanceMatrix[0].length);

            PopulationInitializer populationInitializer = (randomSeed != null) ? new PopulationInitializer(randomSeed)
                    : new PopulationInitializer();

            // HV reference point in normalized space
            double referenceObjective1 = GAParameters.REFERENCE_POINT_F1;
            double referenceObjective2 = GAParameters.REFERENCE_POINT_F2;

            // Print parameter summary
            System.out.println("============== PARAMETERS ==============");
            System.out.println("K                : " + k);
            System.out.println("Population size  : " + populationSize);
            System.out.println("Archive size     : " + archiveSize);
            System.out.println("Max generations  : " + maxGenerations);
            System.out.println("Beta             : " + beta);
            System.out.println("Crossover rate   : " + crossoverRate);
            System.out.println("Mutation rate    : " + mutationRate);
            System.out.println("Random seed      : " + (randomSeed != null ? randomSeed : "none"));
            System.out.println("HV ref point     : (" + referenceObjective1 + ", " + referenceObjective2 + ")");
            System.out.println("========================================");

            // Export run metadata so plot_archives.py can read actual parameters
            long estimatedFunctionEvaluations = (long) populationSize * (maxGenerations + 1L);
            writeRunMetadata(runMetadataJson, k, populationSize, archiveSize, maxGenerations,
                    beta, crossoverRate, mutationRate, randomSeed, estimatedFunctionEvaluations);

            // 4. Initialize population
            System.out.println("STAGE Running Java GA");
            List<Integer> candidateIds = repository.getSelectableCandidateIds();
            if (candidateIds.isEmpty()) {
                throw new IllegalStateException("No selectable candidates found. All candidates may be forbidden.");
            }
            System.out.println("Selectable candidates: " + candidateIds.size());
            List<Individual> population = populationInitializer.initializePopulation(candidateIds, k, populationSize);

            List<Individual> archive = new ArrayList<>();

            // 5. Build dependencies
            FitnessCalculator fitnessCalculator = new FitnessCalculator(distanceMatrix, repository, beta);

            ObjectiveNormalizer objectiveNormalizer = new ObjectiveNormalizer();
            Dominance dominance = new Dominance();
            Pareto pareto = new Pareto(dominance);
            Truncation truncation = new Truncation();

            Evaluate evaluate = new Evaluate(
                    fitnessCalculator,
                    objectiveNormalizer,
                    dominance);

            Survivor survivor = new Survivor(
                    pareto,
                    truncation);

            Selection selection = (randomSeed != null) ? new Selection(randomSeed) : new Selection();
            Variation variation = (randomSeed != null) ? new Variation(randomSeed) : new Variation();

            HypervolumeIndicator hypervolumeIndicator = new HypervolumeIndicator(
                    pareto,
                    referenceObjective1,
                    referenceObjective2);

            // 6. Initial evaluation and archive creation
            List<Individual> evaluated = evaluate.run(population, archive);
            archive = survivor.run(evaluated, archiveSize);

            List<Individual> initialArchiveSnapshot = deepCopyIndividuals(archive);

            System.out.println("Generation 0 completed. Archive size: " + archive.size());

            // 7. Main SPEA2 loop
            for (int generation = 1; generation <= maxGenerations; generation++) {
                List<Individual> matingPool = selection.run(archive, populationSize);

                population = variation.run(
                        matingPool,
                        candidateIds,
                        populationSize,
                        k,
                        crossoverRate,
                        mutationRate);

                evaluated = evaluate.run(population, archive);
                archive = survivor.run(evaluated, archiveSize);

                // Compact progress line (one per generation)
                System.out.println("PROGRESS generation=" + generation + " max=" + maxGenerations);
            }

            // 8. Final archive snapshot
            List<Individual> finalArchiveSnapshot = deepCopyIndividuals(archive);

            // 9. Compute assessment bounds from FINAL ARCHIVE ND SET ONLY.
            //    This ensures the HV-space normalization reflects only the
            //    quality of the final optimized front, not the initial random
            //    baseline or any intermediate generation.
            List<Individual> finalNd = pareto.getNonDominated(finalArchiveSnapshot);

            double idealF1 = finalNd.stream().mapToDouble(Individual::getObjective1).min()
                    .orElseThrow(() -> new IllegalStateException("Final ND set is empty — cannot compute bounds."));
            double nadirF1 = finalNd.stream().mapToDouble(Individual::getObjective1).max().orElse(idealF1);
            double idealF2 = finalNd.stream().mapToDouble(Individual::getObjective2).min().orElse(Double.NaN);
            double nadirF2 = finalNd.stream().mapToDouble(Individual::getObjective2).max().orElse(idealF2);

            // 10. Normalize both archives using the final-ND-based bounds.
            //     Initial archive is normalized with the SAME bounds for CSV
            //     completeness (norm columns are present but not used for
            //     official assessment of the initial archive).
            objectiveNormalizer.normalizePopulationObjectives(
                    initialArchiveSnapshot,
                    idealF1, nadirF1,
                    idealF2, nadirF2);

            objectiveNormalizer.normalizePopulationObjectives(
                    finalArchiveSnapshot,
                    idealF1, nadirF1,
                    idealF2, nadirF2);

            // 11. Export archives
            writeArchiveCsv(initialArchiveSnapshot, initialArchiveCsv);
            writeArchiveCsv(finalArchiveSnapshot, finalArchiveCsv);

            // 12. Compute hypervolume — final archive only.
            double finalHypervolume = hypervolumeIndicator.compute(finalArchiveSnapshot);
            double finalHypervolumeRatio = hypervolumeIndicator.computeRatio(finalArchiveSnapshot);

            int initialNdCount = pareto.getNonDominated(initialArchiveSnapshot).size();
            int finalNdCount = finalNd.size();

            // Compute raw-objective improvement metrics (same formulas as plot_archives.py)
            List<Individual> initialNd = pareto.getNonDominated(initialArchiveSnapshot);

            double initBestF1 = initialNd.stream().mapToDouble(Individual::getObjective1).min().orElse(Double.NaN);
            double initBestF2 = initialNd.stream().mapToDouble(Individual::getObjective2).min().orElse(Double.NaN);
            double finalBestF1 = finalNd.stream().mapToDouble(Individual::getObjective1).min().orElse(Double.NaN);
            double finalBestF2 = finalNd.stream().mapToDouble(Individual::getObjective2).min().orElse(Double.NaN);

            double initMeanF1 = initialNd.stream().mapToDouble(Individual::getObjective1).average().orElse(Double.NaN);
            double initMeanF2 = initialNd.stream().mapToDouble(Individual::getObjective2).average().orElse(Double.NaN);
            double finalMeanF1 = finalNd.stream().mapToDouble(Individual::getObjective1).average().orElse(Double.NaN);
            double finalMeanF2 = finalNd.stream().mapToDouble(Individual::getObjective2).average().orElse(Double.NaN);

            double bestF1Improvement = safeImprovementPercent(initBestF1, finalBestF1);
            double bestF2Improvement = safeImprovementPercent(initBestF2, finalBestF2);
            double meanF1Improvement = safeImprovementPercent(initMeanF1, finalMeanF1);
            double meanF2Improvement = safeImprovementPercent(initMeanF2, finalMeanF2);

            // C-metric
            double cFinalInitial = coverageMetric(finalNd, initialNd, dominance);
            double cInitialFinal = coverageMetric(initialNd, finalNd, dominance);

            long endTimeNs = System.nanoTime();
            double runtimeSeconds = (endTimeNs - startTimeNs) / 1_000_000_000.0;

            // 13. Print final summary
            System.out.println("============== FINAL SUMMARY ==============");
            System.out.printf("Total runtime (s)            : %.2f%n", runtimeSeconds);
            System.out.println("Archive size                 : " + finalArchiveSnapshot.size());
            System.out.printf("Est. function evaluations    : %,d%n", estimatedFunctionEvaluations);
            System.out.println("Initial ND count (raw)       : " + initialNdCount);
            System.out.println("Final ND count (raw)         : " + finalNdCount);
            System.out.printf("Best f1 improvement (%%)      : %s%n", formatPercent(bestF1Improvement));
            System.out.printf("Best f2 improvement (%%)      : %s%n", formatPercent(bestF2Improvement));
            System.out.printf("Mean ND f1 improvement (%%)   : %s%n", formatPercent(meanF1Improvement));
            System.out.printf("Mean ND f2 improvement (%%)   : %s%n", formatPercent(meanF2Improvement));
            System.out.printf("C(Final, Initial)            : %s%n", formatPercent(cFinalInitial * 100));
            System.out.printf("C(Initial, Final)            : %s%n", formatPercent(cInitialFinal * 100));
            System.out.printf("Final hypervolume            : %.6f%n", finalHypervolume);
            System.out.printf("Final hypervolume ratio      : %.6f%n", finalHypervolumeRatio);
            System.out.println("HV ref point                 : (" + referenceObjective1 + ", " + referenceObjective2 + ")");
            System.out.printf("HV normalization bounds      : ideal=(%.6f, %.6f)  nadir=(%.6f, %.6f)%n",
                    idealF1, idealF2, nadirF1, nadirF2);
            System.out.println("(HV-space normalization is based ONLY on the final archive non-dominated set.)");
            System.out.println("============== CSV EXPORT ==============");
            System.out.println("Initial archive CSV : " + initialArchiveCsv.toAbsolutePath());
            System.out.println("Final archive CSV   : " + finalArchiveCsv.toAbsolutePath());
            System.out.println("===========================================");
            System.out.println("STAGE Completed Java GA");

        } catch (IOException e) {
            System.out.println("I/O error: " + e.getMessage());
        } catch (IllegalArgumentException | IllegalStateException e) {
            System.out.println("Runtime error: " + e.getMessage());
        } catch (Exception e) {
            System.out.println("Unexpected error: " + e.getMessage());
            e.printStackTrace();
        }
    }

    // -----------------------------------------------------------------------
    // Metadata export
    // -----------------------------------------------------------------------

    private static void writeRunMetadata(Path outputPath,
                                          int k, int populationSize, int archiveSize,
                                          int maxGenerations, double beta,
                                          double crossoverRate, double mutationRate,
                                          Long randomSeed,
                                          long estimatedFunctionEvaluations) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(outputPath)) {
            writer.write("{\n");
            writer.write("  \"k\": " + k + ",\n");
            writer.write("  \"populationSize\": " + populationSize + ",\n");
            writer.write("  \"archiveSize\": " + archiveSize + ",\n");
            writer.write("  \"maxGenerations\": " + maxGenerations + ",\n");
            writer.write("  \"beta\": " + beta + ",\n");
            writer.write("  \"crossoverRate\": " + crossoverRate + ",\n");
            writer.write("  \"mutationRate\": " + mutationRate + ",\n");
            writer.write("  \"randomSeed\": " + (randomSeed != null ? randomSeed : "null") + ",\n");
            writer.write("  \"estimatedFunctionEvaluations\": " + estimatedFunctionEvaluations + "\n");
            writer.write("}\n");
        }
    }

    // -----------------------------------------------------------------------
    // Improvement helpers — mirror the Python formulas in plot_archives.py
    // -----------------------------------------------------------------------

    /**
     * Percentage improvement for a minimization objective.
     * Positive value means the final is better (lower).
     */
    private static double safeImprovementPercent(double initialValue, double finalValue) {
        if (Double.isNaN(initialValue) || initialValue == 0) return Double.NaN;
        return (initialValue - finalValue) / initialValue * 100;
    }

    /**
     * C-metric: fraction of solutions in {@code setB} dominated by at least
     * one solution in {@code setA}.
     */
    private static double coverageMetric(List<Individual> setA, List<Individual> setB, Dominance dominance) {
        if (setB.isEmpty()) return Double.NaN;
        if (setA.isEmpty()) return 0.0;

        int dominatedCount = 0;
        for (Individual b : setB) {
            for (Individual a : setA) {
                if (dominates(a, b)) {
                    dominatedCount++;
                    break;
                }
            }
        }
        return (double) dominatedCount / setB.size();
    }

    /** Minimization dominance: a dominates b iff a <= b in all objectives and a < b in at least one. */
    private static boolean dominates(Individual a, Individual b) {
        boolean leqF1 = a.getObjective1() <= b.getObjective1();
        boolean leqF2 = a.getObjective2() <= b.getObjective2();
        boolean strict = a.getObjective1() < b.getObjective1() || a.getObjective2() < b.getObjective2();
        return leqF1 && leqF2 && strict;
    }

    private static String formatPercent(double value) {
        if (Double.isNaN(value)) return "N/A";
        return String.format("%.2f%%", value);
    }

    // -----------------------------------------------------------------------
    // Utility
    // -----------------------------------------------------------------------

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

    private static void writeArchiveCsv(List<Individual> archive, Path outputPath) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(outputPath)) {
            writer.write("archive_index,chromosome,f1,f2,norm_f1,norm_f2,strength,raw_fitness,density,total_fitness");
            writer.newLine();

            for (int i = 0; i < archive.size(); i++) {
                Individual individual = archive.get(i);

                writer.write((i + 1) + ",");
                writer.write(joinChromosome(individual.getChromosome()) + ",");
                writer.write(individual.getObjective1() + ",");
                writer.write(individual.getObjective2() + ",");
                writer.write(individual.getNormalizedObjective1() + ",");
                writer.write(individual.getNormalizedObjective2() + ",");
                writer.write(individual.getStrength() + ",");
                writer.write(individual.getRawFitness() + ",");
                writer.write(individual.getDensity() + ",");
                writer.write(individual.getTotalFitness() + "");
                writer.newLine();
            }
        }
    }

    private static String joinChromosome(List<Integer> chromosome) {
        StringBuilder builder = new StringBuilder();

        for (int i = 0; i < chromosome.size(); i++) {
            if (i > 0)
                builder.append("|");
            builder.append(chromosome.get(i));
        }

        return builder.toString();
    }

    private static Path resolveConfiguredPath(String envName, String defaultPath) {
        String configured = System.getenv(envName);
        if (configured == null || configured.isBlank()) {
            configured = defaultPath;
        }
        return resolvePath(configured);
    }

    private static Path resolvePath(String configuredPath) {
        Path path = Paths.get(configuredPath);
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

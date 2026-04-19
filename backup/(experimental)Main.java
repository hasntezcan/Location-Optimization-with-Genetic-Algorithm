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
import service.ObjectiveNormalizer;
import service.PopulationInitializer;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/**
 * Data-collection Main for objective-space calibration.
 *
 * Purpose:
 * - collect Pareto-relevant objective-space data across runs
 * - write one run summary row
 * - write all ND snapshot points as rows
 *
 * This Main is NOT focused on final hypervolume assessment.
 * It is focused on collecting data to later choose:
 * - ideal point
 * - nadir / reference point
 */
public class Main {

    private static final Path OUTPUT_DIRECTORY = Paths.get("output");
    private static final Path RUN_SUMMARY_CSV = OUTPUT_DIRECTORY.resolve("objective_space_run_summary.csv");
    private static final Path ND_POINTS_CSV = OUTPUT_DIRECTORY.resolve("objective_space_nd_points.csv");

    /**
     * Collect ND archive snapshots every N generations.
     * Example: 5 -> gen0, gen5, gen10, ...
     */
    private static final int SNAPSHOT_INTERVAL = 5;

    public static void main(String[] args) {
        long startTimeNs = System.nanoTime();

        String runLabel = args.length > 0 ? args[0] : "run";
        String runNote = args.length > 1 ? args[1] : "";

        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String runId = timestamp + "_" + runLabel;

        CandidateRepository repository = new CandidateRepository();
        CsvLoader csvLoader = new CsvLoader();
        PopulationInitializer populationInitializer = new PopulationInitializer();
        DistanceMatrixLoader distanceMatrixLoader = new DistanceMatrixLoader();

        try {
            Files.createDirectories(OUTPUT_DIRECTORY);

            Path initialArchiveCsv = OUTPUT_DIRECTORY.resolve(runId + "_initial_archive.csv");
            Path finalArchiveCsv = OUTPUT_DIRECTORY.resolve(runId + "_final_archive.csv");

            // 1. Load data
            csvLoader.loadCandidates("data/candidate_points.csv", repository);
            repository.finalizeRepository();

            double[][] distanceMatrix =
                    distanceMatrixLoader.loadDistanceMatrix("data/kadikoy_distance_meters_nxn.npy");

            if (distanceMatrix.length != repository.size() || distanceMatrix[0].length != repository.size()) {
                throw new IllegalStateException("Distance matrix dimensions do not match repository size.");
            }

            // 2. Parameters
            int k = GAParameters.K;
            int populationSize = GAParameters.POPULATION_SIZE;
            int archiveSize = GAParameters.ARCHIVE_SIZE;
            int maxGenerations = GAParameters.MAX_GENERATIONS;
            double beta = GAParameters.BETA;
            double crossoverRate = GAParameters.CROSSOVER_RATE;
            double mutationRate = GAParameters.MUTATION_RATE;

            // 3. Build dependencies
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

            // 4. Initialize
            List<Integer> candidateIds = repository.getAllCandidateIds();
            List<Individual> population =
                    populationInitializer.initializePopulation(candidateIds, k, populationSize);

            List<Individual> archive = new ArrayList<>();

            // 5. ND point records for objective-space analysis
            List<PointRecord> ndPointRecords = new ArrayList<>();

            // 6. Generation 0
            List<Individual> evaluated = evaluate.run(population, archive);
            archive = survivor.run(evaluated, archiveSize);

            List<Individual> initialArchiveSnapshot = deepCopyIndividuals(archive);
            addNdSnapshot(ndPointRecords, archive, pareto, 0, "gen0_nd");

            System.out.println("Run ID: " + runId);
            System.out.println("Generation 0 completed.");
            System.out.println("Initial archive size: " + initialArchiveSnapshot.size());

            // 7. Main loop
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

                if (generation % SNAPSHOT_INTERVAL == 0 || generation == maxGenerations) {
                    addNdSnapshot(ndPointRecords, archive, pareto, generation, "periodic_nd");
                }

                double bestF1 = archive.stream()
                        .mapToDouble(Individual::getObjective1)
                        .min()
                        .orElse(Double.NaN);

                double bestF2 = archive.stream()
                        .mapToDouble(Individual::getObjective2)
                        .min()
                        .orElse(Double.NaN);

                System.out.println("Generation " + generation + " completed.");
                System.out.printf("  Best f1 : %.6f%n", bestF1);
                System.out.printf("  Best f2 : %.6f%n", bestF2);
            }

            // 8. Final archive
            List<Individual> finalArchiveSnapshot = deepCopyIndividuals(archive);
            addNdSnapshot(ndPointRecords, finalArchiveSnapshot, pareto, maxGenerations, "final_nd");

            // 9. Compute reference bounds from all collected ND points
            List<Individual> referenceIndividuals = extractIndividuals(ndPointRecords);
            double[] referenceBounds = computeObjectiveBounds(referenceIndividuals);

            double refMinF1 = referenceBounds[0];
            double refMaxF1 = referenceBounds[1];
            double refMinF2 = referenceBounds[2];
            double refMaxF2 = referenceBounds[3];

            // 10. Normalize initial/final archives in the same collected objective space
            objectiveNormalizer.normalizePopulationObjectives(
                    initialArchiveSnapshot,
                    refMinF1,
                    refMaxF1,
                    refMinF2,
                    refMaxF2
            );

            objectiveNormalizer.normalizePopulationObjectives(
                    finalArchiveSnapshot,
                    refMinF1,
                    refMaxF1,
                    refMinF2,
                    refMaxF2
            );

            // 11. Export archives
            writeArchiveCsv(initialArchiveSnapshot, initialArchiveCsv);
            writeArchiveCsv(finalArchiveSnapshot, finalArchiveCsv);

            // 12. Append ND points for frequency analysis
            appendNdPointsCsv(ND_POINTS_CSV, runId, runLabel, ndPointRecords);

            // 13. Build summary stats
            List<Individual> initialNd = pareto.getNonDominated(initialArchiveSnapshot);
            List<Individual> finalNd = pareto.getNonDominated(finalArchiveSnapshot);

            double[] initialArchiveBounds = computeObjectiveBounds(initialArchiveSnapshot);
            double[] finalArchiveBounds = computeObjectiveBounds(finalArchiveSnapshot);
            double[] initialNdBounds = computeObjectiveBounds(initialNd);
            double[] finalNdBounds = computeObjectiveBounds(finalNd);

            long endTimeNs = System.nanoTime();
            double runtimeSeconds = (endTimeNs - startTimeNs) / 1_000_000_000.0;

            appendRunSummary(
                    RUN_SUMMARY_CSV,
                    runId,
                    timestamp,
                    runLabel,
                    runNote,
                    k,
                    populationSize,
                    archiveSize,
                    maxGenerations,
                    beta,
                    crossoverRate,
                    mutationRate,
                    SNAPSHOT_INTERVAL,
                    ndPointRecords.size(),
                    refMinF1,
                    refMaxF1,
                    refMinF2,
                    refMaxF2,
                    initialArchiveSnapshot.size(),
                    initialNd.size(),
                    initialArchiveBounds[0],
                    initialArchiveBounds[1],
                    initialArchiveBounds[2],
                    initialArchiveBounds[3],
                    initialNdBounds[0],
                    initialNdBounds[1],
                    initialNdBounds[2],
                    initialNdBounds[3],
                    finalArchiveSnapshot.size(),
                    finalNd.size(),
                    finalArchiveBounds[0],
                    finalArchiveBounds[1],
                    finalArchiveBounds[2],
                    finalArchiveBounds[3],
                    finalNdBounds[0],
                    finalNdBounds[1],
                    finalNdBounds[2],
                    finalNdBounds[3],
                    runtimeSeconds,
                    initialArchiveCsv.toAbsolutePath().toString(),
                    finalArchiveCsv.toAbsolutePath().toString()
            );

            // 14. Console summary
            System.out.println("============== OBJECTIVE SPACE SUMMARY ==============");
            System.out.println("Run ID                  : " + runId);
            System.out.println("Run label               : " + runLabel);
            System.out.println("Reference ND point rows : " + ndPointRecords.size());
            System.out.println("Reference min f1        : " + refMinF1);
            System.out.println("Reference max f1        : " + refMaxF1);
            System.out.println("Reference min f2        : " + refMinF2);
            System.out.println("Reference max f2        : " + refMaxF2);
            System.out.println("Initial ND count        : " + initialNd.size());
            System.out.println("Final ND count          : " + finalNd.size());
            System.out.println("Runtime (sec)           : " + runtimeSeconds);
            System.out.println("Summary CSV             : " + RUN_SUMMARY_CSV.toAbsolutePath());
            System.out.println("ND points CSV           : " + ND_POINTS_CSV.toAbsolutePath());
            System.out.println("Initial archive CSV     : " + initialArchiveCsv.toAbsolutePath());
            System.out.println("Final archive CSV       : " + finalArchiveCsv.toAbsolutePath());

        } catch (IOException e) {
            System.out.println("I/O error: " + e.getMessage());
        } catch (IllegalArgumentException | IllegalStateException e) {
            System.out.println("Runtime error: " + e.getMessage());
        } catch (Exception e) {
            System.out.println("Unexpected error: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private static void addNdSnapshot(List<PointRecord> records,
                                      List<Individual> source,
                                      Pareto pareto,
                                      int generation,
                                      String stage) {
        List<Individual> nd = pareto.getNonDominated(source);
        List<Individual> copies = deepCopyIndividuals(nd);

        for (Individual individual : copies) {
            records.add(new PointRecord(generation, stage, individual));
        }
    }

    private static List<Individual> extractIndividuals(List<PointRecord> records) {
        List<Individual> individuals = new ArrayList<>();
        for (PointRecord record : records) {
            individuals.add(record.individual);
        }
        return individuals;
    }

    private static double[] computeObjectiveBounds(List<Individual> individuals) {
        if (individuals == null || individuals.isEmpty()) {
            throw new IllegalArgumentException("Individual list cannot be null or empty.");
        }

        double minF1 = Double.POSITIVE_INFINITY;
        double maxF1 = Double.NEGATIVE_INFINITY;
        double minF2 = Double.POSITIVE_INFINITY;
        double maxF2 = Double.NEGATIVE_INFINITY;

        for (Individual individual : individuals) {
            if (individual.getObjective1() == null || individual.getObjective2() == null) {
                throw new IllegalStateException("Raw objectives must be assigned before computing bounds.");
            }

            double f1 = individual.getObjective1();
            double f2 = individual.getObjective2();

            if (f1 < minF1) minF1 = f1;
            if (f1 > maxF1) maxF1 = f1;
            if (f2 < minF2) minF2 = f2;
            if (f2 > maxF2) maxF2 = f2;
        }

        return new double[]{minF1, maxF1, minF2, maxF2};
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

    private static void appendNdPointsCsv(Path csvPath,
                                          String runId,
                                          String runLabel,
                                          List<PointRecord> records) throws IOException {
        boolean writeHeader = Files.notExists(csvPath);

        try (BufferedWriter writer = Files.newBufferedWriter(
                csvPath,
                StandardOpenOption.CREATE,
                StandardOpenOption.APPEND
        )) {
            if (writeHeader) {
                writer.write("run_id,run_label,generation,stage,chromosome,f1,f2");
                writer.newLine();
            }

            for (PointRecord record : records) {
                writer.write(escape(runId) + ",");
                writer.write(escape(runLabel) + ",");
                writer.write(record.generation + ",");
                writer.write(escape(record.stage) + ",");
                writer.write(escape(joinChromosome(record.individual.getChromosome())) + ",");
                writer.write(record.individual.getObjective1() + ",");
                writer.write(record.individual.getObjective2() + "");
                writer.newLine();
            }
        }
    }

    private static void appendRunSummary(
            Path csvPath,
            String runId,
            String timestamp,
            String runLabel,
            String runNote,
            int k,
            int populationSize,
            int archiveSize,
            int maxGenerations,
            double beta,
            double crossoverRate,
            double mutationRate,
            int snapshotInterval,
            int referenceNdPointRows,
            double refMinF1,
            double refMaxF1,
            double refMinF2,
            double refMaxF2,
            int initialArchiveSize,
            int initialNdCount,
            double initialArchiveMinF1,
            double initialArchiveMaxF1,
            double initialArchiveMinF2,
            double initialArchiveMaxF2,
            double initialNdMinF1,
            double initialNdMaxF1,
            double initialNdMinF2,
            double initialNdMaxF2,
            int finalArchiveSize,
            int finalNdCount,
            double finalArchiveMinF1,
            double finalArchiveMaxF1,
            double finalArchiveMinF2,
            double finalArchiveMaxF2,
            double finalNdMinF1,
            double finalNdMaxF1,
            double finalNdMinF2,
            double finalNdMaxF2,
            double runtimeSeconds,
            String initialArchiveCsvPath,
            String finalArchiveCsvPath
    ) throws IOException {

        boolean writeHeader = Files.notExists(csvPath);

        try (BufferedWriter writer = Files.newBufferedWriter(
                csvPath,
                StandardOpenOption.CREATE,
                StandardOpenOption.APPEND
        )) {
            if (writeHeader) {
                writer.write(
                        "run_id,timestamp,run_label,run_note," +
                        "k,population_size,archive_size,max_generations,beta,crossover_rate,mutation_rate,snapshot_interval," +
                        "reference_nd_point_rows,ref_min_f1,ref_max_f1,ref_min_f2,ref_max_f2," +
                        "initial_archive_size,initial_nd_count,initial_archive_min_f1,initial_archive_max_f1,initial_archive_min_f2,initial_archive_max_f2," +
                        "initial_nd_min_f1,initial_nd_max_f1,initial_nd_min_f2,initial_nd_max_f2," +
                        "final_archive_size,final_nd_count,final_archive_min_f1,final_archive_max_f1,final_archive_min_f2,final_archive_max_f2," +
                        "final_nd_min_f1,final_nd_max_f1,final_nd_min_f2,final_nd_max_f2," +
                        "runtime_seconds,initial_archive_csv,final_archive_csv"
                );
                writer.newLine();
            }

            writer.write(
                    escape(runId) + "," +
                    escape(timestamp) + "," +
                    escape(runLabel) + "," +
                    escape(runNote) + "," +
                    k + "," +
                    populationSize + "," +
                    archiveSize + "," +
                    maxGenerations + "," +
                    beta + "," +
                    crossoverRate + "," +
                    mutationRate + "," +
                    snapshotInterval + "," +
                    referenceNdPointRows + "," +
                    refMinF1 + "," +
                    refMaxF1 + "," +
                    refMinF2 + "," +
                    refMaxF2 + "," +
                    initialArchiveSize + "," +
                    initialNdCount + "," +
                    initialArchiveMinF1 + "," +
                    initialArchiveMaxF1 + "," +
                    initialArchiveMinF2 + "," +
                    initialArchiveMaxF2 + "," +
                    initialNdMinF1 + "," +
                    initialNdMaxF1 + "," +
                    initialNdMinF2 + "," +
                    initialNdMaxF2 + "," +
                    finalArchiveSize + "," +
                    finalNdCount + "," +
                    finalArchiveMinF1 + "," +
                    finalArchiveMaxF1 + "," +
                    finalArchiveMinF2 + "," +
                    finalArchiveMaxF2 + "," +
                    finalNdMinF1 + "," +
                    finalNdMaxF1 + "," +
                    finalNdMinF2 + "," +
                    finalNdMaxF2 + "," +
                    runtimeSeconds + "," +
                    escape(initialArchiveCsvPath) + "," +
                    escape(finalArchiveCsvPath)
            );
            writer.newLine();
        }
    }

    private static String joinChromosome(List<Integer> chromosome) {
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < chromosome.size(); i++) {
            if (i > 0) builder.append("|");
            builder.append(chromosome.get(i));
        }
        return builder.toString();
    }

    private static String escape(String value) {
        if (value == null) return "";
        if (value.contains(",") || value.contains("\"")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    private static final class PointRecord {
        final int generation;
        final String stage;
        final Individual individual;

        PointRecord(int generation, String stage, Individual individual) {
            this.generation = generation;
            this.stage = stage;
            this.individual = individual;
        }
    }
}
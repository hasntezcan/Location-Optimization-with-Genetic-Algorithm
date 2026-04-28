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
 * Main SPEA2 workflow using FIXED assessment bounds from GAParameters.
 *
 * Purpose:
 * - run the optimization
 * - keep initial and final archive snapshots
 * - normalize both archives in the SAME fixed objective space
 * - compute comparable hypervolume values
 */
public class Main {

    private static final Path OUTPUT_DIRECTORY = Paths.get("output");
    private static final Path INITIAL_ARCHIVE_CSV = OUTPUT_DIRECTORY.resolve("initial_archive.csv");
    private static final Path FINAL_ARCHIVE_CSV = OUTPUT_DIRECTORY.resolve("final_archive.csv");

    public static void main(String[] args) {
        long startTimeNs = System.nanoTime();

        CandidateRepository repository = new CandidateRepository();
        CsvLoader csvLoader = new CsvLoader();
        DistanceMatrixLoader distanceMatrixLoader = new DistanceMatrixLoader();

        try {
            Files.createDirectories(OUTPUT_DIRECTORY);

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
                    case "--k": k = Integer.parseInt(args[++i]); break;
                    case "--populationSize": populationSize = Integer.parseInt(args[++i]); break;
                    case "--maxGenerations": maxGenerations = Integer.parseInt(args[++i]); break;
                    case "--mutationRate": mutationRate = Double.parseDouble(args[++i]); break;
                    case "--crossoverRate": crossoverRate = Double.parseDouble(args[++i]); break;
                    case "--archiveSize": archiveSize = Integer.parseInt(args[++i]); break;
                    case "--randomSeed": randomSeed = Long.parseLong(args[++i]); break;
                }
            }

            PopulationInitializer populationInitializer = (randomSeed != null) ? new PopulationInitializer(randomSeed) : new PopulationInitializer();

            // Fixed assessment bounds from GAParameters
            double assessmentIdealF1 = GAParameters.ASSESSMENT_IDEAL_F1;
            double assessmentNadirF1 = GAParameters.ASSESSMENT_NADIR_F1;
            double assessmentIdealF2 = GAParameters.ASSESSMENT_IDEAL_F2;
            double assessmentNadirF2 = GAParameters.ASSESSMENT_NADIR_F2;

            // HV reference point in normalized space
            double referenceObjective1 = GAParameters.REFERENCE_POINT_F1;
            double referenceObjective2 = GAParameters.REFERENCE_POINT_F2;

            // 4. Initialize population
            System.out.println("STAGE Running Java GA");
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

            Selection selection = (randomSeed != null) ? new Selection(randomSeed) : new Selection();
            Variation variation = (randomSeed != null) ? new Variation(randomSeed) : new Variation();

            HypervolumeIndicator hypervolumeIndicator = new HypervolumeIndicator(
                    pareto,
                    referenceObjective1,
                    referenceObjective2
            );

            // 6. Initial evaluation and archive creation
            List<Individual> evaluated = evaluate.run(population, archive);
            archive = survivor.run(evaluated, archiveSize);

            List<Individual> initialArchiveSnapshot = deepCopyIndividuals(archive);

            System.out.println("Generation 0 completed.");
            System.out.println("Evaluated individual count: " + evaluated.size());
            System.out.println("Archive size: " + archive.size());

            // 7. Main SPEA2 loop
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

                double bestF1 = archive.stream()
                        .mapToDouble(Individual::getObjective1)
                        .min()
                        .orElse(Double.NaN);

                double bestF2 = archive.stream()
                        .mapToDouble(Individual::getObjective2)
                        .min()
                        .orElse(Double.NaN);

                System.out.println("PROGRESS generation=" + generation + " max=" + maxGenerations);
                System.out.println("Generation " + generation + " completed.");
                System.out.println("Population size: " + population.size());
                System.out.println("Archive size   : " + archive.size());
                System.out.printf("  Best f1      : %.6f%n", bestF1);
                System.out.printf("  Best f2      : %.6f%n", bestF2);
                System.out.println("--------------------------------------------");
            }

            // 8. Final archive snapshot
            List<Individual> finalArchiveSnapshot = deepCopyIndividuals(archive);

            // 8.5 Dynamically update assessment bounds based on only NON-DOMINATED solutions found
            List<Individual> allSolutions = new ArrayList<>(initialArchiveSnapshot);
            allSolutions.addAll(finalArchiveSnapshot);
            List<Individual> nonDominatedSolutions = pareto.getNonDominated(allSolutions);

            double dynamicMinF1 = nonDominatedSolutions.stream().mapToDouble(Individual::getObjective1).min().orElse(assessmentIdealF1);
            double dynamicMaxF1 = nonDominatedSolutions.stream().mapToDouble(Individual::getObjective1).max().orElse(assessmentNadirF1);
            double dynamicMinF2 = nonDominatedSolutions.stream().mapToDouble(Individual::getObjective2).min().orElse(assessmentIdealF2);
            double dynamicMaxF2 = nonDominatedSolutions.stream().mapToDouble(Individual::getObjective2).max().orElse(assessmentNadirF2);

            // Add 5% padding to avoid points being exactly at 0 or 1
            double padding = 0.05;
            double f1Range = dynamicMaxF1 - dynamicMinF1;
            double f2Range = dynamicMaxF2 - dynamicMinF2;
            
            double paddedMinF1 = dynamicMinF1 - padding * f1Range;
            double paddedMaxF1 = dynamicMaxF1 + padding * f1Range;
            double paddedMinF2 = dynamicMinF2 - padding * f2Range;
            double paddedMaxF2 = dynamicMaxF2 + padding * f2Range;

            // 9. Normalize initial and final archives in the SAME dynamic objective space
            objectiveNormalizer.normalizePopulationObjectives(
                    initialArchiveSnapshot,
                    paddedMinF1,
                    paddedMaxF1,
                    paddedMinF2,
                    paddedMaxF2
            );

            objectiveNormalizer.normalizePopulationObjectives(
                    finalArchiveSnapshot,
                    paddedMinF1,
                    paddedMaxF1,
                    paddedMinF2,
                    paddedMaxF2
            );

            System.out.println("============== DYNAMIC ASSESSMENT BOUNDS ==============");
            System.out.println("Padded Min f1 : " + paddedMinF1);
            System.out.println("Padded Max f1 : " + paddedMaxF1);
            System.out.println("Padded Min f2 : " + paddedMinF2);
            System.out.println("Padded Max f2 : " + paddedMaxF2);

            // 10. Export archives
            writeArchiveCsv(initialArchiveSnapshot, INITIAL_ARCHIVE_CSV);
            writeArchiveCsv(finalArchiveSnapshot, FINAL_ARCHIVE_CSV);

            // 11. Compute hypervolume
            double initialHypervolume = hypervolumeIndicator.compute(initialArchiveSnapshot);
            double initialHypervolumeRatio = hypervolumeIndicator.computeRatio(initialArchiveSnapshot);

            double finalHypervolume = hypervolumeIndicator.compute(finalArchiveSnapshot);
            double finalHypervolumeRatio = hypervolumeIndicator.computeRatio(finalArchiveSnapshot);

            int initialNdCount = pareto.getNonDominated(initialArchiveSnapshot).size();
            int finalNdCount = pareto.getNonDominated(finalArchiveSnapshot).size();

            long endTimeNs = System.nanoTime();
            double runtimeSeconds = (endTimeNs - startTimeNs) / 1_000_000_000.0;

            // 12. Print summary
            System.out.println("============== FIXED ASSESSMENT BOUNDS ==============");
            System.out.println("Ideal f1 : " + assessmentIdealF1);
            System.out.println("Nadir f1 : " + assessmentNadirF1);
            System.out.println("Ideal f2 : " + assessmentIdealF2);
            System.out.println("Nadir f2 : " + assessmentNadirF2);

            System.out.println("============== NON-DOMINATED COUNTS ==============");
            System.out.println("Initial ND count : " + initialNdCount);
            System.out.println("Final ND count   : " + finalNdCount);

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

            System.out.println("============== CSV EXPORT ==============");
            System.out.println("Initial archive CSV : " + INITIAL_ARCHIVE_CSV.toAbsolutePath());
            System.out.println("Final archive CSV   : " + FINAL_ARCHIVE_CSV.toAbsolutePath());

            System.out.println("============== RUNTIME ==============");
            System.out.println("Total runtime (seconds): " + runtimeSeconds);
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
            if (i > 0) builder.append("|");
            builder.append(chromosome.get(i));
        }

        return builder.toString();
    }
}
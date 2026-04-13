package algorithm;

import model.Individual;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;

/**
 * Generates offspring from a mating pool using crossover and mutation.
 *
 * <p>This class preserves the chromosome length and ensures that each offspring
 * chromosome contains unique candidate IDs. It is designed for the parcel
 * locker location problem, where each chromosome is a fixed-size set of
 * selected candidate point IDs.</p>
 */
public class Variation {

    private final Random random;

    /**
     * Creates a variation component with a default random number generator.
     */
    public Variation() {
        this.random = new Random();
    }

    /**
     * Creates a variation component with a fixed random seed.
     *
     * @param seed random seed
     */
    public Variation(long seed) {
        this.random = new Random(seed);
    }

    /**
     * Generates an offspring population from the given mating pool.
     *
     * @param matingPool selected parent pool
     * @param candidateIds all valid candidate IDs in the search space
     * @param populationSize target offspring population size
     * @param chromosomeLength fixed chromosome length
     * @param crossoverRate crossover probability in the range {@code [0, 1]}
     * @param mutationRate mutation probability in the range {@code [0, 1]}
     * @return generated offspring population
     * @throws IllegalArgumentException if any input is invalid
     */
    public List<Individual> run(List<Individual> matingPool,
                                List<Integer> candidateIds,
                                int populationSize,
                                int chromosomeLength,
                                double crossoverRate,
                                double mutationRate) {
        validateInputs(matingPool, candidateIds, populationSize, chromosomeLength, crossoverRate, mutationRate);

        List<Individual> offspring = new ArrayList<>();

        int parentIndex = 0;

        while (offspring.size() < populationSize) {
            Individual parent1 = matingPool.get(parentIndex % matingPool.size());
            Individual parent2 = matingPool.get((parentIndex + 1) % matingPool.size());

            List<Integer> child1Chromosome;
            List<Integer> child2Chromosome;

            if (random.nextDouble() < crossoverRate) {
                List<List<Integer>> children = crossover(
                        parent1.getChromosome(),
                        parent2.getChromosome(),
                        chromosomeLength,
                        candidateIds
                );
                child1Chromosome = children.get(0);
                child2Chromosome = children.get(1);
            } else {
                child1Chromosome = new ArrayList<>(parent1.getChromosome());
                child2Chromosome = new ArrayList<>(parent2.getChromosome());
            }

            if (random.nextDouble() < mutationRate) {
                mutate(child1Chromosome, candidateIds);
            }

            if (random.nextDouble() < mutationRate) {
                mutate(child2Chromosome, candidateIds);
            }

            repairChromosome(child1Chromosome, candidateIds, chromosomeLength);
            repairChromosome(child2Chromosome, candidateIds, chromosomeLength);

            offspring.add(new Individual(child1Chromosome));

            if (offspring.size() < populationSize) {
                offspring.add(new Individual(child2Chromosome));
            }

            parentIndex += 2;
        }

        return offspring;
    }

    /**
     * Performs crossover between two parent chromosomes and returns two children.
     *
     * <p>This implementation uses shared-gene priority recombination. Genes
     * that appear in both parents are guaranteed to be present in both
     * children, preserving proven gene combinations. The remaining chromosome
     * slots are filled from the parent-exclusive genes in shuffled order so
     * that each child receives a different mix. A final repair step ensures
     * correctness.</p>
     *
     * @param parent1 first parent chromosome
     * @param parent2 second parent chromosome
     * @param chromosomeLength fixed chromosome length
     * @param candidateIds all valid candidate IDs
     * @return two child chromosomes
     */
    private List<List<Integer>> crossover(List<Integer> parent1,
                                          List<Integer> parent2,
                                          int chromosomeLength,
                                          List<Integer> candidateIds) {
        Set<Integer> set1 = new HashSet<>(parent1);
        Set<Integer> set2 = new HashSet<>(parent2);

        List<Integer> shared = new ArrayList<>();
        List<Integer> exclusive = new ArrayList<>();

        for (Integer gene : set1) {
            if (set2.contains(gene)) {
                shared.add(gene);
            } else {
                exclusive.add(gene);
            }
        }

        for (Integer gene : set2) {
            if (!set1.contains(gene)) {
                exclusive.add(gene);
            }
        }

        // Both children start with the shared genes
        List<Integer> child1 = new ArrayList<>(shared);
        List<Integer> child2 = new ArrayList<>(shared);

        // Fill remaining slots from the exclusive gene pool
        shuffle(exclusive);

        for (Integer gene : exclusive) {
            if (child1.size() < chromosomeLength) {
                child1.add(gene);
            }
        }

        shuffle(exclusive);

        Set<Integer> child2Set = new HashSet<>(child2);
        for (Integer gene : exclusive) {
            if (child2.size() >= chromosomeLength) {
                break;
            }
            if (child2Set.add(gene)) {
                child2.add(gene);
            }
        }

        repairChromosome(child1, candidateIds, chromosomeLength);
        repairChromosome(child2, candidateIds, chromosomeLength);

        List<List<Integer>> children = new ArrayList<>();
        children.add(child1);
        children.add(child2);

        return children;
    }

    /**
     * Mutates a chromosome by replacing one randomly selected gene with a new
     * valid candidate ID not already present in the chromosome.
     *
     * @param chromosome chromosome to mutate
     * @param candidateIds all valid candidate IDs
     */
    private void mutate(List<Integer> chromosome, List<Integer> candidateIds) {
        if (chromosome.isEmpty()) {
            return;
        }

        int mutationIndex = random.nextInt(chromosome.size());

        Set<Integer> used = new HashSet<>(chromosome);
        List<Integer> available = new ArrayList<>();

        for (Integer candidateId : candidateIds) {
            if (!used.contains(candidateId)) {
                available.add(candidateId);
            }
        }

        if (available.isEmpty()) {
            return;
        }

        int newGene = available.get(random.nextInt(available.size()));
        chromosome.set(mutationIndex, newGene);
    }

    /**
     * Repairs a chromosome so that it has exactly the required length and
     * contains only unique genes.
     *
     * @param chromosome chromosome to repair
     * @param candidateIds all valid candidate IDs
     * @param chromosomeLength required chromosome length
     */
    private void repairChromosome(List<Integer> chromosome,
                                  List<Integer> candidateIds,
                                  int chromosomeLength) {
        List<Integer> uniqueGenes = new ArrayList<>();
        Set<Integer> seen = new HashSet<>();

        for (Integer gene : chromosome) {
            if (seen.add(gene)) {
                uniqueGenes.add(gene);
            }
        }

        List<Integer> available = new ArrayList<>();
        for (Integer candidateId : candidateIds) {
            if (!seen.contains(candidateId)) {
                available.add(candidateId);
            }
        }

        shuffle(available);

        int fillIndex = 0;
        while (uniqueGenes.size() < chromosomeLength && fillIndex < available.size()) {
            uniqueGenes.add(available.get(fillIndex));
            fillIndex++;
        }

        while (uniqueGenes.size() > chromosomeLength) {
            uniqueGenes.remove(uniqueGenes.size() - 1);
        }

        chromosome.clear();
        chromosome.addAll(uniqueGenes);
    }

    /**
     * Validates the inputs of the variation stage.
     *
     * @param matingPool mating pool
     * @param candidateIds candidate ID universe
     * @param populationSize offspring population size
     * @param chromosomeLength fixed chromosome length
     * @param crossoverRate crossover probability
     * @param mutationRate mutation probability
     */
    private void validateInputs(List<Individual> matingPool,
                                List<Integer> candidateIds,
                                int populationSize,
                                int chromosomeLength,
                                double crossoverRate,
                                double mutationRate) {
        if (matingPool == null || matingPool.isEmpty()) {
            throw new IllegalArgumentException("Mating pool cannot be null or empty.");
        }

        if (candidateIds == null || candidateIds.isEmpty()) {
            throw new IllegalArgumentException("Candidate ID list cannot be null or empty.");
        }

        if (populationSize <= 0) {
            throw new IllegalArgumentException("Population size must be greater than 0.");
        }

        if (chromosomeLength <= 0) {
            throw new IllegalArgumentException("Chromosome length must be greater than 0.");
        }

        if (chromosomeLength > candidateIds.size()) {
            throw new IllegalArgumentException(
                    "Chromosome length cannot be greater than the number of available candidate IDs."
            );
        }

        if (crossoverRate < 0.0 || crossoverRate > 1.0) {
            throw new IllegalArgumentException("Crossover rate must be in the range [0, 1].");
        }

        if (mutationRate < 0.0 || mutationRate > 1.0) {
            throw new IllegalArgumentException("Mutation rate must be in the range [0, 1].");
        }
    }

    /**
     * Randomly shuffles a list using the internal random number generator.
     *
     * @param list list to shuffle
     */
    private void shuffle(List<Integer> list) {
        for (int i = list.size() - 1; i > 0; i--) {
            int j = random.nextInt(i + 1);

            Integer temp = list.get(i);
            list.set(i, list.get(j));
            list.set(j, temp);
        }
    }
}
package algorithm;

import algorithm.helper.Pareto;
import algorithm.helper.Truncation;
import model.Individual;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Builds the next SPEA2 archive from the evaluated merged population.
 *
 * <p>This class applies the standard SPEA2 survivor-selection logic:
 * first the non-dominated individuals are collected. If their count is
 * smaller than the archive size, the archive is filled with the best
 * remaining dominated individuals according to total fitness. If their
 * count is larger than the archive size, truncation is applied.</p>
 *
 * <p>In addition, duplicate solutions are removed based on canonical
 * chromosome equality. This prevents the archive from being filled with
 * identical copies of the same solution.</p>
 */
public class Survivor {

    private final Pareto pareto;
    private final Truncation truncation;

    /**
     * Creates a survivor-selection component with the required helpers.
     *
     * @param pareto helper used to extract non-dominated individuals
     * @param truncation helper used when the archive exceeds its size limit
     * @throws IllegalArgumentException if any dependency is {@code null}
     */
    public Survivor(Pareto pareto, Truncation truncation) {
        if (pareto == null) {
            throw new IllegalArgumentException("Pareto cannot be null.");
        }
        if (truncation == null) {
            throw new IllegalArgumentException("Truncation cannot be null.");
        }

        this.pareto = pareto;
        this.truncation = truncation;
    }

    /**
     * Selects the next archive from the fully evaluated merged population.
     *
     * <p>The input list is expected to already contain valid SPEA2 evaluation
     * fields, including objectives, density, and total fitness.</p>
     *
     * @param evaluatedMergedPopulation evaluated merged population
     * @param archiveSize target archive size
     * @return next archive
     * @throws IllegalArgumentException if the population is {@code null}
     *                                  or if {@code archiveSize} is negative
     */
    public List<Individual> run(List<Individual> evaluatedMergedPopulation, int archiveSize) {
        if (evaluatedMergedPopulation == null) {
            throw new IllegalArgumentException("Evaluated merged population cannot be null.");
        }

        if (archiveSize < 0) {
            throw new IllegalArgumentException("Archive size cannot be negative.");
        }

        List<Individual> nonDominated = pareto.getNonDominated(evaluatedMergedPopulation);
        nonDominated = deduplicateByChromosome(nonDominated);

        if (nonDominated.size() == archiveSize) {
            return new ArrayList<>(nonDominated);
        }

        if (nonDominated.size() < archiveSize) {
            return fillArchive(nonDominated, evaluatedMergedPopulation, archiveSize);
        }

        return truncation.run(nonDominated, archiveSize);
    }

    /**
     * Fills an incomplete archive with the best dominated individuals according
     * to total fitness, in ascending order.
     *
     * @param nonDominated current non-dominated archive candidates
     * @param evaluatedMergedPopulation full evaluated merged population
     * @param archiveSize target archive size
     * @return completed archive
     */
    private List<Individual> fillArchive(List<Individual> nonDominated,
                                         List<Individual> evaluatedMergedPopulation,
                                         int archiveSize) {
        List<Individual> archive = new ArrayList<>(nonDominated);
        List<Individual> dominated = collectDominatedIndividuals(nonDominated, evaluatedMergedPopulation);

        dominated = deduplicateByChromosome(dominated);
        dominated.sort(Comparator.comparingDouble(Individual::getTotalFitness));

        for (Individual individual : dominated) {
            if (archive.size() >= archiveSize) {
                break;
            }

            if (!containsSameChromosome(archive, individual)) {
                archive.add(individual);
            }
        }

        return archive;
    }

    /**
     * Collects all dominated individuals from the evaluated merged population.
     *
     * @param nonDominated non-dominated set
     * @param evaluatedMergedPopulation full evaluated merged population
     * @return dominated individuals
     */
    private List<Individual> collectDominatedIndividuals(List<Individual> nonDominated,
                                                         List<Individual> evaluatedMergedPopulation) {
        List<Individual> dominated = new ArrayList<>();

        for (Individual individual : evaluatedMergedPopulation) {
            if (!containsSameChromosome(nonDominated, individual)) {
                dominated.add(individual);
            }
        }

        return dominated;
    }

    /**
     * Removes duplicate solutions from a list using chromosome equality.
     *
     * <p>Because chromosomes are stored in canonical sorted form, their string
     * representation is sufficient as a uniqueness key.</p>
     *
     * @param individuals input list
     * @return deduplicated list preserving first occurrence order
     */
    private List<Individual> deduplicateByChromosome(List<Individual> individuals) {
        List<Individual> unique = new ArrayList<>();
        Set<String> seenKeys = new HashSet<>();

        for (Individual individual : individuals) {
            String key = chromosomeKey(individual);

            if (seenKeys.add(key)) {
                unique.add(individual);
            }
        }

        return unique;
    }

    /**
     * Returns whether a list already contains an individual with the same chromosome.
     *
     * @param individuals individual list
     * @param target individual to check
     * @return {@code true} if an equal chromosome already exists
     */
    private boolean containsSameChromosome(List<Individual> individuals, Individual target) {
        String targetKey = chromosomeKey(target);

        for (Individual individual : individuals) {
            if (chromosomeKey(individual).equals(targetKey)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Builds a stable uniqueness key from the chromosome of an individual.
     *
     * @param individual individual whose chromosome key is needed
     * @return chromosome key
     */
    private String chromosomeKey(Individual individual) {
        return individual.getChromosome().toString();
    }
}
package model;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Represents a solution candidate in the genetic algorithm.
 *
 * <p>The chromosome stores selected candidate point IDs. Since this problem
 * treats a chromosome as an unordered set of selected locker locations,
 * the chromosome is always stored in sorted canonical form. This prevents
 * permutation-equivalent solutions from being treated as different
 * individuals.</p>
 *
 * <p>The individual also keeps both raw and normalized objective values,
 * along with the SPEA2-related attributes used during environmental
 * selection and fitness assignment.</p>
 */
public class Individual {

    private List<Integer> chromosome;

    /**
     * Raw objective value for accessibility (f1).
     */
    private Double objective1;

    /**
     * Raw objective value for equity (f2).
     */
    private Double objective2;

    /**
     * Normalized accessibility objective value.
     */
    private Double normalizedObjective1;

    /**
     * Normalized equity objective value.
     */
    private Double normalizedObjective2;

    /**
     * SPEA2 strength value.
     */
    private int strength;

    /**
     * SPEA2 raw fitness value.
     */
    private int rawFitness;

    /**
     * SPEA2 density value.
     */
    private double density;

    /**
     * Final SPEA2 fitness value.
     */
    private double totalFitness;

    /**
     * Creates an individual with the given chromosome.
     *
     * <p>The chromosome list is copied and sorted to enforce a canonical
     * representation of the solution.</p>
     *
     * @param chromosome selected candidate point IDs that define the individual
     */
    public Individual(List<Integer> chromosome) {
        this.chromosome = canonicalizeChromosome(chromosome);

        this.objective1 = null;
        this.objective2 = null;

        this.normalizedObjective1 = null;
        this.normalizedObjective2 = null;

        this.strength = 0;
        this.rawFitness = 0;
        this.density = 0.0;
        this.totalFitness = 0.0;
    }

    /**
     * Returns the chromosome of this individual.
     *
     * @return selected candidate point IDs in canonical sorted form
     */
    public List<Integer> getChromosome() {
        return chromosome;
    }

    /**
     * Sets the chromosome of this individual.
     *
     * <p>The input list is copied and sorted to enforce a canonical
     * representation of the solution.</p>
     *
     * @param chromosome selected candidate point IDs
     */
    public void setChromosome(List<Integer> chromosome) {
        this.chromosome = canonicalizeChromosome(chromosome);
    }

    /**
     * Returns the raw accessibility objective value.
     *
     * @return accessibility objective value, or {@code null} if not evaluated
     */
    public Double getObjective1() {
        return objective1;
    }

    /**
     * Sets the raw accessibility objective value.
     *
     * @param objective1 accessibility objective value
     */
    public void setObjective1(Double objective1) {
        this.objective1 = objective1;
    }

    /**
     * Returns the raw equity objective value.
     *
     * @return equity objective value, or {@code null} if not evaluated
     */
    public Double getObjective2() {
        return objective2;
    }

    /**
     * Sets the raw equity objective value.
     *
     * @param objective2 equity objective value
     */
    public void setObjective2(Double objective2) {
        this.objective2 = objective2;
    }

    /**
     * Returns the normalized accessibility objective value.
     *
     * @return normalized accessibility objective value, or {@code null} if not normalized
     */
    public Double getNormalizedObjective1() {
        return normalizedObjective1;
    }

    /**
     * Sets the normalized accessibility objective value.
     *
     * @param normalizedObjective1 normalized accessibility objective value
     */
    public void setNormalizedObjective1(Double normalizedObjective1) {
        this.normalizedObjective1 = normalizedObjective1;
    }

    /**
     * Returns the normalized equity objective value.
     *
     * @return normalized equity objective value, or {@code null} if not normalized
     */
    public Double getNormalizedObjective2() {
        return normalizedObjective2;
    }

    /**
     * Sets the normalized equity objective value.
     *
     * @param normalizedObjective2 normalized equity objective value
     */
    public void setNormalizedObjective2(Double normalizedObjective2) {
        this.normalizedObjective2 = normalizedObjective2;
    }

    /**
     * Returns the SPEA2 strength value.
     *
     * @return strength value
     */
    public int getStrength() {
        return strength;
    }

    /**
     * Sets the SPEA2 strength value.
     *
     * @param strength strength value
     */
    public void setStrength(int strength) {
        this.strength = strength;
    }

    /**
     * Returns the SPEA2 raw fitness value.
     *
     * @return raw fitness value
     */
    public int getRawFitness() {
        return rawFitness;
    }

    /**
     * Sets the SPEA2 raw fitness value.
     *
     * @param rawFitness raw fitness value
     */
    public void setRawFitness(int rawFitness) {
        this.rawFitness = rawFitness;
    }

    /**
     * Returns the SPEA2 density value.
     *
     * @return density value
     */
    public double getDensity() {
        return density;
    }

    /**
     * Sets the SPEA2 density value.
     *
     * @param density density value
     */
    public void setDensity(double density) {
        this.density = density;
    }

    /**
     * Returns the final SPEA2 fitness value.
     *
     * @return total fitness value
     */
    public double getTotalFitness() {
        return totalFitness;
    }

    /**
     * Sets the final SPEA2 fitness value.
     *
     * @param totalFitness total fitness value
     */
    public void setTotalFitness(double totalFitness) {
        this.totalFitness = totalFitness;
    }

    /**
     * Converts the chromosome into canonical sorted form.
     *
     * @param chromosome chromosome to canonicalize
     * @return copied and sorted chromosome
     * @throws IllegalArgumentException if the chromosome is {@code null}
     */
    private List<Integer> canonicalizeChromosome(List<Integer> chromosome) {
        if (chromosome == null) {
            throw new IllegalArgumentException("Chromosome cannot be null.");
        }

        List<Integer> canonical = new ArrayList<>(chromosome);
        Collections.sort(canonical);
        return canonical;
    }

    /**
     * Returns a textual representation of the individual and its evaluation fields.
     *
     * @return individual summary
     */
    @Override
    public String toString() {
        return "Individual{" +
                "chromosome=" + chromosome +
                ", objective1=" + objective1 +
                ", objective2=" + objective2 +
                ", normalizedObjective1=" + normalizedObjective1 +
                ", normalizedObjective2=" + normalizedObjective2 +
                ", strength=" + strength +
                ", rawFitness=" + rawFitness +
                ", density=" + density +
                ", totalFitness=" + totalFitness +
                '}';
    }
}
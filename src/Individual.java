import java.util.ArrayList;
import java.util.List;

/**
 * Represents a solution candidate in the genetic algorithm.
 * The chromosome stores selected candidate point IDs, while objective and
 * SPEA2 fitness fields store evaluation results used during optimization.
 */
public class Individual {

    private List<Integer> chromosome;

    // Objective values
    private Double objective1;   // f1: accessibility
    private Double objective2;   // f2: equity

    // SPEA2 attributes
    private int strength;
    private int rawFitness;
    private double density;
    private double totalFitness;

    /**
     * Creates an individual with the given chromosome.
     * The chromosome list is copied to protect the internal representation from
     * external list reference changes.
     *
     * @param chromosome selected candidate point IDs that define the individual
     */
    public Individual(List<Integer> chromosome) {
        this.chromosome = new ArrayList<>(chromosome);

        this.objective1 = null;
        this.objective2 = null;

        this.strength = 0;
        this.rawFitness = 0;
        this.density = 0.0;
        this.totalFitness = 0.0;
    }

    /**
     * Returns the chromosome of this individual.
     *
     * @return selected candidate point IDs
     */
    public List<Integer> getChromosome() {
        return chromosome;
    }

    /**
     * Sets the chromosome of this individual.
     * The input list is copied to protect the internal representation from
     * external list reference changes.
     *
     * @param chromosome selected candidate point IDs
     */
    public void setChromosome(List<Integer> chromosome) {
        this.chromosome = new ArrayList<>(chromosome);
    }

    /**
     * Returns the first objective value, representing accessibility.
     *
     * @return accessibility objective value, or null if it has not been evaluated
     */
    public Double getObjective1() {
        return objective1;
    }

    /**
     * Sets the first objective value, representing accessibility.
     *
     * @param objective1 accessibility objective value
     */
    public void setObjective1(Double objective1) {
        this.objective1 = objective1;
    }

    /**
     * Returns the second objective value, representing equity.
     *
     * @return equity objective value, or null if it has not been evaluated
     */
    public Double getObjective2() {
        return objective2;
    }

    /**
     * Sets the second objective value, representing equity.
     *
     * @param objective2 equity objective value
     */
    public void setObjective2(Double objective2) {
        this.objective2 = objective2;
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
     * Returns the total SPEA2 fitness value.
     *
     * @return total fitness value
     */
    public double getTotalFitness() {
        return totalFitness;
    }

    /**
     * Sets the total SPEA2 fitness value.
     *
     * @param totalFitness total fitness value
     */
    public void setTotalFitness(double totalFitness) {
        this.totalFitness = totalFitness;
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
                ", strength=" + strength +
                ", rawFitness=" + rawFitness +
                ", density=" + density +
                ", totalFitness=" + totalFitness +
                '}';
    }
}

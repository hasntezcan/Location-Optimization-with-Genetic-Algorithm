import java.util.ArrayList;
import java.util.List;

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

    public Individual(List<Integer> chromosome) {
        this.chromosome = new ArrayList<>(chromosome);

        this.objective1 = null;
        this.objective2 = null;

        this.strength = 0;
        this.rawFitness = 0;
        this.density = 0.0;
        this.totalFitness = 0.0;
    }

    public List<Integer> getChromosome() {
        return chromosome;
    }

    public void setChromosome(List<Integer> chromosome) {
        this.chromosome = new ArrayList<>(chromosome);
    }

    public Double getObjective1() {
        return objective1;
    }

    public void setObjective1(Double objective1) {
        this.objective1 = objective1;
    }

    public Double getObjective2() {
        return objective2;
    }

    public void setObjective2(Double objective2) {
        this.objective2 = objective2;
    }

    public int getStrength() {
        return strength;
    }

    public void setStrength(int strength) {
        this.strength = strength;
    }

    public int getRawFitness() {
        return rawFitness;
    }

    public void setRawFitness(int rawFitness) {
        this.rawFitness = rawFitness;
    }

    public double getDensity() {
        return density;
    }

    public void setDensity(double density) {
        this.density = density;
    }

    public double getTotalFitness() {
        return totalFitness;
    }

    public void setTotalFitness(double totalFitness) {
        this.totalFitness = totalFitness;
    }

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
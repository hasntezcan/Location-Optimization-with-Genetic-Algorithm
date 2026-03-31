import java.util.ArrayList;
import java.util.List;

public class Individual {

    private List<Integer> chromosome;
    private Double fitness;

    public Individual(List<Integer> chromosome) {
        this.chromosome = new ArrayList<>(chromosome);
        this.fitness = null;
    }

    public List<Integer> getChromosome() {
        return chromosome;
    }

    public void setChromosome(List<Integer> chromosome) {
        this.chromosome = new ArrayList<>(chromosome);
    }

    public Double getFitness() {
        return fitness;
    }

    public void setFitness(Double fitness) {
        this.fitness = fitness;
    }

    @Override
    public String toString() {
        return "Individual{" +
                "chromosome=" + chromosome +
                ", fitness=" + fitness +
                '}';
    }
}
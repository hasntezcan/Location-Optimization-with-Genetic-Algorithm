import java.util.List;

public class FitnessCalculator {

    private double[][] distanceMatrix;
    private CandidateRepository repository;
    private double totalSystemDemand;
    private double beta;

    public FitnessCalculator(double[][] distanceMatrix, CandidateRepository repository, double beta) {
        this.distanceMatrix = distanceMatrix;
        this.repository = repository;
        this.beta = beta;
        this.totalSystemDemand = calculateTotalDemand();
    }

    private double calculateTotalDemand() {
        return repository.getAllCandidatesSorted().stream()
                .mapToDouble(CandidatePoint::getDemandScore)
                .sum();
    }

    // f1: Accessibility (minimize)
    public void evaluateF1(Individual individual) {
        double weightedDistanceSum = 0.0;
        List<CandidatePoint> allGrids = repository.getAllCandidatesSorted();
        List<Integer> lockerIds = individual.getChromosome();

        for (CandidatePoint grid : allGrids) {
            int gridIndex = repository.getIndexById(grid.getId());
            double minDistance = Double.MAX_VALUE;

            for (int lockerId : lockerIds) {
                int lockerIndex = repository.getIndexById(lockerId);
                double currentDistance = distanceMatrix[gridIndex][lockerIndex];

                if (currentDistance < minDistance) {
                    minDistance = currentDistance;
                }
            }

            double distanceCost = Math.pow(minDistance, beta);
            weightedDistanceSum += grid.getDemandScore() * distanceCost;
        }

        double f1Score = weightedDistanceSum / totalSystemDemand;
        individual.setObjective1(f1Score);
    }

    // f2: Equity (minimize)
    public void evaluateF2(Individual individual) {
        // sonraki adımda dolduracağız
    }
}
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class FitnessCalculator {

    private double[][] decayMatrix; // Önceden sönümlenmiş mesafe değerleri
    private CandidateRepository repository;
    private double totalSystemDemand; // Tüm Kadıköy'ün toplam demandScore'u

    public FitnessCalculator(double[][] decayMatrix, CandidateRepository repository) {
        this.decayMatrix = decayMatrix;
        this.repository = repository;
        this.totalSystemDemand = calculateTotalDemand();
    }

    private double calculateTotalDemand() {
        return repository.getAllCandidatesSorted().stream()
                .mapToDouble(CandidatePoint::getDemandScore)
                .sum();
    }

    // f1: Erişilebilirlik (Minimize edilecek)
    public void evaluateF1(Individual individual) {
        double weightedDistanceSum = 0.0;
        List<CandidatePoint> allGrids = repository.getAllCandidatesSorted();
        List<Integer> lockerIds = individual.getChromosome();

        // Her bir grid için en yakın seçili dolabı bul
        for (CandidatePoint grid : allGrids) {
            int gridIndex = repository.getIndexById(grid.getId());
            double minDecayValue = Double.MAX_VALUE;

            for (int lockerId : lockerIds) {
                int lockerIndex = repository.getIndexById(lockerId);
                // Matristen hazır sönümlenmiş mesafe/etki değerini çekiyoruz
                double currentDecay = decayMatrix[gridIndex][lockerIndex]; 
                if (currentDecay < minDecayValue) {
                    minDecayValue = currentDecay;
                }
            }

            // Gridin talebi ile en kısa (veya en etkili) mesafeyi çarp
            weightedDistanceSum += (grid.getDemandScore() * minDecayValue);
        }

        double f1Score = weightedDistanceSum / totalSystemDemand;
        // Individual nesnesine fitness değerini ata (bunun için Individual sınıfına f1 ve f2 field'ları eklemelisin)
        // individual.setF1(f1Score); 
    }

    // f2: Eşitsizlik (Minimize edilecek)
    public void evaluateF2(Individual individual) {
        // 1. Her mahalle için f1 mantığıyla mahalle içi ağırlıklı ortalamayı bul
        // 2. Çıkan mahalle ortalamalarının varyansını hesapla
        // 3. individual.setF2(varianceScore);
    }
}
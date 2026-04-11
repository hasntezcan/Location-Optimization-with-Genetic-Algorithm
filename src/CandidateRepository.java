import java.util.*;

public class CandidateRepository {
    // 1. For direct access via ID (Fast lookup)
    private final Map<Integer, CandidatePoint> candidateMap = new HashMap<>();
    
    // 2. Map ID to matrix index (Crucial for GA performance during fitness evaluation)
    private final Map<Integer, Integer> idToIndexMap = new HashMap<>();
    
    // 3. Map matrix index to object (Maintains identical order with the Python distance matrix)
    private List<CandidatePoint> sortedCandidates = new ArrayList<>();

    public void addCandidate(CandidatePoint candidate) {
        candidateMap.put(candidate.getId(), candidate);
    }

    /**
     * This method must be called exactly once after the data loading process is complete.
     * It synchronizes the Java objects with the Python-generated distance matrix indexing.
     */
    public void finalizeRepository() {
        // Populate the list and sort by ID ascending (Matches Python's sorting logic)
        this.sortedCandidates = new ArrayList<>(candidateMap.values());
        this.sortedCandidates.sort(Comparator.comparingInt(CandidatePoint::getId));

        // Establish the ID -> Index mapping for O(1) translation
        for (int i = 0; i < sortedCandidates.size(); i++) {
            idToIndexMap.put(sortedCandidates.get(i).getId(), i);
        }
        
        System.out.println("Repository finalized and synchronized with distance matrix. Total points: " + sortedCandidates.size());
    }

    /**
     * Retrieves the candidate point corresponding to a specific index in the distance matrix.
     * Use this during GA fitness calculations.
     */
    public CandidatePoint getCandidateByIndex(int index) {
        return sortedCandidates.get(index);
    }

    /**
     * Finds the matrix row/column index associated with a specific candidate ID.
     */
    public int getIndexById(int id) {
        return idToIndexMap.getOrDefault(id, -1);
    }

    /**
     * Returns a sorted list of all unique candidate IDs.
     * Sorting ensures deterministic behavior during population initialization.
     */
    public List<Integer> getAllCandidateIds() {
        List<Integer> ids = new ArrayList<>(candidateMap.keySet());
        Collections.sort(ids);
        return ids;
    }

    public List<CandidatePoint> getAllCandidatesSorted() {
        return sortedCandidates;
    }

    public int size() {
        return sortedCandidates.size();
    }

    @Override
    public String toString() {
        return "CandidateRepository{candidateCount=" + candidateMap.size() + "}";
    }
}
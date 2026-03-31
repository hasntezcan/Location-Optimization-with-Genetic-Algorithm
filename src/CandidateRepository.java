import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class CandidateRepository {

    private Map<Integer, CandidatePoint> candidateMap;

    public CandidateRepository() {
        this.candidateMap = new HashMap<>();
    }

    public void addCandidate(CandidatePoint candidate) {
        candidateMap.put(candidate.getId(), candidate);
    }

    public CandidatePoint getCandidateById(int id) {
        return candidateMap.get(id);
    }

    public boolean containsId(int id) {
        return candidateMap.containsKey(id);
    }

    public int size() {
        return candidateMap.size();
    }

    public List<Integer> getAllCandidateIds() {
        return new ArrayList<>(candidateMap.keySet());
    }

    public List<CandidatePoint> getAllCandidates() {
        return new ArrayList<>(candidateMap.values());
    }

    @Override
    public String toString() {
        return "CandidateRepository{" +
                "candidateCount=" + candidateMap.size() +
                '}';
    }
}
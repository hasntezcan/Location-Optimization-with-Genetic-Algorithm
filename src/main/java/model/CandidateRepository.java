package model;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Stores candidate points and provides efficient access by candidate ID
 * and by distance-matrix index.
 *
 * <p>The repository keeps a direct ID lookup map and also maintains a
 * deterministic candidate ordering that matches the Python-generated
 * distance matrix indexing.</p>
 */
public class CandidateRepository {

    /**
     * Direct access map by candidate ID.
     */
    private final Map<Integer, CandidatePoint> candidateMap = new HashMap<>();

    /**
     * Maps candidate ID to its distance-matrix index.
     */
    private final Map<Integer, Integer> idToIndexMap = new HashMap<>();

    /**
     * Candidates sorted by ID in the same order as the Python distance matrix.
     */
    private List<CandidatePoint> sortedCandidates = new ArrayList<>();

    /**
     * Adds a candidate point to the repository.
     *
     * @param candidate candidate point to add
     */
    public void addCandidate(CandidatePoint candidate) {
        candidateMap.put(candidate.getId(), candidate);
    }

    /**
     * Finalizes the repository after all candidate points have been loaded.
     *
     * <p>This method sorts all candidates by ascending ID and builds the
     * ID-to-index mapping required for consistent access to the distance matrix.
     * It must be called after loading is complete and before fitness evaluation
     * begins.</p>
     *
     * @throws IllegalStateException if no candidate points have been loaded
     */
    public void finalizeRepository() {
        if (candidateMap.isEmpty()) {
            throw new IllegalStateException("Cannot finalize repository: no candidates loaded.");
        }

        this.sortedCandidates = new ArrayList<>(candidateMap.values());
        this.sortedCandidates.sort(Comparator.comparingInt(CandidatePoint::getId));

        idToIndexMap.clear();
        for (int i = 0; i < sortedCandidates.size(); i++) {
            idToIndexMap.put(sortedCandidates.get(i).getId(), i);
        }

        System.out.println(
                "Repository finalized and synchronized with distance matrix. Total points: "
                        + sortedCandidates.size()
        );
    }

    /**
     * Returns the candidate point at the given distance-matrix index.
     *
     * @param index distance-matrix index
     * @return candidate point at the given index
     */
    public CandidatePoint getCandidateByIndex(int index) {
        return sortedCandidates.get(index);
    }

    /**
     * Returns the candidate point for the given candidate ID.
     *
     * @param id candidate ID
     * @return candidate point, or {@code null} if not found
     */
    public CandidatePoint getCandidateById(int id) {
        return candidateMap.get(id);
    }

    /**
     * Checks whether a candidate ID exists in the repository.
     *
     * @param id candidate ID
     * @return true if the repository contains the ID
     */
    public boolean containsId(int id) {
        return candidateMap.containsKey(id);
    }

    /**
     * Returns the distance-matrix index associated with the given candidate ID.
     *
     * @param id candidate ID
     * @return matrix index of the candidate, or {@code -1} if not found
     */
    public int getIndexById(int id) {
        return idToIndexMap.getOrDefault(id, -1);
    }

    /**
     * Returns all candidate IDs in ascending order.
     *
     * <p>This ordering is deterministic and suitable for population initialization.</p>
     *
     * @return sorted candidate ID list
     */
    public List<Integer> getAllCandidateIds() {
        List<Integer> ids = new ArrayList<>(candidateMap.keySet());
        Collections.sort(ids);
        return ids;
    }

    /**
     * Returns candidate IDs that are allowed to be selected as locker locations.
     *
     * <p>Forbidden candidates remain in the repository because they are still
     * demand grid points and must stay aligned with the distance matrix. This
     * method is only for the GA selection universe.</p>
     *
     * @return sorted candidate IDs where {@code isForbidden == false}
     */
    public List<Integer> getSelectableCandidateIds() {
        List<CandidatePoint> source = sortedCandidates.isEmpty()
                ? new ArrayList<>(candidateMap.values())
                : sortedCandidates;

        List<Integer> ids = new ArrayList<>();
        for (CandidatePoint candidate : source) {
            if (!candidate.isForbidden()) {
                ids.add(candidate.getId());
            }
        }

        Collections.sort(ids);
        return ids;
    }

    /**
     * Returns candidate IDs with one or more mapped physical existing lockers.
     *
     * <p>This uses only {@code existing_locker_count}; the 300m proximity field
     * {@code nearby_locker_count} is context data and is never a fixed-facility
     * source.</p>
     *
     * @return sorted candidate IDs where {@code existingLockerCount > 0}
     */
    public List<Integer> getCandidateIdsWithExistingLockers() {
        List<CandidatePoint> source = sortedCandidates.isEmpty()
                ? new ArrayList<>(candidateMap.values())
                : sortedCandidates;

        List<Integer> ids = new ArrayList<>();
        for (CandidatePoint candidate : source) {
            if (candidate.getExistingLockerCount() > 0) {
                ids.add(candidate.getId());
            }
        }

        Collections.sort(ids);
        return ids;
    }

    /**
     * Returns the total number of mapped physical existing lockers.
     *
     * @return sum of {@code existing_locker_count} across all candidates
     */
    public int getExistingPhysicalLockerCount() {
        List<CandidatePoint> source = sortedCandidates.isEmpty()
                ? new ArrayList<>(candidateMap.values())
                : sortedCandidates;
        return source.stream().mapToInt(CandidatePoint::getExistingLockerCount).sum();
    }

    /**
     * Returns candidate IDs influenced by an existing locker within 300m.
     * This contextual set must not be used as fixed facilities.
     *
     * @return sorted candidate IDs where {@code nearbyLockerCount > 0}
     */
    public List<Integer> getCandidateIdsWithNearbyLockerInfluence() {
        List<CandidatePoint> source = sortedCandidates.isEmpty()
                ? new ArrayList<>(candidateMap.values())
                : sortedCandidates;
        List<Integer> ids = new ArrayList<>();
        for (CandidatePoint candidate : source) {
            if (candidate.getNearbyLockerCount() > 0) {
                ids.add(candidate.getId());
            }
        }
        Collections.sort(ids);
        return ids;
    }

    /**
     * Returns all candidates in the repository sorted by ascending ID.
     *
     * @return sorted candidate list
     */
    public List<CandidatePoint> getAllCandidatesSorted() {
        return sortedCandidates;
    }

    /**
     * Returns the number of candidates stored in the repository.
     *
     * @return candidate count
     */
    public int size() {
        return candidateMap.size();
    }

    /**
     * Returns a short textual representation of the repository.
     *
     * @return repository summary
     */
    @Override
    public String toString() {
        return "CandidateRepository{candidateCount=" + candidateMap.size() + "}";
    }
}

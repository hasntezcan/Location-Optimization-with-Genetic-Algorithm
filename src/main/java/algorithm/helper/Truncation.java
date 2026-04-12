package algorithm.helper;

import model.Individual;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Applies SPEA2 truncation to an oversized archive.
 *
 * <p>When the archive contains more individuals than allowed, this helper
 * removes individuals from the most crowded regions of the normalized
 * objective space. The crowding comparison follows the SPEA2 truncation idea:
 * sorted neighbor-distance lists are compared lexicographically, and the
 * individual located in the densest region is removed first.</p>
 */
public class Truncation {

    /**
     * Reduces the given archive to the requested target size.
     *
     * <p>The returned list is a new list. The original archive list is not
     * modified.</p>
     *
     * @param archive archive to truncate
     * @param targetSize desired final archive size
     * @return truncated archive
     * @throws IllegalArgumentException if the archive is {@code null}
     *                                  or if {@code targetSize} is negative
     */
    public List<Individual> run(List<Individual> archive, int targetSize) {
        if (archive == null) {
            throw new IllegalArgumentException("Archive cannot be null.");
        }

        if (targetSize < 0) {
            throw new IllegalArgumentException("Target size cannot be negative.");
        }

        List<Individual> working = new ArrayList<>(archive);

        while (working.size() > targetSize) {
            int removeIndex = findMostCrowdedIndividualIndex(working);
            working.remove(removeIndex);
        }

        return working;
    }

    /**
     * Finds the index of the individual located in the most crowded region
     * of the normalized objective space.
     *
     * @param archive working archive
     * @return index of the individual to remove
     */
    private int findMostCrowdedIndividualIndex(List<Individual> archive) {
        int selectedIndex = -1;
        List<Double> selectedDistances = null;

        for (int i = 0; i < archive.size(); i++) {
            List<Double> distances = buildSortedDistanceList(archive, i);

            if (selectedIndex == -1) {
                selectedIndex = i;
                selectedDistances = distances;
                continue;
            }

            if (isLexicographicallySmaller(distances, selectedDistances)) {
                selectedIndex = i;
                selectedDistances = distances;
            }
        }

        return selectedIndex;
    }

    /**
     * Builds the sorted list of normalized objective-space distances from the
     * given individual to all other individuals in the archive.
     *
     * @param archive archive list
     * @param index index of the reference individual
     * @return ascending sorted distance list
     * @throws IllegalStateException if normalized objective values are missing
     */
    private List<Double> buildSortedDistanceList(List<Individual> archive, int index) {
        Individual reference = archive.get(index);
        List<Double> distances = new ArrayList<>();

        for (int i = 0; i < archive.size(); i++) {
            if (i == index) {
                continue;
            }

            distances.add(distanceInNormalizedObjectiveSpace(reference, archive.get(i)));
        }

        Collections.sort(distances);
        return distances;
    }

    /**
     * Compares two sorted distance lists lexicographically.
     *
     * <p>The list with the smaller first differing distance is considered more
     * crowded and therefore lexicographically smaller.</p>
     *
     * @param first first sorted distance list
     * @param second second sorted distance list
     * @return {@code true} if the first list is lexicographically smaller;
     *         {@code false} otherwise
     */
    private boolean isLexicographicallySmaller(List<Double> first, List<Double> second) {
        int limit = Math.min(first.size(), second.size());

        for (int i = 0; i < limit; i++) {
            double a = first.get(i);
            double b = second.get(i);

            if (a < b) {
                return true;
            }

            if (a > b) {
                return false;
            }
        }

        return first.size() < second.size();
    }

    /**
     * Computes the Euclidean distance between two individuals in the normalized
     * objective space.
     *
     * @param a first individual
     * @param b second individual
     * @return normalized objective-space distance
     * @throws IllegalStateException if normalized objective values are missing
     */
    private double distanceInNormalizedObjectiveSpace(Individual a, Individual b) {
        if (a.getNormalizedObjective1() == null || a.getNormalizedObjective2() == null) {
            throw new IllegalStateException("Normalized objectives are missing for the first individual.");
        }

        if (b.getNormalizedObjective1() == null || b.getNormalizedObjective2() == null) {
            throw new IllegalStateException("Normalized objectives are missing for the second individual.");
        }

        double dx = a.getNormalizedObjective1() - b.getNormalizedObjective1();
        double dy = a.getNormalizedObjective2() - b.getNormalizedObjective2();

        return Math.sqrt(dx * dx + dy * dy);
    }
}
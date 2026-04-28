package config;

/**
 * Configuration parameters for the genetic algorithm.
 *
 * <p>
 * This class stores all configurable constants used by the SPEA2
 * optimization pipeline. Keeping them in a single location makes it
 * easy to adjust experiment settings without modifying algorithm or
 * orchestration logic.
 * </p>
 */
public class GAParameters {

    /**
     * Number of locker locations selected per chromosome.
     */
    public static final int K = 5;

    /**
     * Number of individuals in the main population.
     */
    public static final int POPULATION_SIZE = 100;

    /**
     * Maximum number of individuals kept in the SPEA2 archive.
     */
    public static final int ARCHIVE_SIZE = 50;

    /**
     * Number of evolutionary generations to run.
     */
    public static final int MAX_GENERATIONS = 200;

    /**
     * Distance-decay exponent used in the accessibility objective.
     */
    public static final double BETA = 2.0;

    /**
     * Probability of applying crossover to a pair of parents.
     */
    public static final double CROSSOVER_RATE = 0.9;

    /**
     * Probability of applying mutation to a child chromosome.
     */
    public static final double MUTATION_RATE = 0.1;

    public static final double ASSESSMENT_IDEAL_F1 = 0.93;
    public static final double ASSESSMENT_IDEAL_F2 = 0.40;

    public static final double ASSESSMENT_NADIR_F1 = 1.27;
    public static final double ASSESSMENT_NADIR_F2 = 0.58;

    public static final double REFERENCE_POINT_F1 = 1.1;
    public static final double REFERENCE_POINT_F2 = 1.1;

    private GAParameters() {
        // Utility class — prevent instantiation.
    }
}

package model;

/**
 * Represents one candidate grid point and demand source.
 *
 * <p>Rows with {@code isForbidden == false} may be selected as locker
 * locations. Forbidden rows still remain in the model as demand grid points so
 * the candidate CSV stays aligned with the precomputed distance matrix.</p>
 */
public class CandidatePoint {

    private int id;

    private String mahalleNameTurkish;
    private String mahalleNameEnglish;

    private int mahallePopulation;

    private int poiAtm;
    private int poiBank;
    private int poiHospital;
    private int poiSchool;
    private int poiUniversity;
    private int poiPostOffice;
    private int poiTransport;
    private int poiBusStop;

    private double lon;
    private double lat;

    private boolean isForbidden;
    private int nearbyLockerCount;
    private int existingLockerCount;

    private int gridCountByMahalle;
    private double population;
    private double poiScore;
    private double demandScore;

    /**
     * Creates an empty candidate point.
     */
    public CandidatePoint() {
    }

    /**
     * Creates a candidate point with all input data required by the optimization model.
     *
     * @param id unique candidate point identifier
     * @param mahalleNameTurkish neighborhood name in Turkish
     * @param mahalleNameEnglish neighborhood name in English
     * @param mahallePopulation total population of the neighborhood
     * @param poiAtm number of nearby ATMs
     * @param poiBank number of nearby banks
     * @param poiHospital number of nearby hospitals
     * @param poiSchool number of nearby schools
     * @param poiUniversity number of nearby universities
     * @param poiPostOffice number of nearby post offices
     * @param poiTransport number of nearby transport points
     * @param poiBusStop number of nearby bus stops
     * @param lon longitude coordinate of the candidate point
     * @param lat latitude coordinate of the candidate point
     * @param isForbidden whether the candidate point is forbidden for locker placement
     * @param nearbyLockerCount number of existing lockers in the candidate's 300m neighborhood
     * @param existingLockerCount number of physical existing lockers mapped to this candidate
     * @param gridCountByMahalle number of grid points in the same neighborhood
     * @param population estimated population assigned to the candidate point
     * @param poiScore point-of-interest score of the candidate point
     * @param demandScore final demand score of the candidate point
     */
    public CandidatePoint(int id,
                          String mahalleNameTurkish,
                          String mahalleNameEnglish,
                          int mahallePopulation,
                          int poiAtm,
                          int poiBank,
                          int poiHospital,
                          int poiSchool,
                          int poiUniversity,
                          int poiPostOffice,
                          int poiTransport,
                          int poiBusStop,
                          double lon,
                          double lat,
                          boolean isForbidden,
                          int nearbyLockerCount,
                          int existingLockerCount,
                          int gridCountByMahalle,
                          double population,
                          double poiScore,
                          double demandScore) {
        this.id = id;
        this.mahalleNameTurkish = mahalleNameTurkish;
        this.mahalleNameEnglish = mahalleNameEnglish;
        this.mahallePopulation = mahallePopulation;
        this.poiAtm = poiAtm;
        this.poiBank = poiBank;
        this.poiHospital = poiHospital;
        this.poiSchool = poiSchool;
        this.poiUniversity = poiUniversity;
        this.poiPostOffice = poiPostOffice;
        this.poiTransport = poiTransport;
        this.poiBusStop = poiBusStop;
        this.lon = lon;
        this.lat = lat;
        this.isForbidden = isForbidden;
        this.nearbyLockerCount = nearbyLockerCount;
        this.existingLockerCount = existingLockerCount;
        this.gridCountByMahalle = gridCountByMahalle;
        this.population = population;
        this.poiScore = poiScore;
        this.demandScore = demandScore;
    }

    /**
     * Returns the unique candidate point identifier.
     *
     * @return candidate point id
     */
    public int getId() {
        return id;
    }

    /**
     * Sets the unique candidate point identifier.
     *
     * @param id candidate point id
     */
    public void setId(int id) {
        this.id = id;
    }

    /**
     * Returns the Turkish neighborhood name.
     *
     * @return Turkish neighborhood name
     */
    public String getMahalleNameTurkish() {
        return mahalleNameTurkish;
    }

    /**
     * Sets the Turkish neighborhood name.
     *
     * @param mahalleNameTurkish Turkish neighborhood name
     */
    public void setMahalleNameTurkish(String mahalleNameTurkish) {
        this.mahalleNameTurkish = mahalleNameTurkish;
    }

    /**
     * Returns the English neighborhood name.
     *
     * @return English neighborhood name
     */
    public String getMahalleNameEnglish() {
        return mahalleNameEnglish;
    }

    /**
     * Sets the English neighborhood name.
     *
     * @param mahalleNameEnglish English neighborhood name
     */
    public void setMahalleNameEnglish(String mahalleNameEnglish) {
        this.mahalleNameEnglish = mahalleNameEnglish;
    }

    /**
     * Returns the total population of the neighborhood.
     *
     * @return neighborhood population
     */
    public int getMahallePopulation() {
        return mahallePopulation;
    }

    /**
     * Sets the total population of the neighborhood.
     *
     * @param mahallePopulation neighborhood population
     */
    public void setMahallePopulation(int mahallePopulation) {
        this.mahallePopulation = mahallePopulation;
    }

    /**
     * Returns the number of nearby ATMs.
     *
     * @return ATM count
     */
    public int getPoiAtm() {
        return poiAtm;
    }

    /**
     * Sets the number of nearby ATMs.
     *
     * @param poiAtm ATM count
     */
    public void setPoiAtm(int poiAtm) {
        this.poiAtm = poiAtm;
    }

    /**
     * Returns the number of nearby banks.
     *
     * @return bank count
     */
    public int getPoiBank() {
        return poiBank;
    }

    /**
     * Sets the number of nearby banks.
     *
     * @param poiBank bank count
     */
    public void setPoiBank(int poiBank) {
        this.poiBank = poiBank;
    }

    /**
     * Returns the number of nearby hospitals.
     *
     * @return hospital count
     */
    public int getPoiHospital() {
        return poiHospital;
    }

    /**
     * Sets the number of nearby hospitals.
     *
     * @param poiHospital hospital count
     */
    public void setPoiHospital(int poiHospital) {
        this.poiHospital = poiHospital;
    }

    /**
     * Returns the number of nearby schools.
     *
     * @return school count
     */
    public int getPoiSchool() {
        return poiSchool;
    }

    /**
     * Sets the number of nearby schools.
     *
     * @param poiSchool school count
     */
    public void setPoiSchool(int poiSchool) {
        this.poiSchool = poiSchool;
    }

    /**
     * Returns the number of nearby universities.
     *
     * @return university count
     */
    public int getPoiUniversity() {
        return poiUniversity;
    }

    /**
     * Sets the number of nearby universities.
     *
     * @param poiUniversity university count
     */
    public void setPoiUniversity(int poiUniversity) {
        this.poiUniversity = poiUniversity;
    }

    /**
     * Returns the number of nearby post offices.
     *
     * @return post office count
     */
    public int getPoiPostOffice() {
        return poiPostOffice;
    }

    /**
     * Sets the number of nearby post offices.
     *
     * @param poiPostOffice post office count
     */
    public void setPoiPostOffice(int poiPostOffice) {
        this.poiPostOffice = poiPostOffice;
    }

    /**
     * Returns the number of nearby transport points.
     *
     * @return transport point count
     */
    public int getPoiTransport() {
        return poiTransport;
    }

    /**
     * Sets the number of nearby transport points.
     *
     * @param poiTransport transport point count
     */
    public void setPoiTransport(int poiTransport) {
        this.poiTransport = poiTransport;
    }

    /**
     * Returns the number of nearby bus stops.
     *
     * @return bus stop count
     */
    public int getPoiBusStop() {
        return poiBusStop;
    }

    /**
     * Sets the number of nearby bus stops.
     *
     * @param poiBusStop bus stop count
     */
    public void setPoiBusStop(int poiBusStop) {
        this.poiBusStop = poiBusStop;
    }

    /**
     * Returns the longitude coordinate of the candidate point.
     *
     * @return longitude coordinate
     */
    public double getLon() {
        return lon;
    }

    /**
     * Sets the longitude coordinate of the candidate point.
     *
     * @param lon longitude coordinate
     */
    public void setLon(double lon) {
        this.lon = lon;
    }

    /**
     * Returns the latitude coordinate of the candidate point.
     *
     * @return latitude coordinate
     */
    public double getLat() {
        return lat;
    }

    /**
     * Sets the latitude coordinate of the candidate point.
     *
     * @param lat latitude coordinate
     */
    public void setLat(double lat) {
        this.lat = lat;
    }

    /**
     * Returns whether the candidate point is forbidden for locker placement.
     *
     * @return true if the candidate point is forbidden; false otherwise
     */
    public boolean isForbidden() {
        return isForbidden;
    }

    /**
     * Sets whether the candidate point is forbidden for locker placement.
     *
     * @param forbidden true if the candidate point is forbidden; false otherwise
     */
    public void setForbidden(boolean forbidden) {
        isForbidden = forbidden;
    }

    /**
     * Returns the number of existing lockers in the candidate's 300m neighborhood.
     *
     * @return locker count
     */
    public int getNearbyLockerCount() {
        return nearbyLockerCount;
    }

    /**
     * Sets the number of existing lockers in the candidate's 300m neighborhood.
     *
     * @param nearbyLockerCount nearby locker count
     */
    public void setNearbyLockerCount(int nearbyLockerCount) {
        this.nearbyLockerCount = nearbyLockerCount;
    }

    /**
     * Returns the number of physical existing lockers mapped to this candidate.
     *
     * @return physical existing locker count
     */
    public int getExistingLockerCount() {
        return existingLockerCount;
    }

    /**
     * Sets the number of physical existing lockers mapped to this candidate.
     *
     * @param existingLockerCount physical existing locker count
     */
    public void setExistingLockerCount(int existingLockerCount) {
        this.existingLockerCount = existingLockerCount;
    }

    /**
     * Backward-compatible alias for the old proximity-count accessor.
     *
     * @return nearby locker count
     * @deprecated use {@link #getNearbyLockerCount()}
     */
    @Deprecated
    public int getLockerCount() {
        return getNearbyLockerCount();
    }

    /**
     * Backward-compatible alias for the old proximity-count mutator.
     *
     * @param lockerCount nearby locker count
     * @deprecated use {@link #setNearbyLockerCount(int)}
     */
    @Deprecated
    public void setLockerCount(int lockerCount) {
        setNearbyLockerCount(lockerCount);
    }

    /**
     * Returns the number of grid points in the same neighborhood.
     *
     * @return grid point count by neighborhood
     */
    public int getGridCountByMahalle() {
        return gridCountByMahalle;
    }

    /**
     * Sets the number of grid points in the same neighborhood.
     *
     * @param gridCountByMahalle grid point count by neighborhood
     */
    public void setGridCountByMahalle(int gridCountByMahalle) {
        this.gridCountByMahalle = gridCountByMahalle;
    }

    /**
     * Returns the estimated population assigned to the candidate point.
     *
     * @return candidate point population
     */
    public double getPopulation() {
        return population;
    }

    /**
     * Sets the estimated population assigned to the candidate point.
     *
     * @param population candidate point population
     */
    public void setPopulation(double population) {
        this.population = population;
    }

    /**
     * Returns the point-of-interest score of the candidate point.
     *
     * @return point-of-interest score
     */
    public double getPoiScore() {
        return poiScore;
    }

    /**
     * Sets the point-of-interest score of the candidate point.
     *
     * @param poiScore point-of-interest score
     */
    public void setPoiScore(double poiScore) {
        this.poiScore = poiScore;
    }

    /**
     * Returns the final demand score of the candidate point.
     *
     * @return demand score
     */
    public double getDemandScore() {
        return demandScore;
    }

    /**
     * Sets the final demand score of the candidate point.
     *
     * @param demandScore demand score
     */
    public void setDemandScore(double demandScore) {
        this.demandScore = demandScore;
    }

    /**
     * Returns a short textual representation of the candidate point.
     *
     * @return candidate point summary
     */
    @Override
    public String toString() {
        return "CandidatePoint{" +
                "id=" + id +
                ", mahalleNameTurkish='" + mahalleNameTurkish + '\'' +
                ", population=" + population +
                ", poiScore=" + poiScore +
                ", demandScore=" + demandScore +
                '}';
    }
}

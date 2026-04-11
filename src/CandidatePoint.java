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
    private int lockerCount;

    private int gridCountByMahalle;
    private double population;
    private double demandScore;

    public CandidatePoint() {
    }

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
                          int lockerCount,
                          int gridCountByMahalle,
                          double population,
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
        this.lockerCount = lockerCount;
        this.gridCountByMahalle = gridCountByMahalle;
        this.population = population;
        this.demandScore = demandScore;
    }

    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public String getMahalleNameTurkish() {
        return mahalleNameTurkish;
    }

    public void setMahalleNameTurkish(String mahalleNameTurkish) {
        this.mahalleNameTurkish = mahalleNameTurkish;
    }

    public String getMahalleNameEnglish() {
        return mahalleNameEnglish;
    }

    public void setMahalleNameEnglish(String mahalleNameEnglish) {
        this.mahalleNameEnglish = mahalleNameEnglish;
    }

    public int getMahallePopulation() {
        return mahallePopulation;
    }

    public void setMahallePopulation(int mahallePopulation) {
        this.mahallePopulation = mahallePopulation;
    }

    public int getPoiAtm() {
        return poiAtm;
    }

    public void setPoiAtm(int poiAtm) {
        this.poiAtm = poiAtm;
    }

    public int getPoiBank() {
        return poiBank;
    }

    public void setPoiBank(int poiBank) {
        this.poiBank = poiBank;
    }

    public int getPoiHospital() {
        return poiHospital;
    }

    public void setPoiHospital(int poiHospital) {
        this.poiHospital = poiHospital;
    }

    public int getPoiSchool() {
        return poiSchool;
    }

    public void setPoiSchool(int poiSchool) {
        this.poiSchool = poiSchool;
    }

    public int getPoiUniversity() {
        return poiUniversity;
    }

    public void setPoiUniversity(int poiUniversity) {
        this.poiUniversity = poiUniversity;
    }

    public int getPoiPostOffice() {
        return poiPostOffice;
    }

    public void setPoiPostOffice(int poiPostOffice) {
        this.poiPostOffice = poiPostOffice;
    }

    public int getPoiTransport() {
        return poiTransport;
    }

    public void setPoiTransport(int poiTransport) {
        this.poiTransport = poiTransport;
    }

    public int getPoiBusStop() {
        return poiBusStop;
    }

    public void setPoiBusStop(int poiBusStop) {
        this.poiBusStop = poiBusStop;
    }

    public double getLon() {
        return lon;
    }

    public void setLon(double lon) {
        this.lon = lon;
    }

    public double getLat() {
        return lat;
    }

    public void setLat(double lat) {
        this.lat = lat;
    }

    public boolean isForbidden() {
        return isForbidden;
    }

    public void setForbidden(boolean forbidden) {
        isForbidden = forbidden;
    }

    public int getLockerCount() {
        return lockerCount;
    }

    public void setLockerCount(int lockerCount) {
        this.lockerCount = lockerCount;
    }

    public int getGridCountByMahalle() {
        return gridCountByMahalle;
    }

    public void setGridCountByMahalle(int gridCountByMahalle) {
        this.gridCountByMahalle = gridCountByMahalle;
    }

    public double getPopulation() {
        return population;
    }

    public void setPopulation(double population) {
        this.population = population;
    }

    public double getDemandScore() {
        return demandScore;
    }

    public void setDemandScore(double demandScore) {
        this.demandScore = demandScore;
    }

    @Override
    public String toString() {
        return "CandidatePoint{" +
                "id=" + id +
                ", mahalleNameTurkish='" + mahalleNameTurkish + '\'' +
                ", mahalleNameEnglish='" + mahalleNameEnglish + '\'' +
                ", mahallePopulation=" + mahallePopulation +
                ", poiAtm=" + poiAtm +
                ", poiBank=" + poiBank +
                ", poiHospital=" + poiHospital +
                ", poiSchool=" + poiSchool +
                ", poiUniversity=" + poiUniversity +
                ", poiPostOffice=" + poiPostOffice +
                ", poiTransport=" + poiTransport +
                ", poiBusStop=" + poiBusStop +
                ", lon=" + lon +
                ", lat=" + lat +
                ", isForbidden=" + isForbidden +
                ", lockerCount=" + lockerCount +
                ", gridCountByMahalle=" + gridCountByMahalle +
                ", population=" + population +
                ", demandScore=" + demandScore +
                '}';
    }
}
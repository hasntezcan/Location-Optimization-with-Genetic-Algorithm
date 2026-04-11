import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

public class CsvLoader {

    public void loadCandidates(String filePath, CandidateRepository repository) throws IOException {
        BufferedReader reader = new BufferedReader(new FileReader(filePath));

        String line;
        boolean isFirstLine = true;

        while ((line = reader.readLine()) != null) {
            if (isFirstLine) {
                isFirstLine = false;
                continue;
            }

            if (line.trim().isEmpty()) {
                continue;
            }

            String[] parts = line.split(",");

            // Mapping based on data/candidate_points.csv:
            // fid: 0, id: 1, left: 2, top: 3, right: 4, bottom: 5, row_index: 6, col_index: 7,
            // Mahalle_Name_Turkish: 8, Mahalle_Name_English: 9, population_mahalle: 10,
            // poi_atm: 11, poi_bank: 12, poi_hospital: 13, poi_school: 14, poi_university: 15,
            // poi_post_office: 16, poi_transport: 17, poi_bus_stop: 18,
            // lon: 19, lat: 20, is_forbidden: 21, locker_count: 22, grid_count_by_mahalle: 23, population_candidate: 24

            CandidatePoint candidate = new CandidatePoint(
                    Integer.parseInt(parts[1].trim()),    // id
                    parts[8].trim(),                      // mahalleNameTurkish
                    parts[9].trim(),                      // mahalleNameEnglish
                    Integer.parseInt(parts[10].trim()),   // mahallePopulation
                    Integer.parseInt(parts[11].trim()),   // poiAtm
                    Integer.parseInt(parts[12].trim()),   // poiBank
                    Integer.parseInt(parts[13].trim()),   // poiHospital
                    Integer.parseInt(parts[14].trim()),   // poiSchool
                    Integer.parseInt(parts[15].trim()),   // poiUniversity
                    Integer.parseInt(parts[16].trim()),   // poiPostOffice
                    Integer.parseInt(parts[17].trim()),   // poiTransport
                    Integer.parseInt(parts[18].trim()),   // poiBusStop
                    Double.parseDouble(parts[19].trim()), // lon
                    Double.parseDouble(parts[20].trim()), // lat
                    Integer.parseInt(parts[21].trim()) == 1, // isForbidden
                    Integer.parseInt(parts[22].trim()),   // lockerCount
                    Integer.parseInt(parts[23].trim()),   // gridCountByMahalle
                    Double.parseDouble(parts[24].trim()), // population (candidate population)
                    Double.parseDouble(parts[26].trim())  // demandScore (new field)
            );

            repository.addCandidate(candidate);
        }

        reader.close();
    }
}
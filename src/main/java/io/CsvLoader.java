package io;

import model.CandidatePoint;
import model.CandidateRepository;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

/**
 * Loads candidate point data from CSV files into a {@link CandidateRepository}.
 * The loader expects the enriched candidate points CSV format used by the
 * location optimization model.
 */
public class CsvLoader {

    /**
     * Creates a CSV loader instance.
     */
    public CsvLoader() {
    }

    /**
     * Reads candidate points from the given CSV file and adds them to the repository.
     * The first line is treated as a header and skipped. Empty lines are ignored.
     *
     * <p>The method maps values by fixed column positions from the enriched
     * {@code candidate_points.csv} structure, including candidate id,
     * neighborhood names, population fields, POI counts, coordinates,
     * forbidden status, locker count, and demand scores.</p>
     *
     * @param filePath path of the CSV file to load
     * @param repository repository that receives the loaded candidate points
     * @throws IOException if the CSV file cannot be opened or read
     */
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

            // Mapping based on enriched candidate_points.csv:
            // fid:0, id:1, ..., population_candidate:24, poi_score:25, demand_final:26

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
                    Double.parseDouble(parts[25].trim()), // poiScore
                    Double.parseDouble(parts[26].trim())  // demandScore (demand_final)
            );

            repository.addCandidate(candidate);
        }

        reader.close();
    }
}
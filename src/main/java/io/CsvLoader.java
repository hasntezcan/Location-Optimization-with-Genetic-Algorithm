package io;

import model.CandidatePoint;
import model.CandidateRepository;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

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
     * <p>The method maps values by CSV header name from the enriched
     * {@code candidate_points.csv} structure, including candidate id,
     * neighborhood names, population fields, POI counts, coordinates,
     * forbidden status, locker count, and demand scores. If the generated
     * {@code poi_score} or {@code demand_final} columns are missing, the loader
     * falls back to {@code poi_score = 0} and
     * {@code demand_final = population_candidate}; that fallback is intended to
     * keep local runs debuggable, not to preserve the full scientific demand
     * model.</p>
     *
     * @param filePath path of the CSV file to load
     * @param repository repository that receives the loaded candidate points
     * @throws IOException if the CSV file cannot be opened or read
     */
    public void loadCandidates(String filePath, CandidateRepository repository) throws IOException {
        try (BufferedReader reader = new BufferedReader(new FileReader(filePath))) {
            String headerLine = reader.readLine();
            if (headerLine == null) {
                throw new IOException("CSV file is empty: " + filePath);
            }

            Map<String, Integer> headerIndex = buildHeaderIndex(splitCsvLine(headerLine));
            boolean hasPoiScore = headerIndex.containsKey("poi_score");
            boolean hasDemandFinal = headerIndex.containsKey("demand_final");

            String line;
            int lineNumber = 1;
            while ((line = reader.readLine()) != null) {
                lineNumber++;

                if (line.trim().isEmpty()) {
                    continue;
                }

                String[] parts = splitCsvLine(line);

                double population = parseDoubleField(parts, headerIndex, "population_candidate", lineNumber);
                double poiScore = hasPoiScore
                        ? parseDoubleField(parts, headerIndex, "poi_score", lineNumber)
                        : 0.0;
                double demandScore = hasDemandFinal
                        ? parseDoubleField(parts, headerIndex, "demand_final", lineNumber)
                        : population;

                CandidatePoint candidate = new CandidatePoint(
                        parseIntField(parts, headerIndex, "id", lineNumber),
                        getRequiredField(parts, headerIndex, "Mahalle_Name_Turkish", lineNumber),
                        getRequiredField(parts, headerIndex, "Mahalle_Name_English", lineNumber),
                        parseIntField(parts, headerIndex, "population_mahalle", lineNumber),
                        parseIntField(parts, headerIndex, "poi_atm", lineNumber),
                        parseIntField(parts, headerIndex, "poi_bank", lineNumber),
                        parseIntField(parts, headerIndex, "poi_hospital", lineNumber),
                        parseIntField(parts, headerIndex, "poi_school", lineNumber),
                        parseIntField(parts, headerIndex, "poi_university", lineNumber),
                        parseIntField(parts, headerIndex, "poi_post_office", lineNumber),
                        parseIntField(parts, headerIndex, "poi_transport", lineNumber),
                        parseIntField(parts, headerIndex, "poi_bus_stop", lineNumber),
                        parseDoubleField(parts, headerIndex, "lon", lineNumber),
                        parseDoubleField(parts, headerIndex, "lat", lineNumber),
                        parseIntField(parts, headerIndex, "is_forbidden", lineNumber) == 1,
                        parseIntField(parts, headerIndex, "locker_count", lineNumber),
                        parseIntField(parts, headerIndex, "grid_count_by_mahalle", lineNumber),
                        population,
                        poiScore,
                        demandScore
                );

                repository.addCandidate(candidate);
            }
        }
    }

    private String[] splitCsvLine(String line) {
        return line.split(",", -1);
    }

    private Map<String, Integer> buildHeaderIndex(String[] headers) {
        Map<String, Integer> index = new HashMap<>();

        for (int i = 0; i < headers.length; i++) {
            String name = headers[i].trim().replace("\uFEFF", "");
            index.put(name, i);
        }

        return index;
    }

    private String getRequiredField(String[] parts,
                                    Map<String, Integer> headerIndex,
                                    String columnName,
                                    int lineNumber) {
        Integer index = headerIndex.get(columnName);
        if (index == null) {
            throw new IllegalStateException("Missing required CSV column: " + columnName);
        }

        if (index >= parts.length) {
            throw new IllegalStateException(
                    "Line " + lineNumber + " is missing value for CSV column: " + columnName
            );
        }

        String value = parts[index].trim();
        if (value.isEmpty()) {
            throw new IllegalStateException(
                    "Line " + lineNumber + " has blank value for CSV column: " + columnName
            );
        }

        return value;
    }

    private int parseIntField(String[] parts,
                              Map<String, Integer> headerIndex,
                              String columnName,
                              int lineNumber) {
        String value = getRequiredField(parts, headerIndex, columnName, lineNumber);
        return Integer.parseInt(value);
    }

    private double parseDoubleField(String[] parts,
                                    Map<String, Integer> headerIndex,
                                    String columnName,
                                    int lineNumber) {
        String value = getRequiredField(parts, headerIndex, columnName, lineNumber);
        return Double.parseDouble(value);
    }
}

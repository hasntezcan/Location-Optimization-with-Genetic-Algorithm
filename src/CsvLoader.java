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

            CandidatePoint candidate = new CandidatePoint(
                    Integer.parseInt(parts[0].trim()),    
                    parts[1].trim(),                       
                    parts[2].trim(),                      
                    Integer.parseInt(parts[3].trim()),     
                    Integer.parseInt(parts[4].trim()),     
                    Integer.parseInt(parts[5].trim()),     
                    Integer.parseInt(parts[6].trim()),     
                    Integer.parseInt(parts[7].trim()),    
                    Integer.parseInt(parts[8].trim()),     
                    Integer.parseInt(parts[9].trim()),     
                    Integer.parseInt(parts[10].trim()),    
                    Integer.parseInt(parts[11].trim()),    
                    Double.parseDouble(parts[12].trim()),  
                    Double.parseDouble(parts[13].trim()),  
                    Integer.parseInt(parts[14].trim()) == 1, 
                    Integer.parseInt(parts[15].trim()),    
                    Integer.parseInt(parts[16].trim()),    
                    Double.parseDouble(parts[17].trim())   
            );

            repository.addCandidate(candidate);
        }

        reader.close();
    }
}
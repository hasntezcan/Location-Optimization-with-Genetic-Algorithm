package io;

import org.jetbrains.bio.npy.NpyArray;
import org.jetbrains.bio.npy.NpyFile;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Loads a precomputed distance matrix from an NPY file.
 *
 * <p>The loader expects a square 2D matrix stored in NumPy's NPY format.
 * Supported numeric array payloads are {@code float[]} and {@code double[]}.</p>
 */
public class DistanceMatrixLoader {

    /**
     * Loads the distance matrix from the given file path.
     *
     * @param filePath path of the NPY distance matrix file
     * @return distance matrix as a 2D {@code double} array
     * @throws IOException if the file cannot be opened or read
     * @throws IllegalArgumentException if the file path is null or blank
     * @throws IllegalStateException if the loaded matrix is not square
     *                               or has an unsupported data type
     */
    public double[][] loadDistanceMatrix(String filePath) throws IOException {
        if (filePath == null || filePath.isBlank()) {
            throw new IllegalArgumentException("Distance matrix file path cannot be null or blank.");
        }

        Path path = Paths.get(filePath);
        NpyArray npyArray = NpyFile.read(path, Integer.MAX_VALUE);

        int[] shape = npyArray.getShape();
        if (shape.length != 2) {
            throw new IllegalStateException(
                    "Expected a 2D distance matrix, but got shape length: " + shape.length
            );
        }

        int rows = shape[0];
        int cols = shape[1];

        if (rows != cols) {
            throw new IllegalStateException(
                    "Distance matrix must be square, but got: " + rows + "x" + cols
            );
        }

        Object rawData = npyArray.getData();
        double[][] matrix = new double[rows][cols];

        if (rawData instanceof float[]) {
            float[] flat = (float[]) rawData;

            if (flat.length != rows * cols) {
                throw new IllegalStateException("Flat float data length does not match matrix shape.");
            }

            int index = 0;
            for (int i = 0; i < rows; i++) {
                for (int j = 0; j < cols; j++) {
                    matrix[i][j] = flat[index++];
                }
            }
            return matrix;
        }

        if (rawData instanceof double[]) {
            double[] flat = (double[]) rawData;

            if (flat.length != rows * cols) {
                throw new IllegalStateException("Flat double data length does not match matrix shape.");
            }

            int index = 0;
            for (int i = 0; i < rows; i++) {
                for (int j = 0; j < cols; j++) {
                    matrix[i][j] = flat[index++];
                }
            }
            return matrix;
        }

        throw new IllegalStateException(
                "Unsupported NPY data type: " + rawData.getClass().getName() +
                ". Expected float[] or double[]."
        );
    }
}
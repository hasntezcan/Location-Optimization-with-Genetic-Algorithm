# Smart City Service Location Recommendation System

A data-driven decision support system that recommends optimal locations for urban services (such as parcel lockers, emergency shelters, etc.) using spatial data analysis. It replaces intuition-based planning with a structured, reproducible, and extensible geographic pipeline.

## ⚙️ Project Pipeline

The system follows a 6-step spatial analysis workflow:

1. **Data Collection:** Gathers base geographic and urban datasets from OpenStreetMap (OSM), population censuses, and road networks.
2. **Map Preparation:** Cleans and organizes GIS layers to define the study area and extract relevant geometries (points, lines, polygons).
3. **Spatial Feature Extraction:** Calculates meaningful metrics for the environment, such as proximity to roads, POI density, and neighborhood characteristics.
4. **Candidate Generation:** Discretizes the study area into evaluable candidate locations (grids or points) for consistent comparison.
5. **Evaluation & Scoring:** Applies objective criteria and optimization algorithms to score candidate areas based on the extracted spatial features.
6. **Recommendation Output:** Generates ranked candidate lists and map-based visualizations to support final planning decisions.

## 🎯 Current Focus & Goals

The primary goal is to build a **robust spatial data pipeline** rather than just producing a one-off map. Currently, the focus is on:
- Establishing a clean, modular codebase.
- Ensuring smooth data flow from raw OSM extraction to final algorithmic evaluation.
- Preparing the system architecture to easily integrate new decision layers and advanced multi-objective optimization models.

## 🛠️ Tech Stack

- **Language:** Python
- **Geospatial Tools:** QGIS, OpenStreetMap (OSM)
- **Data Processing:** Pandas, NumPy, and spatial analysis libraries
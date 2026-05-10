# Parcel Locker UI

An interactive dashboard for exploring parcel locker placement results on a map (Kadikoy).

This UI can be used in two modes:
- **Archive asset mode (default data flow)**: reads generated or committed assets from `public/mock/` to browse archive solutions.
- **Trigger real optimization (local/dev)**: calls `POST /api/run-ga` to run the Java SPEA2 optimizer from the project root, generate plots, and refresh UI assets.

Tech stack: **Next.js**, **React**, **TypeScript**, **Tailwind CSS**, **React Leaflet**, **Recharts**, **lucide-react**.

---

## What this UI is for

This project is a visual decision-support interface for parcel locker placement.

Its purpose is to let a user:

- choose the locker count `K`
- load candidate, boundary, and final archive result data
- optionally trigger a real SPEA2 run locally (via `POST /api/run-ga`)
- browse final archive solutions and Pareto flags
- explore selected locker sets on a map
- inspect the currently selected locker and solution metrics

In short, this UI is a **presentation and interaction layer** for optimization results. The optimizer itself lives in the Java project root; the UI can optionally trigger it in local/dev mode.

---

## Current behavior of the UI

### 1. Initial data loading

When the page opens, the app loads candidate and boundary data from `public/mock/`:

- `candidate-points.json`
- `kadikoy_boundary.geojson`

The candidate file contains potential locker locations and their attributes such as neighborhood, population, POI counts, forbidden status, and related metadata.

The boundary file is used to draw the district outline on the map. The UI also
tries to load `ga-results.json` when it exists. That generated file contains
final archive solutions, objective values, normalized values, Pareto flags, and
best-f1/best-f2 markers generated from `output/final_archive.csv`.

If the files cannot be loaded, the app logs an error in the browser console.

---

### 2. Archive solution loading

After data is loaded, the UI displays the solutions from `ga-results.json` when
that generated file exists. These records represent archive solutions, not true
generation-by-generation optimizer history.

Each archive solution contains:

- selected locker candidates
- accessibility score (`f1`)
- equity score (`f2`)
- total SPEA2 fitness
- normalized objective values
- Pareto and best-objective flags

---

### 3. Locker count input

The left control panel contains a number input for locker count.

When the user clicks **Run Optimization**:

- the input is clamped between `1` and `20`
- runtime parameters are sent to `/api/run-ga`
- Java writes new archive CSV outputs
- Python regenerates `ga-results.json` and the analysis plot
- the current solution resets to the beginning
- playback stops

The advanced controls also expose population size, max generations, mutation
rate, crossover rate, archive size, and optional random seed.

---

### 4. Solution playback

The UI supports archive-solution playback controls:

- **Prev**: move one solution backward
- **Play / Pause**: start or stop automatic playback
- **Next**: move one solution forward
- **Solution slider**: jump directly to a specific archive solution
- **Playback speed slider**: adjust automatic playback interval

When playback reaches the final solution, it loops back to the first solution.

---

### 5. Top locker strip

At the top of the dashboard, the UI shows the lockers in the current archive
solution as a horizontal strip.

Each card shows:

- locker order
- locker label
- neighborhood
- selected state

Clicking a card changes the current selection.

This strip is mainly a quick-selection UI for switching focus between lockers without using the map.

---

### 6. Map behavior

The center panel contains an interactive map built with React Leaflet.

The map shows four visual layers:

#### Boundary
The Kadikoy boundary is drawn from the GeoJSON file.

#### Candidate points
All candidate points not selected in the current archive solution are shown as
small gray markers.

#### Existing locker context
Candidate cells with `locker_count > 0` are aggregated into neighborhood-level
existing-locker markers.

#### Proposed lockers
Selected lockers from the current archive solution are shown as larger blue
circles.

Color meaning in the current implementation:

- **black / dark**: currently selected proposed locker
- **blue**: proposed locker in the current archive solution
- **rose**: existing-locker context marker
- **gray**: candidate point

Clicking a locker on the map selects it.

When a locker becomes selected, the map automatically flies to that location.

Each locker popup shows:

- locker name
- neighborhood
- latitude
- longitude
- its display order in the archive solution

---

### 7. Selected locker detail panel

The right panel shows detailed information for the currently selected locker.

It includes:

- locker name
- neighborhood
- archive solution number
- latitude
- longitude
- accessibility metric
- equity metric
- fitness metric

These metrics belong to the **active archive solution**, not to the individual locker itself.

---

### 8. Selection behavior

The UI tries to preserve the selected locker when the active archive solution changes.

If the previously selected locker still exists in the new solution, it stays selected.

If it no longer exists, the selection is cleared.

This behavior keeps the UI stable during playback.

---

## Real optimization (local/dev)

When you trigger “Optimization” from the UI, `/api/run-ga` performs:
- Passes runtime parameters to Java via Maven `-Dexec.args` (`k`, optionally
  `populationSize`, `maxGenerations`, `mutationRate`, `crossoverRate`,
  `archiveSize`, `randomSeed`)
- Runs `mvn compile exec:java` in the project root
- Runs `scripts/plot_archives.py` and produces `output/archive_comparison_latest.png`
- Copies the latest plot into the UI public folder: `public/mock/archive_comparison_latest.png`
- Regenerates the UI’s mock result assets from the GA outputs
- Streams progress and completion/error events back to the browser as
  `text/event-stream`

Runtime environment variables supported by the route:

| Variable | Purpose |
| --- | --- |
| `PROJECT_ROOT` | Override the Java project root |
| `UI_ROOT` | Override the Next.js app root |
| `GA_CANDIDATE_CSV` | Candidate CSV path passed to child processes |
| `GA_DISTANCE_MATRIX` | Distance matrix path passed to child processes |
| `GA_OUTPUT_DIR` | Java/Python output directory |
| `UI_MOCK_DIR` | UI public mock output directory |
| `MAVEN_CMD` | Maven executable override |
| `PYTHON_CMD` | Python executable override used for plot and GA-output processing scripts |
| `GA_MAX_RUNTIME_MS` | Java process timeout |

This mode:
- is not a production backend design; it is intended for local development/experiments
- should not be deployed to production because it spawns Maven and Python
  processes from a web route

---

## Tech stack

- **Next.js**
- **React**
- **TypeScript**
- **Tailwind CSS**
- **React Leaflet**
- **Recharts**
- **lucide-react**
- **OpenStreetMap tiles**

---

## Project structure

```text
parcel-locker-ui/
├─ public/
│  └─ mock/
│     ├─ candidate-points.json
│     ├─ candidate_points.csv
│     ├─ ga-results.json              (generated)
│     ├─ archive_comparison_latest.png (generated)
│     └─ kadikoy_boundary.geojson
├─ src/
│  ├─ app/
│  │  ├─ api/
│  │  │  └─ run-ga/
│  │  │     └─ route.ts
│  │  ├─ globals.css
│  │  ├─ layout.tsx
│  │  └─ page.tsx
│  ├─ components/
│  │  └─ dashboard/
│  │     ├─ control-panel.tsx
│  │     ├─ locker-detail-panel.tsx
│  │     ├─ locker-map.tsx
│  │     └─ locker-strip.tsx
│  ├─ lib/
│  │  ├─ chart-data.ts
│  │  ├─ ga-api.ts
│  │  ├─ ga-mock.ts
│  │  ├─ mcda.ts
│  │  ├─ mock-data.ts
│  │  ├─ python-runner.ts
│  │  ├─ solution-utils.ts
│  │  ├─ types.ts
│  │  └─ server/
│  │     ├─ ga-runner.ts
│  │     └─ runtime-config.ts
│  └─ scripts/
│     ├─ build_candidate_json.py
│     └─ process_ga_data.py
├─ package.json
├─ package-lock.json
├─ tsconfig.json
├─ next.config.ts
├─ postcss.config.mjs
└─ eslint.config.mjs
```

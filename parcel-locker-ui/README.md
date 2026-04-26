# Parcel Locker UI

An interactive dashboard for exploring parcel locker placement results on a map (Kadikoy).

This UI can be used in two modes:
- **Mock mode (default data flow)**: reads assets from `public/mock/` to quickly demo archive/solution navigation.
- **Trigger real optimization (local/dev)**: calls `POST /api/run-ga` to run the Java SPEA2 optimizer from the project root, generate plots, and refresh UI assets.

Tech stack: **Next.js**, **React**, **TypeScript**, **Tailwind CSS**, **React Leaflet**.

---

## What this UI is for

This project is a visual decision-support interface for parcel locker placement.

Its purpose is to let a user:

- choose how many parcel lockers should be displayed
- load mock candidate and boundary data
- simulate a fake genetic-algorithm style generation sequence
- optionally trigger a real SPEA2 run locally (via `POST /api/run-ga`)
- inspect how selected lockers change across generations
- explore the current result on a map
- inspect the currently selected locker and generation metrics

In short, this UI is a **presentation and interaction layer** for optimization results. The optimizer itself lives in the Java project root; the UI can optionally trigger it in local/dev mode.

---

## Current behavior of the UI

### 1. Initial data loading

When the page opens, the app loads two files from `public/mock/`:

- `candidate-points.json`
- `kadikoy_boundary.geojson`

The candidate file contains potential locker locations and their attributes such as neighborhood, population, POI counts, forbidden status, and related metadata.

The boundary file is used to draw the district outline on the map.

If the files cannot be loaded, the app logs an error in the browser console.

---

### 2. Fake generation creation

After candidate data is loaded, the UI builds a mock optimization run using `buildFakeGenerationRun()`.

This fake run produces a sequence of generations. Each generation contains:

- a list of currently active lockers
- accessibility score
- equity score
- overall fitness score

These generations are **synthetic**. They are not produced by the real GA/SPEA2 implementation. They only imitate the behavior of an evolving optimization process for UI testing and demonstration.

---

### 3. Locker count input

The left control panel contains a number input for locker count.

When the user clicks **Build fake generations**:

- the input is clamped between `1` and `100`
- a new fake generation sequence is built
- the current generation resets to the beginning
- playback stops

This means the locker count acts as a regeneration trigger for the full mock run.

---

### 4. Generation playback

The UI supports generation playback controls:

- **Prev**: move one generation backward
- **Play / Pause**: start or stop automatic playback
- **Next**: move one generation forward
- **Generation slider**: jump directly to a specific generation
- **Playback speed selector**:
  - Slow
  - Normal
  - Fast
  - Stress test

When playback reaches the final generation, it loops back to generation 1.

---

### 5. Top locker strip

At the top of the dashboard, the UI shows the lockers in the current generation as a horizontal strip.

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
All candidate points that are neither active in the current generation nor visible in the previous generation are shown as very small gray markers.

#### Previous generation lockers
Lockers that existed in the previous generation but are not active now are shown as faded light-gray circles.

#### Current generation lockers
Current active lockers are shown as larger colored circles.

Color meaning in the current implementation:

- **black / dark**: currently selected locker
- **blue**: locker persisted from previous generation
- **purple**: locker is new in the current generation

Clicking a locker on the map selects it.

When a locker becomes selected, the map automatically flies to that location.

Each locker popup shows:

- locker name
- neighborhood
- latitude
- longitude
- whether it is new or persisted
- its display order in the generation

---

### 7. Selected locker detail panel

The right panel shows detailed information for the currently selected locker.

It includes:

- locker name
- neighborhood
- generation number
- latitude
- longitude
- accessibility metric
- equity metric
- fitness metric

These metrics belong to the **active generation**, not to the individual locker itself.

---

### 8. Selection behavior

The UI tries to preserve the selected locker when generations change.

If the previously selected locker still exists in the new generation, it stays selected.

If it no longer exists, the first locker in the new generation becomes selected automatically.

This behavior keeps the UI stable during playback.

---

## Real optimization (local/dev)

When you trigger “Optimization” from the UI, `/api/run-ga` performs:
- Updates a few parameters in `src/main/java/config/GAParameters.java` (`k`, optionally `populationSize`, `maxGenerations`, `mutationRate`)
- Runs `mvn compile exec:java` (in the project root)
- Runs `scripts/plot_archives.py` and produces `output/archive_comparison_latest.png`
- Copies the latest plot into the UI public folder: `public/mock/archive_comparison_latest.png`
- Regenerates the UI’s mock result assets from the GA outputs

This mode:
- is not a production backend design; it is intended for local development/experiments
- should not be deployed to production because it runs shell commands via `child_process.exec` on the server

---

## Tech stack

- **Next.js**
- **React**
- **TypeScript**
- **Tailwind CSS**
- **React Leaflet**
- **OpenStreetMap tiles**

---

## Project structure

```text
parcel-locker-ui/
├─ public/
│  └─ mock/
│     ├─ candidate-points.json
│     ├─ candidate_points.csv
│     ├─ ga-results.json
│     ├─ archive_comparison_latest.png
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
│  │  ├─ ga-mock.ts
│  │  ├─ mock-data.ts
│  │  └─ types.ts
│  └─ scripts/
│     └─ build_candidate_json.py
│     └─ process_ga_data.py
├─ package.json
├─ package-lock.json
├─ tsconfig.json
├─ next.config.ts
├─ postcss.config.mjs
└─ eslint.config.mjs

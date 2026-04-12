# Parcel Locker UI

A mock interactive dashboard for visualizing parcel locker placement results in Kadıköy.

This UI is part of a larger parcel-locker location optimization project. The current implementation is a **frontend prototype** built with **Next.js**, **React**, **Tailwind CSS**, and **React Leaflet**. It does **not** run the real optimization algorithm yet. Instead, it loads mock spatial data and simulates a fake generation-by-generation optimization flow so the team can explore interface behavior, map interaction, and result presentation.

---

## What this UI is for

This project is a visual decision-support interface for parcel locker placement.

Its purpose is to let a user:

- choose how many parcel lockers should be displayed
- load mock candidate and boundary data
- simulate a fake genetic-algorithm style generation sequence
- inspect how selected lockers change across generations
- explore the current result on a map
- inspect the currently selected locker and generation metrics

In short, this UI is a **presentation and interaction layer** for optimization results, not the real optimization engine itself.

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
The Kadıköy boundary is drawn from the GeoJSON file.

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

## Important limitation

This project currently uses a **mock optimizer**.

That means:

- there is **no real genetic algorithm execution in the UI**
- there is **no backend optimization service**
- there is **no persistence layer**
- there is **no real-time API**
- accessibility, equity, and fitness values are **artificially generated for demonstration**

So this repository should currently be understood as a **UI prototype for optimization result exploration**.

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
│     └─ kadikoy_boundary.geojson
├─ src/
│  ├─ app/
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
├─ package.json
├─ package-lock.json
├─ tsconfig.json
├─ next.config.ts
├─ postcss.config.mjs
└─ eslint.config.mjs
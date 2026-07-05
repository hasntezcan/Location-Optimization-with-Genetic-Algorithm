# V1 Map UI Strategy

## Current Leaflet Limitations

The current UI uses a map/dashboard experience suitable for viewing Kadikoy parcel locker candidates and optimizer outputs. As V1 evolves into a scenario sandbox, the map needs stronger support for editing, layered rendering, large datasets, and richer comparison interactions.

Leaflet can continue to serve near-term needs, but it may become limiting for:

- High-volume point and polygon rendering.
- GPU-accelerated heatmaps and coverage layers.
- Complex layer styling.
- Scenario editing interactions.
- Smooth comparison of many generated alternatives.

## Target Map Role

The V1 map should become a scenario canvas, not just a viewer.

Users should be able to:

- Inspect grid features.
- Add or import facilities.
- Disable existing facilities.
- Lock proposed locations.
- Toggle objective and benchmark layers.
- Compare current, optimized, and edited scenarios.
- Export or report scenario assumptions.

## Possible MapLibre + deck.gl Direction

A possible future stack is:

- MapLibre for base map and vector style control.
- deck.gl for high-performance layers, heatmaps, arcs, coverage surfaces, and large point sets.
- A scenario state store that maps UI edits to backend scenario contracts.

This is a direction, not an immediate requirement. Migration should be phased and validated against real UI needs.

## Map Layer Architecture

Potential layers:

- Base map.
- Candidate grid points.
- Forbidden or disabled candidates.
- Demand or risk heatmap.
- Existing facilities.
- Proposed facilities.
- Locked facilities.
- Optimized solution candidates.
- Coverage isochrone or distance bands.
- Scenario comparison delta layer.
- Neighborhood or administrative boundaries.

Each layer should have:

- Source metadata.
- Visibility state.
- Styling rules.
- Tooltip or selection behavior.
- Link back to candidate IDs or scenario facility IDs where applicable.

## Sandbox Interactions

The map sandbox should eventually support:

- Add facility: click candidate or map location, then snap to candidate.
- Remove or disable facility: mark an existing scenario facility inactive.
- Lock proposed location: force optimizer to include a candidate.
- Show coverage: visualize service areas or threshold coverage.
- Show heatmap: display demand, risk, or underserved areas.
- Compare scenarios: show current, optimized, expansion, or edited variants.

## Migration Phases

### Phase A: Stabilize Current Viewer

- Keep the current map working.
- Document current generated mock data.
- Preserve candidate ID references.

### Phase B: Scenario State in UI

- Add frontend scenario state for existing, proposed, disabled, and locked facilities.
- Keep backend behavior unchanged until contracts are ready.

### Phase C: Backend Scenario Contract

- Send scenario JSON to the backend.
- Validate candidate IDs and constraints.
- Store run metadata for scenario assumptions.

### Phase D: Rich Layer System

- Introduce explicit layer definitions and toggles.
- Add coverage and heatmap overlays.
- Improve scenario comparison rendering.

### Phase E: Map Modernization

- Evaluate MapLibre and deck.gl against real scenario editing needs.
- Migrate only when the current Leaflet surface blocks planned interactions or performance.


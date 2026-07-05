# Repository Structure

This file describes the current repository layout for humans and AI agents. It is a static guide, not a generated tree.

## Root Files

- `readme.md`: quick-start guide for the current project.
- `AGENTS.md`: first-read operating guide for AI agents.
- `CLAUDE.md`: Claude Code specific operating guide.
- `pom.xml`: Java Maven configuration for the optimizer.
- `requirements.txt`: Python dependency list for scripts.
- `Dockerfile`, `docker-compose.yml`: local/container deployment artifacts.

## Source Folders

- `src/main/java`: Java SPEA2 optimizer, models, loaders, configuration, and app entry points.
- `parcel-locker-ui/src`: Next.js UI, dashboard components, local API route, and UI helper libraries.
- `parcel-locker-ui/src/scripts`: Python scripts used by the UI pipeline to convert optimizer outputs into UI-readable artifacts.
- `scripts`: Python analysis, demand preparation, plotting, validation, and research scripts.
- `data/prepare_ga_inputs.py`: data preparation entry point for candidate and matrix artifacts.

## Data Folders

- `data/candidate_points.csv`: current V0 runtime candidate source.
- `data/kadikoy_distance_meters_nxn.npy`: current V0 runtime distance matrix.
- `data/kadikoy_candidate_ids_sorted.npy`, `data/kadikoy_index_map.csv`: matrix and candidate alignment support artifacts.
- `data/raw`: provenance and raw source material. Treat as source evidence, not routine runtime state.
- `data/archive`: backups and historical data artifacts. Do not edit casually.

## Documentation Folders

- `docs`: current V1 documentation, deployment notes, and repository structure.
- `docs/archive`: older and archived reference material.
- `docs/archive/COMPREHENSIVE_PROJECT_GUIDE_old.md`: archived V0 technical guide for the Kadikoy parcel locker implementation. Use only for historical implementation details; it is not authoritative for V1 architecture.
- `docs/DEPLOYMENT_PHASE1.md`: deployment notes for the current local/container architecture.

## Generated Folders and Files

- `output`: generated optimizer archives, plots, run metadata, and benchmark artifacts. Do not edit by hand unless explicitly requested.
- `parcel-locker-ui/.next`: generated Next.js build/dev output. Do not edit.
- `parcel-locker-ui/public/mock`: generated or copied UI data used by the dashboard. Treat as generated unless the task explicitly targets UI mock data.
- `target`: Maven build output if present. Do not edit.

## Legacy, Archive, and Research Areas

- `backup`: experimental or older Java code.
- `scripts/archive`: legacy and one-off scripts. Use as reference before copying patterns into active code.
- `scripts/archive/one_off`: one-time analysis utilities.
- `scripts/archive/legacy`: legacy scripts retained for provenance.
- `scripts/research`: research-specific scripts for report questions and figures.
- `scripts/validation`: validation and benchmark scripts.
- `sections/figures/final_results`: research/report figures and summaries.

## What Agents Should Not Touch Casually

- Do not edit `.next`.
- Do not hand-edit `output`.
- Do not mutate `data/raw` provenance files.
- Do not rewrite `data/archive`.
- Do not modify candidate IDs or reorder candidate rows without also rebuilding and validating distance matrix alignment.
- Do not infer existing facilities from `nearby_locker_count`.
- Do not reintroduce `locker_count > 0` as existing facility logic.
- Do not stage or commit unless explicitly asked.

## Current Runtime Path

```text
Next.js UI
  -> /api/run-ga
  -> parcel-locker-ui/src/lib/server/ga-runner.ts
  -> Maven / Java app.Main
  -> output archives and run metadata
  -> scripts/plot_archives.py
  -> parcel-locker-ui/src/scripts/process_ga_data.py
  -> parcel-locker-ui/public/mock
  -> dashboard and map views
```

The V1 architecture should generalize this path over time, but current work should respect the existing V0 contracts unless a migration task explicitly changes them.

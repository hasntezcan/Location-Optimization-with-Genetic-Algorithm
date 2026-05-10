# Phase 1 Deployment Notes

Phase 1 keeps the existing behavior: the Next.js API route still runs Maven, waits for the Java GA, runs Python plotting/post-processing, and refreshes files under the UI mock asset directory.

## Required Tools

- Node.js and npm for `parcel-locker-ui`
- Java 17
- Maven
- Python 3
- Python packages from `requirements.txt`

Install Python run-path dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Environment Configuration

Copy `.env.example` and set values only when the defaults do not match your runtime layout.

Important variables:

- `PROJECT_ROOT`: repository root. Defaults to the parent of the UI cwd in the API route.
- `UI_ROOT`: `parcel-locker-ui` directory. Defaults to the API process cwd.
- `GA_CANDIDATE_CSV`: candidate CSV path. Default: `data/candidate_points.csv`.
- `GA_DISTANCE_MATRIX`: distance matrix path. Default: `data/kadikoy_distance_meters_nxn.npy`.
- `GA_OUTPUT_DIR`: Java/Python output directory. Default: `output`.
- `UI_MOCK_DIR`: generated UI public mock directory. Default: `parcel-locker-ui/public/mock`.
- `MAVEN_CMD`: Maven executable override. Defaults to `mvn.cmd` on Windows and `mvn` elsewhere.
- `PYTHON_CMD`: Python executable override. Defaults to detection of `py`/`python` on Windows and `python3`/`python` elsewhere.
- `GA_MAX_RUNTIME_MS`: timeout for the Java GA process launched by `/api/run-ga`. Default: `900000`.

Relative paths are resolved relative to `PROJECT_ROOT` when it is set.

## Local Run

From the repository root:

```bash
mvn compile
python3 -m pip install -r requirements.txt
cd parcel-locker-ui
npm install
npm run dev
```

Then use the existing UI. The `/api/run-ga` contract and streaming response are unchanged.

## Docker Compose

The Phase 1 Docker setup intentionally mirrors the current architecture in one service: the Next.js server runs and still spawns Maven and Python inside the same container.

```bash
docker compose up --build
```

The compose file mounts:

- `./data` read-only at `/app/data`
- `./output` read-write at `/app/output`
- `./parcel-locker-ui/public/mock` read-write for generated UI assets

## Phase 1 Limitations

- `/api/run-ga` still keeps one request open until Java and Python finish.
- Outputs are still shared files, not runId-isolated.
- Concurrent runs are not safe.
- The UI still reads generated mock/public files.
- This is not suitable for Vercel-only deployment because the API route needs long-running process execution and writable files.
- A robust multi-user deployment still needs Phase 3: run IDs, job status/result endpoints, per-run output folders, and concurrency control.

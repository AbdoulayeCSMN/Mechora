# Mechora

**Mechanical engineering calculation prototype (FastAPI + React) for beam, shaft, key, bearing, and gear sizing workflows.**

## Table of contents
- [Overview](#overview)
- [Current capabilities (implemented)](#current-capabilities-implemented)
- [Product vision (roadmap)](#product-vision-roadmap)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Run locally (2 terminals)](#run-locally-2-terminals)
- [API documentation and health check](#api-documentation-and-health-check)
- [Build and verification commands](#build-and-verification-commands)
- [Configuration and CORS notes](#configuration-and-cors-notes)
- [Example workflow](#example-workflow)
- [Limitations and safety disclaimer](#limitations-and-safety-disclaimer)
- [Contributing](#contributing)
- [License and project status](#license-and-project-status)

## Overview
Mechora is an early-stage SaaS/prototype for mechanical design assistance. The current repository contains:
- a **Python backend** exposing a FastAPI application (`backend/api/main.py`), and
- a **Vite + React + TypeScript frontend** (`frontend/`) that calls the backend APIs.

The backend provides engineering calculations and optimization endpoints, while the frontend provides module-based UI views for the currently implemented domains.

## Current capabilities (implemented)
From the code currently in this repository:

- FastAPI app: **Mechora API** (`version 0.1.0`)
- Health endpoint: `GET /health`
- Calculation routes under `/calculate/*` and optimization routes under `/optimize/*`
- Implemented engineering domains in backend and UI:
  - Beams
  - Shafts
  - Keys
  - Bearings
  - Gears
- Backend domain modules in `backend/core` include: advisor logic, loads, materials, sections/profiles/units, beam/shaft/key/bearing/gear calculations, and optimization helpers.
- Automated backend tests exist under:
  - `backend/api/tests`
  - `backend/core/tests`

## Product vision (roadmap)
The `infos` file describes a broader long-term vision, including natural-language engineering assistance, richer standard-component intelligence, advanced optimization, educational/assistant features, reporting, and potential CAD/export flows.

**Important:** those items are vision targets; they should not be interpreted as fully implemented in the current codebase. The implemented scope is the one listed in [Current capabilities](#current-capabilities-implemented).

## Architecture

```text
Frontend (React + Vite + TypeScript)
  - UI modules: beams, shafts, keys, bearings, gears
  - API client: frontend/src/api/client.ts
  - Default API base: http://localhost:8000 (overridable via VITE_API_BASE)
            |
            v
Backend (FastAPI)
  - Entry point: backend/api/main.py
  - Routers: backend/api/routes.py
  - Schemas: backend/api/schemas.py
  - Core engineering logic: backend/core/*.py
```

## Repository structure

```text
Mechora/
├─ backend/
│  ├─ api/
│  │  ├─ main.py
│  │  ├─ routes.py
│  │  ├─ schemas.py
│  │  └─ tests/
│  ├─ core/
│  │  └─ tests/
│  └─ conftest.py
├─ frontend/
│  ├─ src/
│  │  ├─ App.tsx
│  │  ├─ api/client.ts
│  │  ├─ components/views/
│  │  └─ ...
│  ├─ package.json
│  └─ vite.config.ts
└─ infos
```

## Prerequisites
- **Python 3.10+** (recommended for FastAPI/Pydantic ecosystem)
- **Node.js 18+** and npm

## Local setup

### 1) Backend setup
> The repository currently has no `requirements.txt`/`pyproject.toml`, so dependencies must be installed manually.

From repository root (`/home/runner/work/Mechora/Mechora`):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install fastapi pydantic numpy pytest uvicorn
```

### 2) Frontend setup

```bash
cd /home/runner/work/Mechora/Mechora/frontend
npm ci
```

## Run locally (2 terminals)

### Terminal A — backend

```bash
cd /home/runner/work/Mechora/Mechora
source .venv/bin/activate
python -m uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal B — frontend

```bash
cd /home/runner/work/Mechora/Mechora/frontend
npm run dev
```

Vite is configured for `127.0.0.1:5173`, and the backend CORS list allows:
- `http://localhost:5173`
- `http://127.0.0.1:5173`

## API documentation and health check
With backend running:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

Health check example:

```bash
curl http://127.0.0.1:8000/health
# expected: {"status":"ok"}
```

## Build and verification commands

### Frontend build
```bash
cd /home/runner/work/Mechora/Mechora/frontend
npm run build
```

### Backend tests (available)
```bash
cd /home/runner/work/Mechora/Mechora/backend
python -m pytest
```

You can also run subsets:

```bash
python -m pytest api/tests
python -m pytest core/tests
```

### Frontend tests
No frontend test script is currently defined in `frontend/package.json`.

## Configuration and CORS notes
- Frontend API base is set in `frontend/src/api/client.ts`:
  - uses `VITE_API_BASE` when provided
  - falls back to `http://localhost:8000`
- Before changing environments, **check frontend source/config** instead of assuming a backend URL.
- Backend CORS is configured in `backend/api/main.py` for local Vite origins only.

## Example workflow
1. Start backend (`uvicorn`) and frontend (`npm run dev`).
2. Open the frontend in your browser (Vite local URL).
3. Choose a module (Beam/Shaft/Key/Bearing/Gear).
4. Enter input parameters and run calculation/optimization from the UI.
5. Inspect returned values and advice blocks.
6. For API-level checks, use `/docs` and `/health` directly.

## Limitations and safety disclaimer
- This project is currently a **prototype**.
- Engineering calculations may rely on assumptions, simplified models, or incomplete standards coverage.
- Results should be independently verified by qualified engineers before use in real projects, manufacturing, procurement, or safety-critical decisions.
- No production uptime, certification, or regulatory compliance guarantee is provided in this repository.

## Contributing
Contributions are welcome.

Suggested workflow:
1. Create a feature/fix branch.
2. Make focused changes.
3. Run backend tests (`python -m pytest` from `backend/`).
4. Run frontend build (`npm run build` from `frontend/`).
5. Open a pull request with context, assumptions, and test/build evidence.

## License and project status
- **License:** no license file is currently present in this repository, so licensing has not yet been specified.
- **Status:** active prototype / early-stage development.

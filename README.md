# VietPlateAI

VietPlateAI is a full-stack license plate recognition and access-control system built for secured facilities. It combines plate detection, operator-facing review tools, vehicle registry management, and an auditable detection history in one workspace.

The project is designed around two goals:

- recognize and classify license plates quickly from uploaded images or videos
- control who can register vehicles, review requests, and manage access status

## Core Features

- Plate recognition pipeline powered by YOLO, PyTorch, OpenCV, and custom OCR/classification logic
- Detection console for image and video uploads with confidence-aware review
- Role-based authentication with `ADMIN` and `OPERATOR` accounts
- Vehicle registry with `CITIZEN` and `BANNED` status management
- Plate registration request flow where users submit requests and admins approve or reject them
- Detection history with searchable audit records and saved captures
- Retraining workflow for improving the detector and OCR models from reviewed real-world errors

## Architecture

### Backend

- FastAPI application under `backend/api`
- SQLAlchemy ORM with MySQL
- JWT access token + refresh session authentication
- Static media serving for saved detection captures

### Frontend

- React + TypeScript + Vite
- React Router for protected application routes
- TanStack Query for server state
- Tailwind CSS and Radix UI components for the operator console

## User Roles

- `ADMIN`
  - manage cameras and vehicle registry
  - approve or reject plate registration requests
  - update vehicle access status
- `OPERATOR`
  - access detection console and history
  - submit plate registration requests to admins
  - view the status of their own requests

## Main Modules

- `frontend/client/pages/RecognitionConsole.tsx`: upload and inspect recognition results
- `frontend/client/pages/Vehicles.tsx`: role-based entry point for registry or request flow
- `frontend/client/pages/History.tsx`: historical detection records
- `backend/api/routers/detections.py`: detection APIs
- `backend/api/routers/vehicles.py`: vehicle registry APIs
- `backend/api/routers/vehicle_registration_requests.py`: plate registration request APIs
- `backend/training/`: retraining scripts and data preparation workflow

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- MySQL

### 1. Install backend dependencies

```powershell
cd "C:\Users\aDMIN\Documents\SS2\License Plate Recognition"
python -m pip install -r backend\requirements_api.txt
```

### 2. Configure environment

Create `backend/.env` if you want to override defaults. Common settings:

```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/license_plate_recognition
BOOTSTRAP_ADMIN_EMAIL=admin@vietplate.local
BOOTSTRAP_ADMIN_PASSWORD=your-secure-password
CORS_ORIGINS=http://127.0.0.1:8080,http://localhost:8080
JWT_SECRET_KEY=replace-this-in-real-environments
WARM_MODEL_ON_STARTUP=true
```

Frontend API base URL can be configured with:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If not set, the frontend defaults to `http://127.0.0.1:8000`.

### 3. Start the backend

```powershell
python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will:

- create database tables if needed
- warm the recognition model on startup when enabled
- create the bootstrap admin account if the user table is empty and admin credentials are configured

### 4. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

## Build and Validation

From `frontend/`:

```powershell
npm run typecheck
npm run build
```

Backend syntax validation:

```powershell
python -m compileall backend\api
```

## API Summary

Key backend routes include:

- `/auth/*`: login, signup, refresh, logout, current user
- `/detections/*`: recognition and detection history
- `/vehicles/*`: registered vehicle management
- `/vehicle-registration-requests/*`: request submission and admin approval flow
- `/cameras/*`: camera management
- `/health`: basic service health check

## Project Structure

```text
backend/
  api/          FastAPI app, models, routers, auth, CRUD
  src/          Recognition and OCR pipeline code
  training/     Dataset export and retraining scripts
  checkpoints/  Detector and classifier weights
  data/         Saved captures, outputs, and retraining assets

frontend/
  client/       React application
  server/       Server build entry for deployment
  dist/         Frontend build output
```

## Retraining Workflow

The project includes a practical retraining loop based on real failed or low-confidence detections:

1. export reviewed error captures
2. correct labels in `backend/data/retraining/error_review/manifest.csv`
3. bootstrap or refine detector labels
4. retrain the detector
5. rebuild OCR datasets and retrain classifiers

See [backend/training/README.md](backend/training/README.md) for the full workflow.

## Notes

- Vehicle classification affects future detections immediately
- Pending plate requests do not change registry state until an admin approves them
- Saved media is exposed through `/media/detections`
- Default settings are development-friendly and should be hardened before production deployment

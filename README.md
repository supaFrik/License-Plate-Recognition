# Headline Tech Stack

FastAPI, React, TypeScript, Vite, MySQL, SQLAlchemy, PyTorch, YOLO, OpenCV

# Project Name

VietPlateAI

# Short Description

VietPlateAI is a full-stack license plate recognition and vehicle access-control system. It combines AI-based plate detection, OCR/classification, operator authentication, vehicle registry management, registration request approval, and searchable detection history in one project.

# Member List

- 2301040197 - Trịnh Quốc Việt (Leader)
- 2301040179 - Trịnh Xuân Toán
- 2301040182 - Trần Đức Trí

# Tech Stack

## Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Radix UI
- TanStack Query
- React Router

## Backend

- FastAPI
- SQLAlchemy
- PyMySQL
- JWT authentication
- Argon2 password hashing
- Python dotenv

## AI / Computer Vision

- PyTorch
- TorchVision
- Ultralytics YOLO
- OpenCV
- Pillow
- NumPy

## Database

- MySQL

# Main Features

- License plate recognition from uploaded images and videos
- OCR/classification pipeline for extracting plate text
- Detection history with confidence scores and saved captures
- Role-based authentication with `ADMIN` and `OPERATOR`
- Vehicle registry management for approved vehicles
- Vehicle registration request workflow with admin approval or rejection
- Camera management for detection sources
- Bootstrap admin account creation on first startup
- Retraining workflow for improving the detector and OCR models

# Overall Project Structure

```text
License Plate Recognition/
|-- backend/
|   |-- api/                FastAPI app, routers, auth, models, CRUD, config
|   |-- src/                Recognition pipeline and OCR/classification logic
|   |-- training/           Retraining and dataset preparation scripts
|   |-- checkpoints/        Model weights
|   |-- data/               Saved media, outputs, and retraining assets
|   |-- videos/             Sample input/output videos
|   `-- .env                Backend environment file loaded by the API
|-- frontend/
|   |-- client/             React UI pages, components, hooks, and API client
|   |-- server/             Node/Express server entry for built deployment
|   |-- public/             Static assets
|   |-- dist/               Frontend build output
|   `-- .env                Frontend environment file for Vite
|-- .env.example            Example environment variables for both apps
`-- README.md
```

# Installation Steps And Required Tools

## Required Tools

- Git
- Python 3.11 or newer
- Node.js 18 or newer
- npm
- MySQL 8.x

## Clone And Open The Project

```powershell
git clone <your-repository-url>
cd "License Plate Recognition"
```

## Install Backend Dependencies

```powershell
python -m pip install -r backend\requirements_api.txt
```

## Install Frontend Dependencies

```powershell
cd frontend
npm install
cd ..
```

# Environment Variable Setup Using `.env.example`

This repository includes a root-level [.env.example](./.env.example) file.

Use it as a reference, then create:

- `backend/.env` for backend variables
- `frontend/.env` for frontend variables

Backend env file example:

```powershell
Copy-Item .env.example backend\.env
```

Frontend env file example:

```powershell
Copy-Item .env.example frontend\.env
```

After copying, keep only the relevant section in each file or leave the comments in place.

## Main Environment Variables

- `DATABASE_URL`: MySQL connection string used by the FastAPI backend
- `BOOTSTRAP_ADMIN_EMAIL`: first admin account email created when the database has no users
- `BOOTSTRAP_ADMIN_PASSWORD`: password for the bootstrap admin account
- `JWT_SECRET_KEY`: secret used to sign access tokens
- `CORS_ORIGINS`: allowed frontend origins, separated by commas
- `WARM_MODEL_ON_STARTUP`: controls whether the recognition model loads during backend startup
- `VITE_API_BASE_URL`: backend API base URL used by the frontend

# How To Run Frontend

```powershell
cd frontend
npm run dev
```

Default local frontend URL:

```text
http://127.0.0.1:8080
```

# How To Run Backend

```powershell
python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

Default local backend URL:

```text
http://127.0.0.1:8000
```

Health check:

```text
GET /health
```

# How To Set Up Or Migrate/Seed The Database

This project does not use Alembic or a separate migration tool.

Database setup flow:

1. Create a MySQL database named `license_plate_recognition`.
2. Update `DATABASE_URL` in `backend/.env`.
3. Start the backend once.
4. The backend automatically creates tables with SQLAlchemy `create_all()`.
5. If the `detections` table is older, the backend also adds missing columns on startup.
6. If there are no users and `BOOTSTRAP_ADMIN_EMAIL` plus `BOOTSTRAP_ADMIN_PASSWORD` are configured, the backend creates the first admin account automatically.

Example MySQL setup:

```sql
CREATE DATABASE license_plate_recognition;
```

# How To Run The Full System From A Clean Machine

1. Install Git, Python 3.11+, Node.js 18+, npm, and MySQL.
2. Clone the repository.
3. Create the MySQL database: `license_plate_recognition`.
4. Install backend dependencies with `python -m pip install -r backend\requirements_api.txt`.
5. Install frontend dependencies with `cd frontend` then `npm install`.
6. Use [.env.example](./.env.example) to create `backend/.env` and `frontend/.env`.
7. Set `DATABASE_URL`, `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, and `VITE_API_BASE_URL`.
8. Start the backend with `python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000`.
9. Start the frontend with `cd frontend` then `npm run dev`.
10. Open `http://127.0.0.1:8080` in the browser.
11. Sign in with the bootstrap admin account, or create a new operator account from the signup page.

# Demo Account

Login is required.

There is no hard-coded demo account in the repository.

Use one of these options:

- Bootstrap admin account from `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`
- A new operator account created through the `/signup` page

Example bootstrap admin:

```text
Email: admin@vietplate.local
Password: change-this-password
```

# Known Issues

- The backend depends on local AI model checkpoints in `backend/checkpoints`, so a clean machine must have the required weights available.
- Model warm-up on startup can make the first backend launch slow.
- Database schema changes are handled in application startup code instead of a dedicated migration system.
- The repository contains generated data and media under `backend/data`, which can make the source folder large.
- Production security hardening is still needed for secrets, CORS, cookie settings, and deployment-specific configuration.

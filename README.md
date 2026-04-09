# VietPlateAI

VietPlateAI is a console-first license plate intelligence system focused on fast
detection, secure operator access, vehicle registry control, and auditable
detection history.

## Project Warm Up

1. Install backend dependencies:

```powershell
cd "C:\Users\aDMIN\Documents\SS2\License Plate Recognition"
python -m pip install -r backend\requirements_api.txt
```

2. Start the backend API:

```powershell
python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

3. Start the frontend:

```powershell
cd frontend
npm run dev
```

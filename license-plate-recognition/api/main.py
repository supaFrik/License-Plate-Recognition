from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

try:
    from models import Base as models_Base
    import crud, models, schemas
    from database import SessionLocal, engine
except ImportError:
    from . import crud, models, schemas
    from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="License Plate Recognition API (Residential Tracker)", 
    description="API for tracking and classifying visitors as GUEST, CITIZEN, or BANNED via vehicle plates."
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Cameras ---
@app.post("/cameras/", response_model=schemas.Camera, tags=["Cameras"])
def create_camera(camera: schemas.CameraCreate, db: Session = Depends(get_db)):
    return crud.create_camera(db=db, camera=camera)

@app.get("/cameras/", response_model=List[schemas.Camera], tags=["Cameras"])
def read_cameras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_cameras(db, skip=skip, limit=limit)

@app.delete("/cameras/{camera_id}", response_model=schemas.Camera, tags=["Cameras"])
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = crud.delete_camera(db, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

# --- Registered Vehicles ---
@app.post("/vehicles/", response_model=schemas.RegisteredVehicle, tags=["Vehicles"])
def register_vehicle(vehicle: schemas.RegisteredVehicleCreate, db: Session = Depends(get_db)):
    db_vehicle = crud.get_vehicle_by_plate(db, plate_number=vehicle.plate_number)
    if db_vehicle:
        raise HTTPException(status_code=400, detail="Vehicle is already registered")
    return crud.create_registered_vehicle(db=db, vehicle=vehicle)

@app.get("/vehicles/", response_model=List[schemas.RegisteredVehicle], tags=["Vehicles"])
def read_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_vehicles(db, skip=skip, limit=limit)

@app.delete("/vehicles/{plate_number}", response_model=schemas.RegisteredVehicle, tags=["Vehicles"])
def delete_vehicle(plate_number: str, db: Session = Depends(get_db)):
    vehicle = crud.delete_registered_vehicle(db, plate_number)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

# --- Detections ---
@app.post("/detections/", response_model=schemas.Detection, tags=["Detections"])
def create_detection(detection: schemas.DetectionCreate, db: Session = Depends(get_db)):
    """
    Simulates a license plate detected by a camera.
    The system will automatically classify GUEST, CITIZEN, or BANNED based on the currently registered vehicles.
    """
    db_camera = crud.get_camera(db, camera_id=detection.camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found in the database. Register the camera first.")
    return crud.create_detection(db=db, detection=detection)

@app.get("/detections/", response_model=List[schemas.Detection], tags=["Detections"])
def read_detections(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_detections(db, skip=skip, limit=limit)
    
@app.delete("/detections/{detection_id}", response_model=schemas.Detection, tags=["Detections"])
def delete_detection(detection_id: int, db: Session = Depends(get_db)):
    detection = crud.delete_detection(db, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    return detection

@app.post("/detections/recalculate-types", tags=["Detections"])
def recalculate_detection_types(camera_id: int = None, db: Session = Depends(get_db)):
    """
    Recalculate visitor types for all detections based on current registered vehicles.
    Useful when vehicle statuses change after detections are recorded.
    
    Args:
        camera_id: Optional camera ID to recalculate for specific camera
    
    Returns:
        Statistics about recalculated detections
    """
    return crud.recalculate_detection_types(db, camera_id=camera_id)

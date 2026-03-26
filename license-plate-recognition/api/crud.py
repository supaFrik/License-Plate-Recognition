from sqlalchemy.orm import Session

# Import modules - handle both package and direct import scenarios
try:
    import models, schemas
except ImportError:
    from . import models, schemas

# --- Camera CRUD ---
def get_camera(db: Session, camera_id: int):
    return db.query(models.Camera).filter(models.Camera.id == camera_id).first()

def get_cameras(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Camera).offset(skip).limit(limit).all()

def create_camera(db: Session, camera: schemas.CameraCreate):
    db_camera = models.Camera(**camera.model_dump())
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera

def delete_camera(db: Session, camera_id: int):
    camera = get_camera(db, camera_id)
    if camera:
        db.delete(camera)
        db.commit()
    return camera

# --- RegisteredVehicle CRUD ---
def get_vehicle_by_plate(db: Session, plate_number: str):
    return db.query(models.RegisteredVehicle).filter(models.RegisteredVehicle.plate_number == plate_number).first()

def get_vehicles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.RegisteredVehicle).offset(skip).limit(limit).all()

def create_registered_vehicle(db: Session, vehicle: schemas.RegisteredVehicleCreate):
    db_vehicle = models.RegisteredVehicle(**vehicle.model_dump())
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

def update_registered_vehicle_status(db: Session, plate_number: str, status: models.VehicleStatus):
    vehicle = get_vehicle_by_plate(db, plate_number)
    if vehicle:
        vehicle.status = status
        db.commit()
        db.refresh(vehicle)
    return vehicle

def delete_registered_vehicle(db: Session, plate_number: str):
    vehicle = get_vehicle_by_plate(db, plate_number)
    if vehicle:
        db.delete(vehicle)
        db.commit()
    return vehicle

# --- Detection CRUD ---
def get_detections(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Detection).order_by(models.Detection.timestamp.desc()).offset(skip).limit(limit).all()

def create_detection(db: Session, detection: schemas.DetectionCreate):
    # Determine VisitorType for the Residential Building based on plate_number
    vehicle = get_vehicle_by_plate(db, detection.plate_number)
    if vehicle:
        # Convert enum to string for comparison to handle both enum and string values
        vehicle_status_str = vehicle.status.value if hasattr(vehicle.status, 'value') else str(vehicle.status)
        if vehicle_status_str == models.VehicleStatus.CITIZEN.value:
            visitor_type = models.VisitorType.CITIZEN
        else:
            visitor_type = models.VisitorType.BANNED
    else:
        visitor_type = models.VisitorType.GUEST
        
    db_detection = models.Detection(
        camera_id=detection.camera_id,
        plate_number=detection.plate_number,
        confidence=detection.confidence,
        visitor_type=visitor_type
    )
    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)
    return db_detection

def delete_detection(db: Session, detection_id: int):
    detection = db.query(models.Detection).filter(models.Detection.id == detection_id).first()
    if detection:
        db.delete(detection)
        db.commit()
    return detection

def recalculate_detection_types(db: Session, camera_id: int = None):
    """
    Recalculate visitor types for all detections based on current registered vehicles.
    Useful when vehicle statuses are changed after detections are recorded.
    
    Args:
        db: Database session
        camera_id: Optional camera ID to recalculate for specific camera only
    
    Returns:
        dict with updated counts
    """
    query = db.query(models.Detection)
    if camera_id:
        query = query.filter(models.Detection.camera_id == camera_id)
    
    detections = query.all()
    updated_count = 0
    
    for detection in detections:
        vehicle = get_vehicle_by_plate(db, detection.plate_number)
        
        if vehicle:
            vehicle_status_str = vehicle.status.value if hasattr(vehicle.status, 'value') else str(vehicle.status)
            if vehicle_status_str == models.VehicleStatus.CITIZEN.value:
                new_type = models.VisitorType.CITIZEN
            else:
                new_type = models.VisitorType.BANNED
        else:
            new_type = models.VisitorType.GUEST
        
        if detection.visitor_type != new_type:
            detection.visitor_type = new_type
            updated_count += 1
    
    if updated_count > 0:
        db.commit()
    
    return {
        "total_detections": len(detections),
        "updated_count": updated_count,
        "camera_id": camera_id
    }

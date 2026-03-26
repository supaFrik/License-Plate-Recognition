from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Import models - handle both package and direct import scenarios
try:
    from models import VehicleStatus, VisitorType
except ImportError:
    from .models import VehicleStatus, VisitorType

# --- Camera Schemas ---
class CameraBase(BaseModel):
    location_name: Optional[str] = "CT11, Kim Van Kim Lu"
    status: Optional[str] = "active"

class CameraCreate(CameraBase):
    pass

class Camera(CameraBase):
    id: int
    
    class Config:
        from_attributes = True

# --- Registered Vehicle Schemas ---
class RegisteredVehicleBase(BaseModel):
    plate_number: str
    owner_name: str
    status: VehicleStatus = VehicleStatus.CITIZEN

class RegisteredVehicleCreate(RegisteredVehicleBase):
    pass

class RegisteredVehicle(RegisteredVehicleBase):
    id: int
    
    class Config:
        from_attributes = True

# --- Detection Schemas ---
class DetectionBase(BaseModel):
    camera_id: int
    plate_number: str
    confidence: float

class DetectionCreate(DetectionBase):
    pass

class Detection(DetectionBase):
    id: int
    visitor_type: VisitorType
    timestamp: datetime
    
    class Config:
        from_attributes = True

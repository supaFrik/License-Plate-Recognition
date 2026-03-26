from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

# Import Base - handle both package and direct import scenarios
try:
    from database import Base
except ImportError:
    from .database import Base

class VehicleStatus(str, enum.Enum):
    CITIZEN = "CITIZEN"
    BANNED = "BANNED"

class VisitorType(str, enum.Enum):
    GUEST = "GUEST"
    CITIZEN = "CITIZEN"
    BANNED = "BANNED"

class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(255), default="CT11, Kim Van Kim Lu")
    status = Column(String(50), default="active")
    
    detections = relationship("Detection", back_populates="camera")

class RegisteredVehicle(Base):
    __tablename__ = "registered_vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(50), unique=True, index=True)
    owner_name = Column(String(100))
    status = Column(Enum(VehicleStatus), default=VehicleStatus.CITIZEN)

class Detection(Base):
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    plate_number = Column(String(50), index=True)
    confidence = Column(Float)
    visitor_type = Column(Enum(VisitorType))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    camera = relationship("Camera", back_populates="detections")

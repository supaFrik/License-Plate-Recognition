from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

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


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(255), default="Default Camera", nullable=False)
    status = Column(String(50), default="active", nullable=False)

    detections = relationship("Detection", back_populates="camera")


class RegisteredVehicle(Base):
    __tablename__ = "registered_vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(50), unique=True, index=True, nullable=False)
    owner_name = Column(String(100), nullable=False)
    status = Column(Enum(VehicleStatus), default=VehicleStatus.CITIZEN, nullable=False)


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    plate_number = Column(String(50), index=True, nullable=False)
    confidence = Column(Float, nullable=False)
    visitor_type = Column(Enum(VisitorType), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    camera = relationship("Camera", back_populates="detections")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.OPERATOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    refresh_sessions = relationship(
        "RefreshTokenSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RefreshTokenSession(Base):
    __tablename__ = "refresh_token_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)

    user = relationship("User", back_populates="refresh_sessions")


Index("ix_detections_timestamp", Detection.timestamp)
Index("ix_detections_camera_timestamp", Detection.camera_id, Detection.timestamp)
Index("ix_detections_visitor_timestamp", Detection.visitor_type, Detection.timestamp)

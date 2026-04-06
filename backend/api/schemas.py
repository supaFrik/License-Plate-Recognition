from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

try:
    from models import UserRole, VehicleStatus, VisitorType
except ImportError:
    from .models import UserRole, VehicleStatus, VisitorType


class CameraBase(BaseModel):
    location_name: str = "Default Camera"
    status: str = "active"


class CameraCreate(CameraBase):
    pass


class Camera(CameraBase):
    id: int

    class Config:
        from_attributes = True


class CameraListResponse(BaseModel):
    items: list[Camera]


class RegisteredVehicleBase(BaseModel):
    plate_number: str
    owner_name: str
    status: VehicleStatus = VehicleStatus.CITIZEN


class RegisteredVehicleCreate(RegisteredVehicleBase):
    pass


class RegisteredVehicleUpdate(BaseModel):
    owner_name: Optional[str] = None
    status: Optional[VehicleStatus] = None


class RegisteredVehicle(BaseModel):
    id: int
    plate_number: str
    owner_name: str
    status: VehicleStatus

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int


class VehicleListResponse(BaseModel):
    items: list[RegisteredVehicle]
    pagination: PaginationMeta


class DetectionBase(BaseModel):
    camera_id: int
    plate_number: str
    confidence: float


class DetectionCreate(DetectionBase):
    pass


class Detection(BaseModel):
    id: int
    camera_id: int
    camera_name: str
    plate_number: str
    confidence: float
    visitor_type: VisitorType
    timestamp: datetime

    class Config:
        from_attributes = True


class DetectionListResponse(BaseModel):
    items: list[Detection]
    pagination: PaginationMeta


class DetectionLiveResponse(BaseModel):
    items: list[Detection]
    latest_id: int


class PlateBoundingBox(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class DetectionRecognizeResponse(BaseModel):
    filename: str
    content_type: str | None = None
    input_kind: str = "image"
    detected: bool
    plate_number: str | None = None
    confidence: float | None = None
    plate_type: str | None = None
    bbox: PlateBoundingBox | None = None
    image_width: int
    image_height: int
    sampled_frames: int = 1
    analyzed_frames: int = 1
    selected_frame_index: int | None = None
    validation_note: str | None = None
    processing_ms: float
    saved_to_db: bool
    detection: Detection | None = None


class DetectionTypeRecalculation(BaseModel):
    total_detections: int
    updated_count: int
    camera_id: int | None = None


class AuthUser(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class UserCreate(BaseModel):
    email: EmailStr
    password_hash: str
    role: UserRole = UserRole.OPERATOR


class RefreshSessionCreate(BaseModel):
    user_id: int
    token_hash: str
    expires_at: datetime
    user_agent: str | None = None
    ip_address: str | None = None

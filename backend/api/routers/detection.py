from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from .detections import recognize_and_save_detection


router = APIRouter(prefix="/detection", tags=["Detection Compatibility"])


@router.post("", response_model=schemas.DetectionRecognizeResponse)
async def detect_plate(
    file: UploadFile = File(...),
    camera_id: int | None = Form(None),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return await recognize_and_save_detection(file=file, camera_id=camera_id, db=db)

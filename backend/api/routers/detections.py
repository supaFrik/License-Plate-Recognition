from datetime import datetime
from time import perf_counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

try:
    import crud, models, schemas
    from auth import get_current_user, require_admin
    from database import get_db
    from recognition import detect_plate_in_image, detect_plate_in_video
except ImportError:
    from .. import crud, models, schemas
    from ..auth import get_current_user, require_admin
    from ..database import get_db
    from ..recognition import detect_plate_in_image, detect_plate_in_video


router = APIRouter(prefix="/detections", tags=["Detections"])
DEFAULT_CAMERA_LOCATION = "VietPlateAI Upload Console"


def get_or_create_default_camera(db: Session) -> models.Camera:
    camera = crud.get_camera_by_location(db, DEFAULT_CAMERA_LOCATION)
    if camera:
        return camera
    return crud.create_camera(
        db,
        schemas.CameraCreate(location_name=DEFAULT_CAMERA_LOCATION, status="active"),
    )


def serialize_detection(detection: models.Detection) -> schemas.Detection:
    camera_name = detection.camera.location_name if detection.camera else "Unknown Camera"
    return schemas.Detection(
        id=detection.id,
        camera_id=detection.camera_id,
        camera_name=camera_name,
        plate_number=detection.plate_number,
        confidence=detection.confidence,
        visitor_type=detection.visitor_type,
        timestamp=detection.timestamp,
    )


async def recognize_and_save_detection(
    *,
    file: UploadFile,
    camera_id: int | None,
    db: Session,
) -> schemas.DetectionRecognizeResponse:
    content_type = file.content_type or ""
    if not (
        content_type.startswith("image/") or content_type.startswith("video/")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please upload an image or video file.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    started_at = perf_counter()
    try:
        if content_type.startswith("video/"):
            result = detect_plate_in_video(file_bytes, file.filename)
        else:
            result = detect_plate_in_image(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Detection failed: {exc}") from exc
    processing_ms = round((perf_counter() - started_at) * 1000, 2)

    saved_detection = None
    if result["detected"]:
        camera = get_or_create_default_camera(db) if camera_id is None else crud.get_camera(db, camera_id)
        if camera is None:
            raise HTTPException(status_code=404, detail="Camera not found.")
        db_detection = crud.create_detection(
            db,
            schemas.DetectionCreate(
                camera_id=camera.id,
                plate_number=result["plate_number"],
                confidence=result["confidence"],
            ),
        )
        saved_detection = serialize_detection(crud.get_detection(db, db_detection.id))

    return schemas.DetectionRecognizeResponse(
        filename=file.filename or "uploaded-image",
        content_type=file.content_type,
        input_kind=result["input_kind"],
        detected=result["detected"],
        plate_number=result["plate_number"],
        confidence=result["confidence"],
        plate_type=result["plate_type"],
        bbox=(
            schemas.PlateBoundingBox(**result["bbox"])
            if result["bbox"] is not None
            else None
        ),
        image_width=result["image_width"],
        image_height=result["image_height"],
        sampled_frames=result["sampled_frames"],
        analyzed_frames=result["analyzed_frames"],
        selected_frame_index=result["selected_frame_index"],
        validation_note=result["validation_note"],
        processing_ms=processing_ms,
        saved_to_db=saved_detection is not None,
        detection=saved_detection,
    )


@router.post("/recognize", response_model=schemas.DetectionRecognizeResponse)
async def recognize_detection(
    file: UploadFile = File(...),
    camera_id: int | None = Form(None),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return await recognize_and_save_detection(file=file, camera_id=camera_id, db=db)


@router.get("", response_model=schemas.DetectionListResponse)
def read_detections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    plate: str | None = None,
    visitor_type: models.VisitorType | None = None,
    camera_id: int | None = None,
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    items, total = crud.list_detections(
        db,
        page=page,
        page_size=page_size,
        plate=plate,
        visitor_type=visitor_type,
        camera_id=camera_id,
        date_from=date_from,
        date_to=date_to,
    )
    return schemas.DetectionListResponse(
        items=[serialize_detection(item) for item in items],
        pagination=schemas.PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/live", response_model=schemas.DetectionLiveResponse)
def read_live_detections(
    after_id: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    items, latest_id = crud.list_live_detections(db, after_id=after_id, limit=limit)
    return schemas.DetectionLiveResponse(
        items=[serialize_detection(item) for item in items],
        latest_id=latest_id,
    )


@router.post("/recalculate-types", response_model=schemas.DetectionTypeRecalculation)
def recalculate_detection_types(
    camera_id: int | None = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    return crud.recalculate_detection_types(db, camera_id=camera_id)

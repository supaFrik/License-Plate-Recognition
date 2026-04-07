import logging

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

try:
    import crud, models, schemas
    from auth import ensure_bootstrap_admin, get_current_user, require_admin, warm_detection_model
    from config import get_settings
    from database import engine, get_db
    from media import MEDIA_ROOT
    from routers.auth import router as auth_router
    from routers.detection import router as detection_compat_router
    from routers.detections import router as detections_router
    from routers.vehicles import router as vehicles_router
except ImportError:
    from . import crud, models, schemas
    from .auth import ensure_bootstrap_admin, get_current_user, require_admin, warm_detection_model
    from .config import get_settings
    from .database import engine, get_db
    from .media import MEDIA_ROOT
    from .routers.auth import router as auth_router
    from .routers.detection import router as detection_compat_router
    from .routers.detections import router as detections_router
    from .routers.vehicles import router as vehicles_router


logging.basicConfig(level=logging.INFO)
settings = get_settings()


def ensure_detection_columns() -> None:
    inspector = inspect(engine)
    if "detections" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("detections")}
    with engine.begin() as connection:
        if "input_kind" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE detections "
                    "ADD COLUMN input_kind VARCHAR(20) NOT NULL DEFAULT 'image'"
                )
            )
        if "capture_path" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE detections "
                    "ADD COLUMN capture_path VARCHAR(512) NULL"
                )
            )
        if "detector_confidence" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE detections "
                    "ADD COLUMN detector_confidence FLOAT NULL"
                )
            )
        if "ocr_confidence" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE detections "
                    "ADD COLUMN ocr_confidence FLOAT NULL"
                )
            )


ensure_detection_columns()
models.Base.metadata.create_all(bind=engine)

for table in models.Base.metadata.tables.values():
    for index in table.indexes:
        index.create(bind=engine, checkfirst=True)

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(vehicles_router)
app.include_router(detections_router)
app.include_router(detection_compat_router)
app.mount("/media/detections", StaticFiles(directory=MEDIA_ROOT), name="detection-media")


@app.on_event("startup")
def startup() -> None:
    ensure_bootstrap_admin()
    warm_detection_model()


@app.get("/cameras", response_model=schemas.CameraListResponse, tags=["Cameras"])
def read_cameras(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return schemas.CameraListResponse(
        items=[schemas.Camera.model_validate(camera) for camera in crud.get_cameras(db)]
    )


@app.post("/cameras", response_model=schemas.Camera, tags=["Cameras"], status_code=status.HTTP_201_CREATED)
def create_camera(
    camera: schemas.CameraCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    return crud.create_camera(db=db, camera=camera)


@app.delete("/cameras/{camera_id}", response_model=schemas.Camera, tags=["Cameras"])
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    camera = crud.delete_camera(db, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found.")
    return camera


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "VietPlateAI"}

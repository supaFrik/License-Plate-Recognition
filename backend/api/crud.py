from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from . import models, schemas


def _paginate(query, page: int, page_size: int):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def _normalize_plate_number(plate_number: str) -> str:
    return plate_number.strip().upper()


def get_camera(db: Session, camera_id: int):
    return db.query(models.Camera).filter(models.Camera.id == camera_id).first()


def get_camera_by_location(db: Session, location_name: str):
    return (
        db.query(models.Camera)
        .filter(models.Camera.location_name == location_name)
        .first()
    )


def get_cameras(db: Session):
    return db.query(models.Camera).order_by(models.Camera.location_name.asc()).all()


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


def get_vehicle_by_plate(db: Session, plate_number: str):
    normalized = _normalize_plate_number(plate_number)
    return (
        db.query(models.RegisteredVehicle)
        .filter(models.RegisteredVehicle.plate_number == normalized)
        .first()
    )


def get_vehicle_by_id(db: Session, vehicle_id: int):
    return (
        db.query(models.RegisteredVehicle)
        .filter(models.RegisteredVehicle.id == vehicle_id)
        .first()
    )


def list_vehicles(
    db: Session,
    *,
    page: int,
    page_size: int,
    query: str | None = None,
    status: models.VehicleStatus | None = None,
):
    vehicle_query = db.query(models.RegisteredVehicle)
    if query:
        stripped_query = query.strip()
        like_query = f"%{stripped_query.upper()}%"
        vehicle_query = vehicle_query.filter(
            models.RegisteredVehicle.plate_number.ilike(like_query)
            | models.RegisteredVehicle.owner_name.ilike(f"%{stripped_query}%")
        )
    if status:
        vehicle_query = vehicle_query.filter(models.RegisteredVehicle.status == status)
    vehicle_query = vehicle_query.order_by(models.RegisteredVehicle.plate_number.asc())
    return _paginate(vehicle_query, page, page_size)


def create_registered_vehicle(db: Session, vehicle: schemas.RegisteredVehicleCreate):
    payload = vehicle.model_dump()
    payload["plate_number"] = _normalize_plate_number(payload["plate_number"])
    payload["owner_name"] = payload["owner_name"].strip()
    db_vehicle = models.RegisteredVehicle(**payload)
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle


def update_registered_vehicle(
    db: Session,
    db_vehicle: models.RegisteredVehicle,
    vehicle: schemas.RegisteredVehicleUpdate,
):
    if vehicle.owner_name is not None:
        db_vehicle.owner_name = vehicle.owner_name.strip()
    if vehicle.status is not None:
        db_vehicle.status = vehicle.status
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle


def update_registered_vehicle_status(
    db: Session,
    plate_number: str,
    status: models.VehicleStatus,
):
    vehicle = get_vehicle_by_plate(db, plate_number)
    if vehicle:
        vehicle.status = status
        db.commit()
        db.refresh(vehicle)
    return vehicle


def delete_registered_vehicle(
    db: Session,
    plate_number: str | None = None,
    vehicle_id: int | None = None,
):
    vehicle = None
    if vehicle_id is not None:
        vehicle = get_vehicle_by_id(db, vehicle_id)
    elif plate_number is not None:
        vehicle = get_vehicle_by_plate(db, plate_number)
    if vehicle:
        db.delete(vehicle)
        db.commit()
    return vehicle


def get_vehicle_registration_request_by_id(db: Session, request_id: int):
    return (
        db.query(models.VehicleRegistrationRequest)
        .options(
            joinedload(models.VehicleRegistrationRequest.requester),
            joinedload(models.VehicleRegistrationRequest.reviewer),
        )
        .filter(models.VehicleRegistrationRequest.id == request_id)
        .first()
    )


def get_pending_vehicle_registration_request_by_plate(db: Session, plate_number: str):
    normalized = _normalize_plate_number(plate_number)
    return (
        db.query(models.VehicleRegistrationRequest)
        .filter(
            models.VehicleRegistrationRequest.plate_number == normalized,
            models.VehicleRegistrationRequest.status
            == models.VehicleRegistrationRequestStatus.PENDING,
        )
        .first()
    )


def list_vehicle_registration_requests(
    db: Session,
    *,
    current_user: models.User,
    status: models.VehicleRegistrationRequestStatus | None = None,
):
    query = db.query(models.VehicleRegistrationRequest).options(
        joinedload(models.VehicleRegistrationRequest.requester),
        joinedload(models.VehicleRegistrationRequest.reviewer),
    )
    if current_user.role != models.UserRole.ADMIN:
        query = query.filter(
            models.VehicleRegistrationRequest.requester_user_id == current_user.id
        )
    if status is not None:
        query = query.filter(models.VehicleRegistrationRequest.status == status)
    return query.order_by(
        models.VehicleRegistrationRequest.created_at.desc(),
        models.VehicleRegistrationRequest.id.desc(),
    ).all()


def create_vehicle_registration_request(
    db: Session,
    payload: schemas.VehicleRegistrationRequestCreate,
    requester: models.User,
):
    db_request = models.VehicleRegistrationRequest(
        requester_user_id=requester.id,
        plate_number=_normalize_plate_number(payload.plate_number),
        owner_name=payload.owner_name.strip(),
        note=payload.note.strip() if payload.note else None,
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return get_vehicle_registration_request_by_id(db, db_request.id)


def approve_vehicle_registration_request(
    db: Session,
    db_request: models.VehicleRegistrationRequest,
    reviewer: models.User,
    *,
    admin_note: str | None = None,
):
    normalized_plate = _normalize_plate_number(db_request.plate_number)
    existing_vehicle = get_vehicle_by_plate(db, normalized_plate)
    if existing_vehicle is not None:
        return None

    db_vehicle = models.RegisteredVehicle(
        plate_number=normalized_plate,
        owner_name=db_request.owner_name.strip(),
        status=models.VehicleStatus.CITIZEN,
    )
    db.add(db_vehicle)
    db.flush()

    db_request.status = models.VehicleRegistrationRequestStatus.APPROVED
    db_request.reviewed_by_user_id = reviewer.id
    db_request.reviewed_at = datetime.utcnow()
    db_request.admin_note = admin_note.strip() if admin_note else None
    db_request.plate_number = normalized_plate
    db_request.owner_name = db_request.owner_name.strip()

    db.commit()
    return get_vehicle_registration_request_by_id(db, db_request.id)


def reject_vehicle_registration_request(
    db: Session,
    db_request: models.VehicleRegistrationRequest,
    reviewer: models.User,
    *,
    admin_note: str | None = None,
):
    db_request.status = models.VehicleRegistrationRequestStatus.REJECTED
    db_request.reviewed_by_user_id = reviewer.id
    db_request.reviewed_at = datetime.utcnow()
    db_request.admin_note = admin_note.strip() if admin_note else None

    db.commit()
    return get_vehicle_registration_request_by_id(db, db_request.id)


def _resolve_visitor_type(
    db: Session,
    plate_number: str,
) -> models.VisitorType:
    vehicle = get_vehicle_by_plate(db, plate_number)
    if vehicle is None:
        return models.VisitorType.GUEST

    vehicle_status = (
        vehicle.status.value if hasattr(vehicle.status, "value") else str(vehicle.status)
    )
    if vehicle_status == models.VehicleStatus.CITIZEN.value:
        return models.VisitorType.CITIZEN
    return models.VisitorType.BANNED


def create_detection(db: Session, detection: schemas.DetectionCreate):
    plate_number = _normalize_plate_number(detection.plate_number)
    visitor_type = _resolve_visitor_type(db, plate_number)
    db_detection = models.Detection(
        camera_id=detection.camera_id,
        plate_number=plate_number,
        confidence=detection.confidence,
        detector_confidence=detection.detector_confidence,
        ocr_confidence=detection.ocr_confidence,
        visitor_type=visitor_type,
        input_kind=detection.input_kind,
        capture_path=detection.capture_path,
    )
    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)
    return db_detection


def get_detection(db: Session, detection_id: int):
    return (
        db.query(models.Detection)
        .options(joinedload(models.Detection.camera))
        .filter(models.Detection.id == detection_id)
        .first()
    )


def list_detections(
    db: Session,
    *,
    page: int,
    page_size: int,
    plate: str | None = None,
    visitor_type: models.VisitorType | None = None,
    camera_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    detection_query = db.query(models.Detection).options(joinedload(models.Detection.camera))
    if plate:
        detection_query = detection_query.filter(
            models.Detection.plate_number.ilike(f"%{plate.strip().upper()}%")
        )
    if visitor_type:
        detection_query = detection_query.filter(models.Detection.visitor_type == visitor_type)
    if camera_id is not None:
        detection_query = detection_query.filter(models.Detection.camera_id == camera_id)
    if date_from is not None:
        detection_query = detection_query.filter(models.Detection.timestamp >= date_from)
    if date_to is not None:
        detection_query = detection_query.filter(models.Detection.timestamp <= date_to)

    detection_query = detection_query.order_by(
        models.Detection.timestamp.desc(),
        models.Detection.id.desc(),
    )
    return _paginate(detection_query, page, page_size)


def list_live_detections(db: Session, *, after_id: int = 0, limit: int = 20):
    limit = min(max(limit, 1), 50)
    query = db.query(models.Detection).options(joinedload(models.Detection.camera))
    if after_id > 0:
        detections = (
            query.filter(models.Detection.id > after_id)
            .order_by(models.Detection.id.asc())
            .limit(limit)
            .all()
        )
    else:
        detections = list(
            reversed(
                query.order_by(models.Detection.id.desc()).limit(limit).all()
            )
        )
    latest_id = after_id
    if detections:
        latest_id = detections[-1].id
    return detections, latest_id


def delete_detection(db: Session, detection_id: int):
    detection = db.query(models.Detection).filter(models.Detection.id == detection_id).first()
    if detection:
        db.delete(detection)
        db.commit()
    return detection


def recalculate_detection_types(db: Session, camera_id: int | None = None):
    query = db.query(models.Detection)
    if camera_id is not None:
        query = query.filter(models.Detection.camera_id == camera_id)

    detections = query.all()
    updated_count = 0
    for detection in detections:
        new_type = _resolve_visitor_type(db, detection.plate_number)
        if detection.visitor_type != new_type:
            detection.visitor_type = new_type
            updated_count += 1

    if updated_count:
        db.commit()

    return {
        "total_detections": len(detections),
        "updated_count": updated_count,
        "camera_id": camera_id,
    }


def get_user_by_email(db: Session, email: str):
    normalized = email.strip().lower()
    return db.query(models.User).filter(models.User.email == normalized).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def count_users(db: Session) -> int:
    return db.query(models.User).count()


def create_user(db: Session, user: schemas.UserCreate):
    payload = user.model_dump()
    payload["email"] = payload["email"].strip().lower()
    db_user = models.User(**payload)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_last_login(db: Session, user: models.User):
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def create_refresh_session(db: Session, session: schemas.RefreshSessionCreate):
    db_session = models.RefreshTokenSession(**session.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_refresh_session_by_hash(db: Session, token_hash: str):
    return (
        db.query(models.RefreshTokenSession)
        .options(joinedload(models.RefreshTokenSession.user))
        .filter(models.RefreshTokenSession.token_hash == token_hash)
        .first()
    )


def revoke_refresh_session(db: Session, session_id: int):
    session = (
        db.query(models.RefreshTokenSession)
        .filter(models.RefreshTokenSession.id == session_id)
        .first()
    )
    if session and session.revoked_at is None:
        session.revoked_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
    return session

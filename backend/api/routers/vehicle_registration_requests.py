from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user, require_admin
from ..database import get_db


router = APIRouter(
    prefix="/vehicle-registration-requests",
    tags=["Vehicle Registration Requests"],
)


def _build_request_response(
    db_request: models.VehicleRegistrationRequest,
) -> schemas.VehicleRegistrationRequest:
    return schemas.VehicleRegistrationRequest(
        id=db_request.id,
        plate_number=db_request.plate_number,
        owner_name=db_request.owner_name,
        note=db_request.note,
        admin_note=db_request.admin_note,
        status=db_request.status,
        requester_user_id=db_request.requester_user_id,
        requester_email=db_request.requester.email if db_request.requester else "",
        reviewed_by_user_id=db_request.reviewed_by_user_id,
        reviewed_by_email=db_request.reviewer.email if db_request.reviewer else None,
        created_at=db_request.created_at,
        reviewed_at=db_request.reviewed_at,
    )


@router.get("", response_model=schemas.VehicleRegistrationRequestListResponse)
def read_vehicle_registration_requests(
    status: models.VehicleRegistrationRequestStatus | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    items = crud.list_vehicle_registration_requests(
        db,
        current_user=current_user,
        status=status,
    )
    return schemas.VehicleRegistrationRequestListResponse(
        items=[_build_request_response(item) for item in items]
    )


@router.post(
    "",
    response_model=schemas.VehicleRegistrationRequest,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle_registration_request(
    payload: schemas.VehicleRegistrationRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    existing_vehicle = crud.get_vehicle_by_plate(db, payload.plate_number)
    if existing_vehicle is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle is already registered.",
        )

    pending_request = crud.get_pending_vehicle_registration_request_by_plate(
        db, payload.plate_number
    )
    if pending_request is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending registration request already exists for this plate.",
        )

    db_request = crud.create_vehicle_registration_request(db, payload, current_user)
    return _build_request_response(db_request)


@router.post("/{request_id}/approve", response_model=schemas.VehicleRegistrationRequest)
def approve_vehicle_registration_request(
    request_id: int,
    payload: schemas.VehicleRegistrationRequestReview | None = None,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    db_request = crud.get_vehicle_registration_request_by_id(db, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration request not found.",
        )
    if db_request.status != models.VehicleRegistrationRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be approved.",
        )

    approved_request = crud.approve_vehicle_registration_request(
        db,
        db_request,
        admin,
        admin_note=payload.admin_note if payload else None,
    )
    if approved_request is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle is already registered.",
        )

    return _build_request_response(approved_request)


@router.post("/{request_id}/reject", response_model=schemas.VehicleRegistrationRequest)
def reject_vehicle_registration_request(
    request_id: int,
    payload: schemas.VehicleRegistrationRequestReview | None = None,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    db_request = crud.get_vehicle_registration_request_by_id(db, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration request not found.",
        )
    if db_request.status != models.VehicleRegistrationRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be rejected.",
        )

    rejected_request = crud.reject_vehicle_registration_request(
        db,
        db_request,
        admin,
        admin_note=payload.admin_note if payload else None,
    )
    return _build_request_response(rejected_request)

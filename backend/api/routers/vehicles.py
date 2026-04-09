from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user, require_admin
from ..database import get_db


router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("", response_model=schemas.VehicleListResponse)
def read_vehicles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    query: str | None = None,
    status: models.VehicleStatus | None = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    items, total = crud.list_vehicles(
        db,
        page=page,
        page_size=page_size,
        query=query,
        status=status,
    )
    return schemas.VehicleListResponse(
        items=[schemas.RegisteredVehicle.model_validate(item) for item in items],
        pagination=schemas.PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.post("", response_model=schemas.RegisteredVehicle, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: schemas.RegisteredVehicleCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    existing_vehicle = crud.get_vehicle_by_plate(db, payload.plate_number)
    if existing_vehicle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle is already registered.",
        )
    return crud.create_registered_vehicle(db, payload)


@router.patch("/{vehicle_id}", response_model=schemas.RegisteredVehicle)
def update_vehicle(
    vehicle_id: int,
    payload: schemas.RegisteredVehicleUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    vehicle = crud.get_vehicle_by_id(db, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found.")
    return crud.update_registered_vehicle(db, vehicle, payload)


@router.delete("/{vehicle_id}", response_model=schemas.RegisteredVehicle)
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    vehicle = crud.delete_registered_vehicle(db, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found.")
    return vehicle

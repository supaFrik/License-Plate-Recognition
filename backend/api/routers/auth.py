from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

try:
    import crud, schemas
    from auth import (
        auth_rate_limiter,
        authenticate_user,
        build_auth_response,
        clear_refresh_cookie,
        get_current_user,
        register_operator_user,
    )
    from config import get_settings
    from database import get_db
    from security import hash_refresh_token
except ImportError:
    from .. import crud, schemas
    from ..auth import (
        auth_rate_limiter,
        authenticate_user,
        build_auth_response,
        clear_refresh_cookie,
        get_current_user,
        register_operator_user,
    )
    from ..config import get_settings
    from ..database import get_db
    from ..security import hash_refresh_token


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: schemas.RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(auth_rate_limiter),
):
    user = register_operator_user(
        db,
        email=payload.email,
        password=payload.password,
    )
    return build_auth_response(
        db=db,
        user=user,
        request=request,
        response=response,
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    payload: schemas.LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(auth_rate_limiter),
):
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    crud.update_user_last_login(db, user)
    return build_auth_response(
        db=db,
        user=user,
        request=request,
        response=response,
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(auth_rate_limiter),
):
    settings = get_settings()
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing.",
        )

    session = crud.get_refresh_session_by_hash(db, hash_refresh_token(refresh_token))
    if session is None or session.user is None:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid.",
        )

    if session.revoked_at is not None or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired.",
        )

    if not session.user.is_active:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
        )

    return build_auth_response(
        db=db,
        user=session.user,
        request=request,
        response=response,
        revoke_session_id=session.id,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token:
        session = crud.get_refresh_session_by_hash(db, hash_refresh_token(refresh_token))
        if session is not None:
            crud.revoke_refresh_session(db, session.id)
    clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT


@router.get("/me", response_model=schemas.AuthUser)
def me(current_user=Depends(get_current_user)):
    return current_user

from datetime import datetime, timedelta, timezone
import logging

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .config import get_settings
from .database import SessionLocal, get_db
from .recognition import get_plate_recognizer
from .security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


class AuthRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = {}

    def __call__(self, request: Request) -> None:
        settings = get_settings()
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - settings.auth_rate_limit_window_seconds
        ip = request.client.host if request.client else "unknown"
        key = f"{ip}:{request.url.path}"
        timestamps = [
            timestamp
            for timestamp in self._buckets.get(key, [])
            if timestamp >= window_start
        ]
        if len(timestamps) >= settings.auth_rate_limit_max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts. Please try again shortly.",
            )
        timestamps.append(now)
        self._buckets[key] = timestamps


auth_rate_limiter = AuthRateLimiter()


def _unauthorized(detail: str = "Authentication required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> models.User:
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except Exception as exc:
        raise _unauthorized("Invalid or expired access token.") from exc

    user = crud.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Authenticated user is inactive or missing.")
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role != models.UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required.",
        )
    return current_user


def build_auth_response(
    *,
    db: Session,
    user: models.User,
    request: Request,
    response: Response,
    revoke_session_id: int | None = None,
) -> schemas.TokenResponse:
    settings = get_settings()
    if revoke_session_id is not None:
        crud.revoke_refresh_session(db, revoke_session_id)

    refresh_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    crud.create_refresh_session(
        db=db,
        session=schemas.RefreshSessionCreate(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        ),
    )
    access_token = create_access_token(
        user_id=user.id,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        expires=settings.refresh_token_days * 24 * 60 * 60,
        path="/",
        domain=settings.refresh_cookie_domain,
    )
    return schemas.TokenResponse(
        access_token=access_token,
        user=schemas.AuthUser.model_validate(user),
    )


def clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/",
        domain=settings.refresh_cookie_domain,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
    )


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    user = crud.get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def register_operator_user(
    db: Session,
    *,
    email: str,
    password: str,
) -> models.User:
    existing_user = crud.get_user_by_email(db, email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    return crud.create_user(
        db=db,
        user=schemas.UserCreate(
            email=email,
            password_hash=hash_password(password),
            role=models.UserRole.OPERATOR,
        ),
    )


def ensure_bootstrap_admin() -> None:
    settings = get_settings()
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        logger.warning(
            "Bootstrap admin credentials are not configured. "
            "Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD to enable first login."
        )
        return

    db = SessionLocal()
    try:
        if crud.count_users(db) > 0:
            return
        crud.create_user(
            db=db,
            user=schemas.UserCreate(
                email=settings.bootstrap_admin_email,
                password_hash=hash_password(settings.bootstrap_admin_password),
                role=models.UserRole.ADMIN,
            ),
        )
        logger.info("Created bootstrap VietPlateAI admin account for %s", settings.bootstrap_admin_email)
    finally:
        db.close()


def warm_detection_model() -> None:
    settings = get_settings()
    if not settings.warm_model_on_startup:
        return
    try:
        get_plate_recognizer()
        logger.info("VietPlateAI recognizer warmed successfully.")
    except Exception as exc:
        logger.exception("Failed to warm VietPlateAI recognizer: %s", exc)

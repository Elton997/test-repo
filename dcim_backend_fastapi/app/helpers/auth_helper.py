# app/helpers/auth_helper.py
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, TYPE_CHECKING

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db  # Centralized DB dependency

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models import auth_models as models

_auth_models_module = None


def _get_models():
    """Lazy-load auth models to avoid importing heavy SQLAlchemy definitions at startup."""
    global _auth_models_module
    if _auth_models_module is None:
        from app.models import auth_models as auth_models_module

        _auth_models_module = auth_models_module
    return _auth_models_module


def _get_token_from_header(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )
    scheme, _, token_str = authorization.partition(" ")
    token_str = token_str.strip()
    if scheme.lower() != "bearer" or not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    return token_str


def _build_jwt_payload(user: "models.User") -> Dict[str, Any]:
    """
    Build JWT claims for a user including RBAC/role information.

    Payload includes:
    - sub: user id
    - username, email
    - roles: list of active role codes
    - is_active flag
    - iat / exp based on ACCESS_TOKEN_EXPIRE_SECONDS
    """
    # Collect active role codes for the user
    role_codes = {
        (ur.role.code or "").upper()
        for ur in (user.user_roles or [])
        if ur.role and ur.role.is_active and ur.role.code
    }

    now = datetime.now(timezone.utc)
    expire_at = now + timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)

    return {
        "sub": str(user.id),
        "username": user.name,
        "email": user.email,
        "roles": sorted(role_codes),
        "is_active": bool(user.is_active),
        "iat": int(now.timestamp()),
        "exp": int(expire_at.timestamp()),
    }


def create_access_token_for_user(*, user: "models.User") -> str:
    """
    Create a signed JWT access token for the given user.

    The token does NOT get stored in the database – only the refresh token is
    persisted. All RBAC/user details are embedded as claims.
    """
    payload = _build_jwt_payload(user)
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.

    - Returns payload on success
    - Raises HTTPException(419) if token is expired
    - Raises HTTPException(401) for other validation errors
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=419,
            detail="Access token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )


def get_current_refresh_token(
    db: Session = Depends(get_db),
    authorization: str | None = Header(None, alias="Authorization"),
) -> "models.Token":
    """
    Resolve the current refresh token from the Authorization header.

    Refresh tokens remain opaque, stored in the database with expiry and type.
    """
    models = _get_models()
    token_key = _get_token_from_header(authorization)

    # Look up by token key first to avoid being overly strict on token_type filtering.
    token = db.query(models.Token).filter(models.Token.token_key == token_key).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    if (token.token_type or "").lower() != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token type",
        )

    if token.expires and token.expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    return token


def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> "models.User":
    """
    Dependency that validates the JWT access token and returns the DB user.

    - Validates the Authorization: Bearer <jwt> header
    - Decodes JWT using settings.JWT_SECRET_KEY / JWT_ALGORITHM
    - Loads the user by ID from the database and checks is_active
    """
    token_str = _get_token_from_header(authorization)
    payload = decode_access_token(token_str)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token missing subject",
        )

    models = _get_models()
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier in token",
        )

    user = db.query(models.User).get(user_id_int)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or invalid user",
        )
    return user

def build_menu_for_user(db: Session, user_id: int):
    models = _get_models()
    # Load user + roles
    user = db.query(models.User).get(user_id)

    is_admin = False
    if user:
        for ur in user.user_roles:
            if ur.role and ur.role.code and ur.role.code.upper() == "ADMIN":
                is_admin = True
                break

    if is_admin:
        # Super admin → see ALL active menus & sub_menus
        rows = (
            db.query(models.Menu, models.SubMenu)
            .join(models.SubMenu, models.SubMenu.menu_id == models.Menu.id)
            .filter(models.Menu.is_active == True)
            .filter(models.SubMenu.is_active == True)
            .order_by(models.Menu.sort_order, models.SubMenu.sort_order)
            .all()
        )
    else:
        # Normal RBAC-filtered menu (only active menus/submenus)
        rows = (
            db.query(models.Menu, models.SubMenu)
            .join(models.SubMenu, models.SubMenu.menu_id == models.Menu.id)
            .join(models.RoleSubMenuAccess, models.RoleSubMenuAccess.sub_menu_id == models.SubMenu.id)
            .join(models.UserRole, models.UserRole.role_id == models.RoleSubMenuAccess.role_id)
            .filter(models.UserRole.user_id == user_id)
            .filter(models.RoleSubMenuAccess.can_view == 1)
            .filter(models.Menu.is_active == True)
            .filter(models.SubMenu.is_active == True)
            .order_by(models.Menu.sort_order, models.SubMenu.sort_order)
            .all()
        )

    menu_dict = {}

    for menu, sub in rows:
        key = menu.header_name
        if key not in menu_dict:
            menu_dict[key] = {
                "MenuHeaderName": menu.header_name,
                "icon": menu.icon,
                "sub_menu_details": [],
            }

        menu_dict[key]["sub_menu_details"].append(
            {
                "display_name": sub.display_name,
                "page_url": sub.page_url,
                "icon": sub.icon,
            }
        )

    return {"menuList": list(menu_dict.values())}


def create_token_for_user(
    *,
    user: "models.User",
    db: Session,
    expires_in: int,
    token_type: str = "refresh",
) -> "models.Token":
    models = _get_models()
    token_key = secrets.token_hex(32)

    token = models.Token(
        token_key=token_key,
        user_id=user.id,
        created=datetime.utcnow(),
        expires=datetime.utcnow() + timedelta(seconds=expires_in),
        token_type=token_type,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def create_token_pair_for_user(
    *,
    user: "models.User",
    db: Session,
) -> tuple[str, "models.Token"]:
    """
    Create a JWT access token and a single persisted refresh token for a user.

    Only the refresh token is stored in the database; the access token is a
    signed JWT built from user claims and expiry.
    """
    access_token = create_access_token_for_user(user=user)
    refresh_token = create_token_for_user(
        user=user,
        db=db,
        expires_in=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        token_type="refresh",
    )
    return access_token, refresh_token
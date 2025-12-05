# app/dcim/router.py
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.helpers.auth_helper import (
    build_menu_for_user,
    create_access_token_for_user,
    create_token_pair_for_user,
    get_current_user,
    get_current_refresh_token,
)
from app.schemas import auth_schemas as schemas
from app.services.ldap_service import ldap_authenticate

if TYPE_CHECKING:  # pragma: no cover
    from app.models import auth_models as models


router = APIRouter(prefix="/api/dcim", tags=["auth"])


@lru_cache(maxsize=1)
def _get_auth_models():
    from app.models import auth_models as auth_models_module

    return auth_models_module


def _build_configure_flags(user: models.User) -> schemas.ConfigureFlags:
    role_codes = {
        (ur.role.code or "").upper()
        for ur in user.user_roles
        if ur.role and ur.role.code and ur.role.is_active
    }
    has_admin = "ADMIN" in role_codes
    has_editor = "EDITOR" in role_codes
    has_viewer = "VIEWER" in role_codes

    # Editors inherit viewer abilities, admins inherit all abilities
    return schemas.ConfigureFlags(
        is_editable=has_admin or has_editor,
        is_deletable=has_admin,
        is_viewer=has_admin or has_editor or has_viewer,
    )


@router.post("/login", response_model=schemas.LoginResponse)
def login(
    credentials: schemas.LoginRequest,   # 👈 now from body
    db: Session = Depends(get_db),
):
    """
    Frontend sends JSON body:
      {
        "username": "admin",
        "password": "xyz"
      }
    """

    auth_user = credentials.username
    auth_pass = credentials.password

    # ok, user_dn = ldap_authenticate(
    #     server_uri=settings.LDAP_SERVER_URI,
    #     base_dn=settings.LDAP_BASE_DN,
    #     username=auth_user,
    #     password=auth_pass,
    #     bind_dn=settings.LDAP_BIND_DN,
    #     bind_password=settings.LDAP_BIND_PASSWORD
    # )

    # if not ok:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="LDAP authentication failed"
    #     )
    
    models = _get_auth_models()

    user = (
        db.query(models.User)
        .filter(models.User.name == auth_user)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    # TODO: verify password or LDAP

    # Optional: delete existing tokens for this user if you want "single-session" behavior
    db.query(models.Token).filter(models.Token.user_id == user.id).delete()
    db.commit()

    # Issue token pair (JWT access token + DB-backed refresh token)
    access_token, refresh_token = create_token_pair_for_user(user=user, db=db)

    # Build RBAC menu
    menu = build_menu_for_user(db, user.id)

    # Update last_login (use current time)
    user.last_login = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)

    return schemas.LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token.token_key,
        user=user,
        menuList=menu["menuList"],
        configure=_build_configure_flags(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Logout: remove all refresh tokens for this user.
    """
    models = _get_auth_models()

    db.query(models.Token).filter(models.Token.user_id == current_user.id).delete()
    db.commit()


@router.post("/refresh", response_model=schemas.LoginResponse)
def refresh_token(
    refresh_token=Depends(get_current_refresh_token),
    db: Session = Depends(get_db),
):
    """
    Refresh flow:
      - client sends refresh token in Authorization: Bearer <refresh_token>
      - validate refresh token
      - delete all tokens for that user (or at least old pair)
      - create new access + refresh tokens
      - return new pair + menu
    """
    user = refresh_token.user
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or invalid user",
        )

    # Issue new access token using the existing (still valid) refresh token.
    # When the refresh token itself expires, the user must log in again.
    new_access = create_access_token_for_user(user=user)

    # Update last_login to new access token creation time (optional)
    user.last_login = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)

    # Rebuild menu
    menu = build_menu_for_user(db, user.id)

    return schemas.LoginResponse(
        access_token=new_access,
        # Reuse the same refresh token key until it expires
        refresh_token=refresh_token.token_key,
        user=user,
        menuList=menu["menuList"],
        configure=_build_configure_flags(user),
    )
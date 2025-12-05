# app/helpers/rbac_helper.py
"""
RBAC helper functions for role-based access control.
Updated to match Alembic migrations with 'dcim' schema.
"""
from enum import Enum
from typing import Dict, Optional, Set

from fastapi import Depends, Header, HTTPException, status

from app.helpers.auth_helper import decode_access_token, _get_token_from_header


class AccessLevel(str, Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


ADMIN_CODES: Set[str] = {"ADMIN"}
EDITOR_CODES: Set[str] = {"EDITOR"}
VIEWER_CODES: Set[str] = {"VIEWER"}


def _access_level_from_roles(roles: Set[str]) -> AccessLevel:
    """
    Compute access level from a set of role codes.
    """
    if roles & ADMIN_CODES:
        return AccessLevel.admin
    if roles & EDITOR_CODES:
        return AccessLevel.editor
    if roles & VIEWER_CODES:
        return AccessLevel.viewer
    # Default to viewer if no matching role codes found
    return AccessLevel.viewer


def get_access_level(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AccessLevel:
    """
    FastAPI dependency to compute the user's AccessLevel (admin/editor/viewer).

    This uses the roles embedded in the JWT access token to avoid extra DB
    queries. The JWT is expected to contain a `roles` claim with active role
    codes (e.g., ["ADMIN", "EDITOR", "VIEWER"]).
    """
    token_str = _get_token_from_header(authorization)
    payload: Dict[str, object] = decode_access_token(token_str)

    raw_roles = payload.get("roles") or []
    if isinstance(raw_roles, str):
        roles_set: Set[str] = {raw_roles.upper()}
    else:
        try:
            roles_iter = list(raw_roles)  # type: ignore[arg-type]
        except TypeError:
            roles_iter = []
        roles_set = {str(r).upper() for r in roles_iter}

    is_superuser = bool(payload.get("is_superuser"))  # optional flag
    if is_superuser:
        return AccessLevel.admin

    return _access_level_from_roles(roles_set)


def require_at_least_viewer(
    access_level: AccessLevel = Depends(get_access_level),
) -> AccessLevel:
    """
    Require that the user has at least viewer access.
    For now, all roles that resolve to viewer/editor/admin are allowed.
    """
    if access_level not in {AccessLevel.admin, AccessLevel.editor, AccessLevel.viewer}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this resource.",
        )
    return access_level


def require_editor_or_admin(
    access_level: AccessLevel = Depends(get_access_level),
) -> AccessLevel:
    """
    Require editor or admin access for write operations (create/update/delete).
    """
    if access_level not in {AccessLevel.admin, AccessLevel.editor}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You need editor or admin access to perform this action.",
        )
    return access_level


def require_admin(
    access_level: AccessLevel = Depends(get_access_level),
) -> AccessLevel:
    """
    Require admin-only access for privileged operations.
    """
    if access_level is not AccessLevel.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this action.",
        )
    return access_level

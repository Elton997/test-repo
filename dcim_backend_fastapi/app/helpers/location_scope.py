from __future__ import annotations

from typing import Optional, Set

from fastapi import HTTPException, status

from app.helpers.rbac_helper import AccessLevel


def get_allowed_location_ids(current_user, access_level: AccessLevel) -> Optional[Set[int]]:
    """
    Resolve the set of location IDs the current user is allowed to access.

    Returns:
        - None: user is admin → unrestricted.
        - Set[int]: allowed location IDs for non-admin users.

    Raises:
        HTTPException(403) if a non-admin user does not have any assigned locations.
    """
    if access_level == AccessLevel.admin:
        return None

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to determine current user for location access restriction.",
        )

    accesses = getattr(current_user, "location_accesses", None) or []
    allowed_ids = {
        entry.location_id
        for entry in accesses
        if entry.location_id is not None
    }

    if not allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No locations are assigned to your account. Contact an administrator.",
        )

    return allowed_ids


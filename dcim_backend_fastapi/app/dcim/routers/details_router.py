"""
DCIM Details Router - Generic API for retrieving detailed information about specific entities.
Supports fetching single entity details by type and ID with all related data.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.rbac_helper import AccessLevel, require_at_least_viewer
from app.helpers.listing_types import ListingType
from app.helpers.location_scope import get_allowed_location_ids
from app.models.entity_models import Location, Building, Rack, Device, Datacenter, AssetOwner

router = APIRouter(prefix="/api/dcim", tags=["DCIM Details"])


def _get_detail_handlers():
    """Lazy import heavy helper only when needed."""
    from app.helpers.details_helper import ENTITY_DETAIL_HANDLERS

    return ENTITY_DETAIL_HANDLERS


def _ensure_entity_in_location_scope(
    db: Session,
    entity: ListingType,
    name: str,
    allowed_location_ids,
) -> None:
    if allowed_location_ids is None:
        return

    scope_map = {
        ListingType.locations: (Location, Location.id),
        ListingType.buildings: (Building, Building.location_id),
        ListingType.racks: (Rack, Rack.location_id),
        ListingType.devices: (Device, Device.location_id),
        ListingType.datacenters: (Datacenter, Datacenter.location_id),
        ListingType.asset_owner: (AssetOwner, AssetOwner.location_id),
    }

    if entity not in scope_map:
        return

    model_cls, location_column = scope_map[entity]

    query = (
        db.query(location_column)
        .filter(func.upper(model_cls.name) == func.upper(name))
        .filter(location_column.in_(allowed_location_ids))
    )

    if not query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity.value} '{name}' not found or access denied",
        )


@router.get(
    "/details",
    response_model=Dict[str, Any],
    summary="Generic DCIM details API - Get entity details by type and name",
)
def get_entity_details(
    entity: ListingType = Query(
        ...,
        description=(
            "Entity type: racks | devices | device_types | "
            "locations | buildings | asset_owner | makes | models"
        ),
    ),
    name: str = Query(..., description="Entity name to fetch details for", min_length=1),
    access_level: AccessLevel = Depends(require_at_least_viewer),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Single endpoint to get detailed information about any DCIM entity by name.
    
    Supports:
    - locations: Location info + buildings list + stats
    - buildings: Building info + racks list + capacity stats
    - racks: Rack info + devices list + utilization stats
    - devices: Full device info with all relationships
    - device_types: Device type + make + model + device count
    - asset_owner: Asset owner + location info
    - makes: Make + models + device types + stats
    - models: Model + make + device types
    
    Returns detailed entity-specific data with nested related objects.
    """
    handler = _get_detail_handlers().get(entity)
    
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {entity}",
        )

    allowed_location_ids = get_allowed_location_ids(current_user, access_level)
    _ensure_entity_in_location_scope(db, entity, name, allowed_location_ids)

    data = handler(db, name)

    return {
        "entity": entity,
        "data": data,
    }
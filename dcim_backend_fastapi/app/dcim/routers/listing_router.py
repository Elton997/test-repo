"""
DCIM Listing Router - Generic API for listing various DCIM entities.
Supports pagination, filtering, and role-based access control.
Updated to match Alembic migrations.
"""
from datetime import date
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.listing_cache import (
    build_listing_cache_key,
    listing_cache,
)
from app.helpers.rbac_helper import AccessLevel, require_at_least_viewer
from app.helpers.listing_types import ListingType
from app.helpers.location_scope import get_allowed_location_ids

router = APIRouter(prefix="/api/dcim", tags=["DCIM Listings"])


def _normalize_empty_to_none(value: Union[str, int, date, None]) -> Union[str, int, date, None]:
    """Convert empty strings to None for optional parameters."""
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _parse_optional_int(value: Union[str, int, None]) -> Optional[int]:
    """Parse optional integer parameter, converting empty strings to None."""
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip() == "":
            return None
        try:
            return int(value)
        except ValueError:
            return None
    return int(value)


def _parse_optional_date(value: Union[str, date, None]) -> Optional[date]:
    """Parse optional date parameter, converting empty strings to None."""
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip() == "":
            return None
        try:
            # Try parsing ISO format date (YYYY-MM-DD)
            return date.fromisoformat(value)
        except ValueError:
            return None
    return value if isinstance(value, date) else None


def _get_listing_handler(entity: ListingType):
    """Lazy import for heavy listing helper module."""
    from app.helpers.listing_helper import ENTITY_LIST_HANDLERS

    return ENTITY_LIST_HANDLERS.get(entity)


@router.get(
    "/list",
    response_model=Dict[str, Any],
    summary="Generic DCIM listing API with role-based RBAC and pagination",
)
def list_dcim_entities(
    entity: ListingType = Query(
        ...,
        description=(
            "What to list: locations | buildings | racks | devices | "
            "device_types | makes | models | datacenters | asset_owner | applications"
        ),
    ),
    offset: int = Query(0, ge=0, description="Offset for pagination (0-based)"),
    page_size: int = Query(10, ge=1, le=100, description="Page size for pagination (max 100)"),
    # Location filters
    location_name: Optional[str] = Query(None, description="Filter by location name"),
    location_description: Optional[str] = Query(None, description="Filter by location description"),
    # Building filters
    building_name: Optional[str] = Query(None, description="Filter by building name"),
    building_status: Optional[str] = Query(None, description="Filter by building status"),
    building_description: Optional[str] = Query(None, description="Filter by building description"),
    # Wing filters
    wing_name: Optional[str] = Query(None, description="Filter by wing name"),
    wing_description: Optional[str] = Query(None, description="Filter by wing description"),
    # Floor filters
    floor_name: Optional[str] = Query(None, description="Filter by floor name"),
    floor_description: Optional[str] = Query(None, description="Filter by floor description"),
    # Rack filters
    rack_name: Optional[str] = Query(None, description="Filter by rack name"),
    rack_status: Optional[str] = Query(None, description="Filter by rack status"),
    rack_height: Optional[Union[str, int]] = Query(None, description="Filter by rack height"),
    rack_description: Optional[str] = Query(None, description="Filter by rack description"),
    # Device filters
    device_name: Optional[str] = Query(None, description="Filter by device name"),
    device_status: Optional[str] = Query(None, description="Filter by device status"),
    device_position: Optional[Union[str, int]] = Query(None, description="Filter by device position"),
    device_face: Optional[str] = Query(None, description="Filter by device face (front/rear)"),
    device_description: Optional[str] = Query(None, description="Filter by device description"),
    serial_number: Optional[str] = Query(None, description="Filter by device serial number"),
    ip_address: Optional[str] = Query(None, description="Filter by device IP address"),
    po_number: Optional[str] = Query(None, description="Filter by device PO number"),
    asset_user: Optional[str] = Query(None, description="Filter by device asset user"),
    asset_owner: Optional[str] = Query(None, description="Filter by device asset owner name"),
    applications_mapped_name: Optional[str] = Query(None, description="Filter by application mapped name"),
    warranty_start_date: Optional[Union[str, date]] = Query(None, description="Filter by warranty start date (YYYY-MM-DD)"),
    warranty_end_date: Optional[Union[str, date]] = Query(None, description="Filter by warranty end date (YYYY-MM-DD)"),
    amc_start_date: Optional[Union[str, date]] = Query(None, description="Filter by AMC start date (YYYY-MM-DD)"),
    amc_end_date: Optional[Union[str, date]] = Query(None, description="Filter by AMC end date (YYYY-MM-DD)"),
    # Device type filters
    device_type: Optional[str] = Query(None, description="Filter by device type name"),
    device_type_description: Optional[str] = Query(None, description="Filter by device type description"),
    # Make filters
    make_name: Optional[str] = Query(None, description="Filter by make name"),
    make_description: Optional[str] = Query(None, description="Filter by make description"),
    # Model filters
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    model_description: Optional[str] = Query(None, description="Filter by model description"),
    model_height: Optional[Union[str, int]] = Query(None, description="Filter by model height"),
    # Datacenter filters
    datacenter_name: Optional[str] = Query(None, description="Filter by datacenter name"),
    datacenter_description: Optional[str] = Query(None, description="Filter by datacenter description"),
    # Asset owner filters
    asset_owner_name: Optional[str] = Query(None, description="Filter by asset owner name"),
    asset_owner_description: Optional[str] = Query(None, description="Filter by asset owner description"),
    # Application filters
    application_name: Optional[str] = Query(None, description="Filter by application name"),
    application_description: Optional[str] = Query(None, description="Filter by application description"),
    access_level: AccessLevel = Depends(require_at_least_viewer),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Single endpoint to list different DCIM entities with aggregates and derived fields.
    
    Supports:
    - Pagination via offset/page_size
    - Filtering by location_name, building_name, wing_name, floor_name, rack_name, device_name, device_type, make_name, model_name, datacenter_name
    - Role-based access control (viewer, editor, admin)
    
    Entity types and their returned fields:
    
    Supported entities and returned fields:
    
    **locations**
    - id, name, buildings (total count)
    
    **buildings**:
    - id, name, status, location (name), devices (total), racks (total)
    
    **racks**:
    - id, name, location (name), building (name), wing (name), floor (name), 
      datacenter (name), status, height, devices (total), used_space (U consumed),
      available_space (remaining space)
    
    **devices**:
    - id, name, status, building (name), location (name), wing (name), floor (name), 
      datacenter (name), rack (name), height (from model), make (name), 
      device_type (name), ip, po_number, asset_owner, asset_user, 
      application_mapped (name), warranty_start_date, warranty_end_date, 
      amc_start_date, amc_end_date, serial_no
    
    **device_types**:
    - id, name (device type name), make (name), primary_model_height (U Height), 
      instances (devices total)
    
    **asset_owner**:
    - id, name (owner name), location (name), description, applications (count)
    
    **applications**:
    - id, name (application name), asset_owner (name), description, devices (count)
    
    **makes**:
    - id, name, racks (total), devices (total), models (model types total), description
    
    **models**:
    - id, name (model name), make (name), device_types (count)
    
    **datacenters**:
    - id, name, description, location (name), building (name), wing (name), 
      floor (name), racks (total), devices (total)
    
    Returns entity-specific fields with computed aggregates.
    """
    allowed_location_ids = get_allowed_location_ids(current_user, access_level)

    # Normalize empty strings to None for string parameters
    # Parse integer and date parameters, converting empty strings to None
    rack_height_parsed = _parse_optional_int(rack_height)
    device_position_parsed = _parse_optional_int(device_position)
    model_height_parsed = _parse_optional_int(model_height)
    warranty_start_date_parsed = _parse_optional_date(warranty_start_date)
    warranty_end_date_parsed = _parse_optional_date(warranty_end_date)
    amc_start_date_parsed = _parse_optional_date(amc_start_date)
    amc_end_date_parsed = _parse_optional_date(amc_end_date)
    
    # Collect all filter parameters into a dictionary for cleaner code
    filter_params = {
        'location_name': _normalize_empty_to_none(location_name),
        'location_description': _normalize_empty_to_none(location_description),
        'building_name': _normalize_empty_to_none(building_name),
        'building_status': _normalize_empty_to_none(building_status),
        'building_description': _normalize_empty_to_none(building_description),
        'wing_name': _normalize_empty_to_none(wing_name),
        'wing_description': _normalize_empty_to_none(wing_description),
        'floor_name': _normalize_empty_to_none(floor_name),
        'floor_description': _normalize_empty_to_none(floor_description),
        'rack_name': _normalize_empty_to_none(rack_name),
        'rack_status': _normalize_empty_to_none(rack_status),
        'rack_height': rack_height_parsed,
        'rack_description': _normalize_empty_to_none(rack_description),
        'device_name': _normalize_empty_to_none(device_name),
        'device_status': _normalize_empty_to_none(device_status),
        'device_position': device_position_parsed,
        'device_face': _normalize_empty_to_none(device_face),
        'device_description': _normalize_empty_to_none(device_description),
        'serial_number': _normalize_empty_to_none(serial_number),
        'ip_address': _normalize_empty_to_none(ip_address),
        'po_number': _normalize_empty_to_none(po_number),
        'asset_user': _normalize_empty_to_none(asset_user),
        'asset_owner': _normalize_empty_to_none(asset_owner),
        'applications_mapped_name': _normalize_empty_to_none(applications_mapped_name),
        'warranty_start_date': warranty_start_date_parsed,
        'warranty_end_date': warranty_end_date_parsed,
        'amc_start_date': amc_start_date_parsed,
        'amc_end_date': amc_end_date_parsed,
        'device_type': _normalize_empty_to_none(device_type),
        'device_type_description': _normalize_empty_to_none(device_type_description),
        'make_name': _normalize_empty_to_none(make_name),
        'make_description': _normalize_empty_to_none(make_description),
        'model_name': _normalize_empty_to_none(model_name),
        'model_description': _normalize_empty_to_none(model_description),
        'model_height': model_height_parsed,
        'datacenter_name': _normalize_empty_to_none(datacenter_name),
        'datacenter_description': _normalize_empty_to_none(datacenter_description),
        'asset_owner_name': _normalize_empty_to_none(asset_owner_name),
        'asset_owner_description': _normalize_empty_to_none(asset_owner_description),
        'application_name': _normalize_empty_to_none(application_name),
        'application_description': _normalize_empty_to_none(application_description),
    }
    
    # Build cache key with all parameters
    cache_key = build_listing_cache_key(
        entity=entity,
        offset=offset,
        page_size=page_size,
        user_id=getattr(current_user, "id", None),
        access_level=getattr(access_level, "value", str(access_level)),
        **filter_params,
    )

    # Check cache first
    cached_payload = listing_cache.get(cache_key)
    if cached_payload:
        return cached_payload

    # Get handler
    handler = _get_listing_handler(entity)
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {entity}",
        )

    # Call handler with all parameters
    total, data = handler(
        db=db,
        offset=offset,
        page_size=page_size,
        allowed_location_ids=allowed_location_ids,
        **filter_params,
    )

    response_payload = {
        "entity": entity,
        "offset": offset,
        "limit": page_size,
        "total": total,
        "results": data,
    }

    listing_cache.set(cache_key, response_payload, entity=entity)

    return response_payload

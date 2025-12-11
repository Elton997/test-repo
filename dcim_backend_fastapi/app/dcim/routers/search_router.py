"""
DCIM Global Search Router - Search across all DCIM entities.
Searches across ALL fields in each entity type.
"""
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.rbac_helper import AccessLevel, require_at_least_viewer
from app.helpers.location_scope import get_allowed_location_ids
from app.models.entity_models import (
    Location,
    Building,
    Wing,
    Floor,
    Datacenter,
    Rack,
    Device,
    DeviceType,
    Make,
    Model,
    AssetOwner,
    ApplicationMapped,
)
from app.models.auth_models import User

router = APIRouter(prefix="/api/dcim", tags=["DCIM Global Search"])


def _search_locations(
    db: Session,
    search_term: str,
    limit: int,
    allowed_location_ids: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """Search locations across all fields."""
    search_upper = search_term.upper()
    # Try to convert search term to integer for ID search
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(Location.name).contains(search_upper),
        func.upper(func.to_char(Location.id)).contains(search_upper),
        func.upper(Location.description).contains(search_upper),
    ]
    
    if search_id is not None:
        conditions.append(Location.id == search_id)
    
    query = (
        db.query(Location)
        .filter(or_(*conditions))
        .order_by(Location.name)
        .limit(limit)
    )
    if allowed_location_ids is not None:
        query = query.filter(Location.id.in_(allowed_location_ids))
    results = query.all()
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "description": loc.description,
            "type": "location",
        }
        for loc in results
    ]


def _search_buildings(
    db: Session,
    search_term: str,
    limit: int,
    allowed_location_ids: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """Search buildings across all fields including related location."""
    search_upper = search_term.upper()
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(Building.name).contains(search_upper),
        func.upper(Building.status).contains(search_upper),
        func.upper(Building.description).contains(search_upper),
        func.upper(func.to_char(Building.id)).contains(search_upper),
        func.upper(func.to_char(Building.location_id)).contains(search_upper),
        func.upper(Location.name).contains(search_upper),  # Search in related location name
        func.upper(Location.description).contains(search_upper),
    ]
    
    if search_id is not None:
        conditions.extend([Building.id == search_id, Building.location_id == search_id])
    
    query = (
        db.query(Building, Location)
        .join(Location, Building.location_id == Location.id)
        .filter(or_(*conditions))
        .order_by(Building.name)
        .limit(limit)
    )
    if allowed_location_ids is not None:
        query = query.filter(Building.location_id.in_(allowed_location_ids))
    results = query.all()
    return [
        {
            "id": building.id,
            "name": building.name,
            "status": building.status,
            "description": building.description,
            "location": location.name if location else None,
            "type": "building",
        }
        for building, location in results
    ]


def _search_racks(
    db: Session,
    search_term: str,
    limit: int,
    allowed_location_ids: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """Search racks across all fields including related entities."""
    search_upper = search_term.upper()
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(Rack.name).contains(search_upper),
        func.upper(Rack.status).contains(search_upper),
        func.upper(Rack.description).contains(search_upper),
        func.upper(func.to_char(Rack.id)).contains(search_upper),
        func.upper(func.to_char(Rack.height)).contains(search_upper),
        func.upper(func.to_char(Rack.space_used)).contains(search_upper),
        func.upper(func.to_char(Rack.space_available)).contains(search_upper),
        func.upper(Location.name).contains(search_upper),
        func.upper(Building.name).contains(search_upper),
    ]
    
    if search_id is not None:
        conditions.extend([
            Rack.id == search_id,
            Rack.height == search_id,
            Rack.space_used == search_id,
            Rack.space_available == search_id,
        ])
    
    query = (
        db.query(Rack, Location, Building)
        .join(Location, Rack.location_id == Location.id)
        .join(Building, Rack.building_id == Building.id)
        .filter(or_(*conditions))
        .order_by(Rack.name)
        .limit(limit)
    )
    if allowed_location_ids is not None:
        query = query.filter(Rack.location_id.in_(allowed_location_ids))
    results = query.all()
    return [
        {
            "id": rack.id,
            "name": rack.name,
            "status": rack.status,
            "description": rack.description,
            "location": location.name if location else None,
            "building": building.name if building else None,
            "height": rack.height,
            "type": "rack",
        }
        for rack, location, building in results
    ]


def _search_devices(
    db: Session,
    search_term: str,
    limit: int,
    allowed_location_ids: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """Search devices across all fields including related entities."""
    search_upper = search_term.upper()
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(Device.name).contains(search_upper),
        func.upper(Device.serial_no).contains(search_upper),
        func.upper(Device.ip).contains(search_upper),
        func.upper(Device.status).contains(search_upper),
        func.upper(Device.po_number).contains(search_upper),
        func.upper(Device.asset_user).contains(search_upper),
        func.upper(Device.description).contains(search_upper),
        func.upper(func.to_char(Device.id)).contains(search_upper),
        func.upper(func.to_char(Device.position)).contains(search_upper),
        func.upper(func.to_char(Device.space_required)).contains(search_upper),
    ]
    
    # Search in related entities
    conditions.extend([
        func.upper(Location.name).contains(search_upper),
        func.upper(Building.name).contains(search_upper),
        func.upper(Rack.name).contains(search_upper),
    ])
    
    if search_id is not None:
        conditions.extend([
            Device.id == search_id,
            Device.position == search_id,
            Device.space_required == search_id,
        ])
    
    query = (
        db.query(Device, Location, Building, Rack, Make, DeviceType, ApplicationMapped, AssetOwner)
        .outerjoin(Location, Device.location_id == Location.id)
        .outerjoin(Building, Device.building_id == Building.id)
        .outerjoin(Rack, Device.rack_id == Rack.id)
        .outerjoin(Make, Device.make_id == Make.id)
        .outerjoin(DeviceType, Device.devicetype_id == DeviceType.id)
        .outerjoin(ApplicationMapped, Device.applications_mapped_id == ApplicationMapped.id)
        .outerjoin(AssetOwner, ApplicationMapped.asset_owner_id == AssetOwner.id)
        .filter(or_(*conditions))
        .order_by(Device.name)
        .limit(limit)
    )
    if allowed_location_ids is not None:
        query = query.filter(Device.location_id.in_(allowed_location_ids))
    results = query.all()
    return [
        {
            "id": device.id,
            "name": device.name,
            "status": device.status,
            "description": device.description,
            "serial_no": device.serial_no,
            "ip": device.ip,
            "po_number": device.po_number,
            "asset_user": device.asset_user,
            "position": device.position,
            "location": location.name if location else None,
            "building": building.name if building else None,
            "rack": rack.name if rack else None,
            "make": make.name if make else None,
            "device_type": device_type.name if device_type else None,
            "application": application.name if application else None,
            "asset_owner": asset_owner.name if asset_owner else None,
            "type": "device",
        }
        for device, location, building, rack, make, device_type, application, asset_owner in results
    ]


def _search_device_types(
    db: Session,
    search_term: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Search device types across all fields including related make."""
    search_upper = search_term.upper()
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(DeviceType.name).contains(search_upper),
        func.upper(DeviceType.description).contains(search_upper),
        func.upper(func.to_char(DeviceType.id)).contains(search_upper),
        func.upper(Make.name).contains(search_upper),  # Search in related make name
        func.upper(Make.description).contains(search_upper),
    ]
    
    if search_id is not None:
        conditions.extend([DeviceType.id == search_id, DeviceType.make_id == search_id])
    
    query = (
        db.query(DeviceType, Make)
        .outerjoin(Make, DeviceType.make_id == Make.id)
        .filter(or_(*conditions))
        .order_by(DeviceType.name)
        .limit(limit)
    )
    results = query.all()
    return [
        {
            "id": device_type.id,
            "name": device_type.name,
            "description": device_type.description,
            "make": make.name if make else None,
            "type": "device_type",
        }
        for device_type, make in results
    ]


def _search_makes(
    db: Session,
    search_term: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Search makes across all fields."""
    search_upper = search_term.upper()
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(Make.name).contains(search_upper),
        func.upper(Make.description).contains(search_upper),
        func.upper(func.to_char(Make.id)).contains(search_upper),
    ]
    
    if search_id is not None:
        conditions.append(Make.id == search_id)
    
    query = (
        db.query(Make)
        .filter(or_(*conditions))
        .order_by(Make.name)
        .limit(limit)
    )
    results = query.all()
    return [
        {
            "id": make.id,
            "name": make.name,
            "description": make.description,
            "type": "make",
        }
        for make in results
    ]


def _search_models(
    db: Session,
    search_term: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Search models across all fields including related make and device type."""
    search_upper = search_term.upper()
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(Model.name).contains(search_upper),
        func.upper(Model.description).contains(search_upper),
        func.upper(func.to_char(Model.id)).contains(search_upper),
        func.upper(func.to_char(Model.height)).contains(search_upper),
        func.upper(Make.name).contains(search_upper),
        func.upper(Make.description).contains(search_upper),
        func.upper(DeviceType.name).contains(search_upper),
        func.upper(DeviceType.description).contains(search_upper),
    ]
    
    if search_id is not None:
        conditions.extend([
            Model.id == search_id,
            Model.height == search_id,
            Model.make_id == search_id,
            Model.device_type_id == search_id,
        ])
    
    query = (
        db.query(Model, Make, DeviceType)
        .join(Make, Model.make_id == Make.id)
        .join(DeviceType, Model.device_type_id == DeviceType.id)
        .filter(or_(*conditions))
        .order_by(Model.name)
        .limit(limit)
    )
    results = query.all()
    return [
        {
            "id": model.id,
            "name": model.name,
            "description": model.description,
            "height": model.height,
            "make": make.name if make else None,
            "device_type": device_type.name if device_type else None,
            "type": "model",
        }
        for model, make, device_type in results
    ]


def _search_datacenters(
    db: Session,
    search_term: str,
    limit: int,
    allowed_location_ids: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """Search datacenters across all fields including related entities."""
    search_upper = search_term.upper()
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(Datacenter.name).contains(search_upper),
        func.upper(Datacenter.description).contains(search_upper),
        func.upper(func.to_char(Datacenter.id)).contains(search_upper),
        func.upper(Location.name).contains(search_upper),
        func.upper(Location.description).contains(search_upper),
        func.upper(Building.name).contains(search_upper),
        func.upper(Building.description).contains(search_upper),
    ]
    
    if search_id is not None:
        conditions.extend([
            Datacenter.id == search_id,
            Datacenter.location_id == search_id,
            Datacenter.building_id == search_id,
        ])
    
    query = (
        db.query(Datacenter, Location, Building)
        .join(Location, Datacenter.location_id == Location.id)
        .join(Building, Datacenter.building_id == Building.id)
        .filter(or_(*conditions))
        .order_by(Datacenter.name)
        .limit(limit)
    )
    if allowed_location_ids is not None:
        query = query.filter(Datacenter.location_id.in_(allowed_location_ids))
    results = query.all()
    return [
        {
            "id": datacenter.id,
            "name": datacenter.name,
            "description": datacenter.description,
            "location": location.name if location else None,
            "building": building.name if building else None,
            "type": "datacenter",
        }
        for datacenter, location, building in results
    ]


def _search_asset_owners(
    db: Session,
    search_term: str,
    limit: int,
    allowed_location_ids: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """Search asset owners across all fields including related location."""
    search_upper = search_term.upper()
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(AssetOwner.name).contains(search_upper),
        func.upper(AssetOwner.description).contains(search_upper),
        func.upper(func.to_char(AssetOwner.id)).contains(search_upper),
        func.upper(Location.name).contains(search_upper),
        func.upper(Location.description).contains(search_upper),
    ]
    
    if search_id is not None:
        conditions.extend([AssetOwner.id == search_id, AssetOwner.location_id == search_id])
    
    query = (
        db.query(AssetOwner, Location)
        .outerjoin(Location, AssetOwner.location_id == Location.id)
        .filter(or_(*conditions))
        .order_by(AssetOwner.name)
        .limit(limit)
    )
    if allowed_location_ids is not None:
        query = query.filter(AssetOwner.location_id.in_(allowed_location_ids))
    results = query.all()
    return [
        {
            "id": asset_owner.id,
            "name": asset_owner.name,
            "description": asset_owner.description,
            "location": location.name if location else None,
            "type": "asset_owner",
        }
        for asset_owner, location in results
    ]


def _search_applications(
    db: Session,
    search_term: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Search applications across all fields including related asset owner."""
    search_upper = search_term.upper()
    try:
        search_id = int(search_term)
    except ValueError:
        search_id = None
    
    conditions = [
        func.upper(ApplicationMapped.name).contains(search_upper),
        func.upper(ApplicationMapped.description).contains(search_upper),
        func.upper(func.to_char(ApplicationMapped.id)).contains(search_upper),
        func.upper(AssetOwner.name).contains(search_upper),
        func.upper(AssetOwner.description).contains(search_upper),
    ]
    
    if search_id is not None:
        conditions.extend([
            ApplicationMapped.id == search_id,
            ApplicationMapped.asset_owner_id == search_id,
        ])
    
    query = (
        db.query(ApplicationMapped, AssetOwner)
        .outerjoin(AssetOwner, ApplicationMapped.asset_owner_id == AssetOwner.id)
        .filter(or_(*conditions))
        .order_by(ApplicationMapped.name)
        .limit(limit)
    )
    results = query.all()
    return [
        {
            "id": application.id,
            "name": application.name,
            "description": application.description,
            "asset_owner": asset_owner.name if asset_owner else None,
            "type": "application",
        }
        for application, asset_owner in results
    ]


@router.get(
    "/search",
    response_model=Dict[str, Any],
    summary="Global search across all DCIM entities",
)
def global_search(
    q: str = Query(..., min_length=1, description="Search query string"),
    limit_per_type: int = Query(10, ge=1, le=50, description="Maximum results per entity type (max 50)"),
    access_level: AccessLevel = Depends(require_at_least_viewer),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search across ALL fields in all DCIM entities.
    
    This is a comprehensive search that searches across:
    - All string fields (name, description, status, IP, serial numbers, etc.)
    - All numeric fields (IDs, heights, positions, counts, etc.)
    - Related entity names (e.g., location names, building names, make names)
    
    Entity types searched:
    - **locations**: All fields including ID
    - **buildings**: All fields including status, location names
    - **racks**: All fields including height, space used/available, related location/building names
    - **devices**: All fields including serial number, IP, PO number, position, status, asset_user, and related entity names (location, building, rack, make, device_type, application, asset_owner)
    - **device_types**: All fields including related make names
    - **makes**: All fields
    - **models**: All fields including height and related make/device_type names
    - **datacenters**: All fields including related location/building names
    - **asset_owners**: All fields including related location names
    - **applications**: All fields including related asset_owner names
    
    Returns results grouped by entity type with a maximum number of results per type.
    All searches are case-insensitive. Numeric searches also match exact ID/number values.
    
    Example:
        GET /api/dcim/search?q=server&limit_per_type=5
        GET /api/dcim/search?q=192.168.1.1&limit_per_type=10
        GET /api/dcim/search?q=42&limit_per_type=20
    """
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty",
        )
    
    search_term = q.strip()
    allowed_location_ids = get_allowed_location_ids(current_user, access_level)
    
    # Search across all entity types
    results = {
        "query": search_term,
        "limit_per_type": limit_per_type,
        "results": {
            "locations": _search_locations(db, search_term, limit_per_type, allowed_location_ids),
            "buildings": _search_buildings(db, search_term, limit_per_type, allowed_location_ids),
            "racks": _search_racks(db, search_term, limit_per_type, allowed_location_ids),
            "devices": _search_devices(db, search_term, limit_per_type, allowed_location_ids),
            "device_types": _search_device_types(db, search_term, limit_per_type),
            "makes": _search_makes(db, search_term, limit_per_type),
            "models": _search_models(db, search_term, limit_per_type),
            "datacenters": _search_datacenters(db, search_term, limit_per_type, allowed_location_ids),
            "asset_owners": _search_asset_owners(db, search_term, limit_per_type, allowed_location_ids),
            "applications": _search_applications(db, search_term, limit_per_type),
        },
    }
    
    # Calculate totals
    total_results = sum(len(entity_results) for entity_results in results["results"].values())
    results["total"] = total_results
    
    # Add counts per type
    results["counts"] = {
        entity_type: len(entity_results)
        for entity_type, entity_results in results["results"].items()
    }
    
    return results


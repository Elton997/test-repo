# app/helpers/add_entity_helper.py
"""
Helper functions for creating DCIM entities.
Contains all entity-specific creation logic with validation.
Updated to match Alembic migrations.
Uses names instead of IDs for foreign key references.
Optimized: Uses utility functions, proper exception handling, reduced redundant queries.
"""
from typing import Any, Dict, Callable, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, exc
from sqlalchemy.orm import Session

from app.helpers.listing_types import ListingType
from app.helpers.db_utils import get_entity_by_name, check_entity_exists, db_operation
from app.helpers.rack_capacity_helper import (
    ensure_rack_capacity,
    ensure_continuous_space,
    reserve_rack_capacity,
)
from app.models.entity_models import (
    Rack,
    Device,
    DeviceType,
    Location,
    Building,
    Wing,
    Floor,
    Datacenter,
    AssetOwner,
    Make,
    Model,
    ApplicationMapped,
)


# =============================================================================
# Helper functions to resolve names to IDs (using utility functions)
# =============================================================================

def get_location_by_name(db: Session, name: str) -> Location:
    """Get location by name (case-insensitive)."""
    return get_entity_by_name(db, Location, name)


def get_building_by_name(db: Session, name: str) -> Building:
    """Get building by name (case-insensitive)."""
    return get_entity_by_name(db, Building, name)


def get_wing_by_name(db: Session, name: str) -> Wing:
    """Get wing by name (case-insensitive)."""
    return get_entity_by_name(db, Wing, name)


def get_floor_by_name(db: Session, name: str) -> Floor:
    """Get floor by name (case-insensitive)."""
    return get_entity_by_name(db, Floor, name)


def get_datacenter_by_name(db: Session, name: str) -> Datacenter:
    """Get datacenter by name (case-insensitive)."""
    return get_entity_by_name(db, Datacenter, name)


def get_rack_by_name(db: Session, name: str) -> Rack:
    """Get rack by name (case-insensitive)."""
    return get_entity_by_name(db, Rack, name)


def get_make_by_name(db: Session, name: str) -> Make:
    """Get make by name (case-insensitive)."""
    return get_entity_by_name(db, Make, name)


def get_model_by_name(db: Session, name: str) -> Model:
    """Get model by name (case-insensitive)."""
    return get_entity_by_name(db, Model, name)


def get_device_type_by_name(db: Session, name: str) -> DeviceType:
    """Get device type by name (case-insensitive)."""
    return get_entity_by_name(db, DeviceType, name)


def get_asset_owner_by_name(db: Session, name: str) -> AssetOwner:
    """Get asset owner by name (case-insensitive)."""
    return get_entity_by_name(db, AssetOwner, name)


def get_application_by_name(db: Session, name: str) -> ApplicationMapped:
    """Get application by name (case-insensitive)."""
    return get_entity_by_name(db, ApplicationMapped, name)


# =============================================================================
# Entity-specific create functions
# =============================================================================

def create_location(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new location with proper exception handling."""
    with db_operation(db, "create location"):
        # Check if location name already exists (case-insensitive)
        if check_entity_exists(db, Location, data["name"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location with name '{data['name']}' already exists",
            )
        
        location = Location(
            name=data["name"],
            description=data.get("description"),
        )
        db.add(location)
        db.commit()
        db.refresh(location)
        
        return {
            "id": location.id,
            "name": location.name,
            "description": location.description,
        }


def create_building(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new building with proper exception handling."""
    with db_operation(db, "create building"):
        # Check if building name already exists
        if check_entity_exists(db, Building, data["name"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Building with name '{data['name']}' already exists",
            )
        
        # Resolve location name to ID
        location = get_location_by_name(db, data["location_name"])
        
        building = Building(
            name=data["name"],
            status=data.get("status", "active"),
            location_id=location.id,
            description=data.get("description"),
        )
        db.add(building)
        db.commit()
        db.refresh(building)
        
        return {
            "id": building.id,
            "name": building.name,
            "status": building.status,
            "location_id": building.location_id,
            "location_name": location.name,
            "description": building.description,
        }


def create_wing(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new wing."""
    # Resolve names to IDs
    location = get_location_by_name(db, data["location_name"])
    building = get_building_by_name(db, data["building_name"])
    
    wing = Wing(
        name=data["name"],
        location_id=location.id,
        building_id=building.id,
        description=data["description"],
    )
    db.add(wing)
    db.commit()
    db.refresh(wing)
    
    return {
        "id": wing.id,
        "name": wing.name,
        "location_id": wing.location_id,
        "location_name": location.name,
        "building_id": wing.building_id,
        "building_name": building.name,
        "description": wing.description,
    }


def create_floor(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new floor."""
    # Resolve names to IDs
    location = get_location_by_name(db, data["location_name"])
    building = get_building_by_name(db, data["building_name"])
    wing = get_wing_by_name(db, data["wing_name"])
    
    floor = Floor(
        name=data["name"],
        location_id=location.id,
        building_id=building.id,
        wing_id=wing.id,
        description=data["description"],
    )
    db.add(floor)
    db.commit()
    db.refresh(floor)
    
    return {
        "id": floor.id,
        "name": floor.name,
        "location_id": floor.location_id,
        "location_name": location.name,
        "building_id": floor.building_id,
        "building_name": building.name,
        "wing_id": floor.wing_id,
        "wing_name": wing.name,
        "description": floor.description,
    }


def create_datacenter(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new datacenter."""
    # Resolve names to IDs
    location = get_location_by_name(db, data["location_name"])
    building = get_building_by_name(db, data["building_name"])
    wing = get_wing_by_name(db, data["wing_name"])
    floor = get_floor_by_name(db, data["floor_name"])
    
    datacenter = Datacenter(
        name=data["name"],
        location_id=location.id,
        building_id=building.id,
        wing_id=wing.id,
        floor_id=floor.id,
        description=data["description"],
    )
    db.add(datacenter)
    db.commit()
    db.refresh(datacenter)
    
    return {
        "id": datacenter.id,
        "name": datacenter.name,
        "location_id": datacenter.location_id,
        "location_name": location.name,
        "building_id": datacenter.building_id,
        "building_name": building.name,
        "wing_id": datacenter.wing_id,
        "wing_name": wing.name,
        "floor_id": datacenter.floor_id,
        "floor_name": floor.name,
        "description": datacenter.description,
    }


def create_rack(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new rack with proper exception handling."""
    with db_operation(db, "create rack"):
        # Check if rack name already exists
        if check_entity_exists(db, Rack, data["name"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Rack with name '{data['name']}' already exists",
            )
        
        # Resolve names to IDs
        location = get_location_by_name(db, data["location_name"])
        building = get_building_by_name(db, data["building_name"])
        wing = get_wing_by_name(db, data["wing_name"])
        floor = get_floor_by_name(db, data["floor_name"])
        datacenter = get_datacenter_by_name(db, data["datacenter_name"])
        
        # Height is required according to UI requirements
        height = data.get("height")
        if height is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Height is required for rack creation",
            )
        
        rack = Rack(
            name=data["name"],
            building_id=building.id,
            location_id=location.id,
            wing_id=wing.id,
            floor_id=floor.id,
            datacenter_id=datacenter.id,
            status=data.get("status", "active"),
            width=data.get("width"),
            height=height,
            space_used=0,
            space_available=height,
            description=data.get("description"),
        )
        db.add(rack)
        db.commit()
        db.refresh(rack)
        
        return {
            "id": rack.id,
            "name": rack.name,
            "location_id": rack.location_id,
            "location_name": location.name,
            "building_id": rack.building_id,
            "building_name": building.name,
            "wing_id": rack.wing_id,
            "wing_name": wing.name,
            "floor_id": rack.floor_id,
            "floor_name": floor.name,
            "datacenter_id": rack.datacenter_id,
            "datacenter_name": datacenter.name,
            "status": rack.status,
            "height": rack.height,
            "space_used": rack.space_used,
            "space_available": rack.space_available,
            "created_at": rack.created_at,
        }


def create_device(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new device with proper exception handling and optimized lookups."""
    with db_operation(db, "create device"):
        # Resolve all required names to IDs (could be optimized with batch lookup in future)
        location = get_location_by_name(db, data["location_name"])
        building = get_building_by_name(db, data["building_name"])
        rack = get_rack_by_name(db, data["rack_name"])
        device_type = get_device_type_by_name(db, data["devicetype_name"])
        make = get_make_by_name(db, data["make_name"])
        model = get_model_by_name(db, data["model_name"])
        datacenter = get_datacenter_by_name(db, data["datacenter_name"])
        wing = get_wing_by_name(db, data["wing_name"])
        floor = get_floor_by_name(db, data["floor_name"])
        asset_owner = get_asset_owner_by_name(db, data["asset_owner_name"])
        application = get_application_by_name(db, data["application_name"])
    
    # Ensure make compatibility
    if model.make_id != make.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model.name}' belongs to a different make",
        )
    
    # Align device type automatically if needed
    if model.device_type_id != device_type.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model.name}' is not linked to device type '{device_type.name}'",
        )
    
    def _validate_date_range(label: str, start_date, end_date) -> None:
        if start_date and end_date and end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{label} end date cannot be before start date",
            )

    _validate_date_range(
        "Warranty",
        data.get("warranty_start_date"),
        data.get("warranty_end_date"),
    )
    _validate_date_range(
        "AMC",
        data.get("amc_start_date"),
        data.get("amc_end_date"),
    )

    # Update application's asset_owner if different
    if application.asset_owner_id != asset_owner.id:
        application.asset_owner_id = asset_owner.id
    
    space_required = model.height
    if not space_required or space_required <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model.name}' has invalid height and cannot determine rack space",
        )

    # Get position (required for device placement)
    position = data.get("position")
    if position is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position is required for device placement",
        )
    
    # Validate continuous space availability at the specified position
    ensure_continuous_space(db, rack, position, space_required)
    
    # Also check overall rack capacity (for informational purposes)
    ensure_rack_capacity(rack, space_required)
    
    face_value = data.pop("face", None)
    face_front = data.get("face_front")
    face_rear = data.get("face_rear")

    def _face_bool(value: Optional[str]) -> tuple[bool, bool]:
        if not value:
            return False, False
        value = value.lower()
        if value == "front":
            return True, False
        if value == "rear":
            return False, True
        if value == "both":
            return True, True
        # default fallback
        return True, True

    if face_value:
        face_front, face_rear = _face_bool(face_value)

    if face_front is None:
        face_front = True
    if face_rear is None:
        face_rear = face_front  # default behavior keeps rear true for front placements

    device = Device(
        name=data["name"],
        serial_no=data.get("serial_no"),
        position=position,
        face_front=face_front,
        face_rear=face_rear,
        status=data.get("status", "active"),
        building_id=building.id,
        location_id=location.id,
        rack_id=rack.id,
        devicetype_id=device_type.id,
        make_id=make.id,
        dc_id=datacenter.id,
        wings_id=wing.id,
        floor_id=floor.id,
        ip=data.get("ip"),
        po_number=data.get("po_number"),
        asset_user=data.get("asset_user", "instock"),
        applications_mapped_id=application.id,
        warranty_start_date=data.get("warranty_start_date"),
        warranty_end_date=data.get("warranty_end_date"),
        amc_start_date=data.get("amc_start_date"),
        amc_end_date=data.get("amc_end_date"),
        space_required=space_required,
        description=data.get("description"),
        front_image_path=data.get("front_image_path"),
        rear_image_path=data.get("rear_image_path"),
    )
    db.add(device)
    reserve_rack_capacity(rack, space_required)
    db.commit()
    db.refresh(device)
    
    return {
        "id": device.id,
        "name": device.name,
        "serial_no": device.serial_no,
        "position": device.position,
        "face_front": device.face_front,
        "face_rear": device.face_rear,
        "status": device.status,
        "location_name": location.name,
        "building_name": building.name,
        "rack_name": rack.name,
        "model_name": model.name,
        "asset_owner_name": asset_owner.name,
        "created_at": device.created_at,
        "front_image_path": device.front_image_path,
        "rear_image_path": device.rear_image_path,
    }


def create_device_type(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new device type with proper exception handling."""
    with db_operation(db, "create device type"):
        # Check if device type name already exists
        if check_entity_exists(db, DeviceType, data["name"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device type with name '{data['name']}' already exists",
            )
        
        # Resolve names to IDs
        make = get_make_by_name(db, data["make_name"])
        device_type = DeviceType(
            name=data["name"],
            make_id=make.id,
            description=data.get("description"),
        )
        db.add(device_type)
        db.commit()
        db.refresh(device_type)
        
        return {
            "id": device_type.id,
            "name": device_type.name,
            "make_id": device_type.make_id,
            "make_name": make.name,
        }


def create_asset_owner(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new asset owner."""
    # Resolve location name to ID
    location = get_location_by_name(db, data["location_name"])
    
    asset_owner = AssetOwner(
        name=data["name"],
        location_id=location.id,
        description=data["description"],
    )
    db.add(asset_owner)
    db.commit()
    db.refresh(asset_owner)
    
    return {
        "id": asset_owner.id,
        "name": asset_owner.name,
        "location_id": asset_owner.location_id,
        "location_name": location.name,
    }


def create_make(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new make with proper exception handling."""
    with db_operation(db, "create make"):
        # Check if make name already exists
        if check_entity_exists(db, Make, data["name"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Make with name '{data['name']}' already exists",
            )
        
        make = Make(
            name=data["name"],
            description=data.get("description"),
        )
        db.add(make)
        db.commit()
        db.refresh(make)
        
        return {
            "id": make.id,
            "name": make.name,
        }


def create_model(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new model with proper exception handling."""
    with db_operation(db, "create model"):
        # Check if model name already exists
        if check_entity_exists(db, Model, data["name"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Model with name '{data['name']}' already exists",
            )
        
        # Resolve make name to ID
        make = get_make_by_name(db, data["make_name"])
        device_type = get_device_type_by_name(db, data["devicetype_name"])
        if device_type.make_id != make.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Device type '{device_type.name}' belongs to a different make",
            )
        model = Model(
            name=data["name"],
            make_id=make.id,
            device_type_id=device_type.id,
            height=data["height"],
            description=data.get("description"),
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        
        return {
            "id": model.id,
            "name": model.name,
            "make_id": model.make_id,
            "make_name": make.name,
            "device_type_id": model.device_type_id,
            "device_type_name": device_type.name,
            "height": model.height,
        }


def create_application(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new application mapped."""
    # Resolve asset owner name to ID
    asset_owner = get_asset_owner_by_name(db, data["asset_owner_name"])
    
    application = ApplicationMapped(
        name=data["name"],
        asset_owner_id=asset_owner.id,
        description=data["description"],
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return {
        "id": application.id,
        "name": application.name,
        "asset_owner_id": application.asset_owner_id,
        "asset_owner_name": asset_owner.name,
    }


# =============================================================================
# Entity handler mapping
# =============================================================================

ENTITY_CREATE_HANDLERS: Dict[ListingType, Callable[[Session, Dict[str, Any]], Dict[str, Any]]] = {
    ListingType.locations: create_location,
    ListingType.buildings: create_building,
    ListingType.wings: create_wing,
    ListingType.floors: create_floor,
    ListingType.datacenters: create_datacenter,
    ListingType.racks: create_rack,
    ListingType.devices: create_device,
    ListingType.device_types: create_device_type,
    ListingType.asset_owner: create_asset_owner,
    ListingType.makes: create_make,
    ListingType.models: create_model,
    ListingType.applications: create_application,
}

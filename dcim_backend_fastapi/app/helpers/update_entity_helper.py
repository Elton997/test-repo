# app/helpers/update_entity_helper.py
"""
Helper functions for updating DCIM entities.
Contains all entity-specific update logic with validation.
Updated to match Alembic migrations.
Optimized: Uses utility functions, proper exception handling, reduced redundant queries.
"""
from typing import Any, Dict, Callable

from fastapi import HTTPException, status
from sqlalchemy import func, exc
from sqlalchemy.orm import Session

from app.helpers.listing_types import ListingType
from app.helpers.db_utils import get_entity_by_name, check_entity_exists, db_operation
from app.helpers.rack_capacity_helper import (
    ensure_continuous_space,
    reserve_rack_capacity,
    release_rack_capacity,
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
# Entity-specific update functions
# =============================================================================

def update_location(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing location by name with proper exception handling."""
    with db_operation(db, "update location"):
        location = get_entity_by_name(db, Location, entity_name)
        
        # Check if new name conflicts with existing location (case-insensitive)
        if "name" in data and func.upper(data["name"]) != func.upper(location.name):
            if check_entity_exists(db, Location, data["name"], exclude_id=location.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Location with name '{data['name']}' already exists",
                )
            location.name = data["name"]
        
        if "description" in data:
            location.description = data["description"]
        
        db.commit()
        db.refresh(location)
        
        return {
            "id": location.id,
            "name": location.name,
            "description": location.description,
        }


def update_building(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing building by name."""
    building = db.query(Building).filter(func.upper(Building.name) == func.upper(entity_name)).first()
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with name '{entity_name}' not found",
        )
    
    # Check if new name conflicts with existing building (case-insensitive)
    if "name" in data and func.upper(data["name"]) != func.upper(building.name):
        existing = db.query(Building).filter(func.upper(Building.name) == func.upper(data["name"])).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Building with name '{data['name']}' already exists",
            )
        building.name = data["name"]
    
    # Verify location exists if updating
    if "location_name" in data:
        location = db.query(Location).filter(func.upper(Location.name) == func.upper(data["location_name"])).first()
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location with name '{data['location_name']}' not found",
            )
        building.location_id = location.id
    
    if "status" in data:
        building.status = data["status"]
    if "description" in data:
        building.description = data["description"]
    
    db.commit()
    db.refresh(building)
    
    return {
        "id": building.id,
        "name": building.name,
        "status": building.status,
        "location_id": building.location_id,
    }


def update_wing(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing wing by name."""
    wing = db.query(Wing).filter(func.upper(Wing.name) == func.upper(entity_name)).first()
    if not wing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wing with name '{entity_name}' not found",
        )
    
    if "name" in data:
        wing.name = data["name"]
    if "location_name" in data:
        location = db.query(Location).filter(func.upper(Location.name) == func.upper(data["location_name"])).first()
        if not location:
            raise HTTPException(status_code=404, detail=f"Location '{data['location_name']}' not found")
        wing.location_id = location.id
    if "building_name" in data:
        building = db.query(Building).filter(func.upper(Building.name) == func.upper(data["building_name"])).first()
        if not building:
            raise HTTPException(status_code=404, detail=f"Building '{data['building_name']}' not found")
        wing.building_id = building.id
    if "description" in data:
        wing.description = data["description"]
    
    db.commit()
    db.refresh(wing)
    
    return {"id": wing.id, "name": wing.name, "location_id": wing.location_id, "building_id": wing.building_id}


def update_floor(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing floor by name."""
    floor = db.query(Floor).filter(func.upper(Floor.name) == func.upper(entity_name)).first()
    if not floor:
        raise HTTPException(status_code=404, detail=f"Floor with name '{entity_name}' not found")
    
    if "name" in data:
        floor.name = data["name"]
    if "location_name" in data:
        location = db.query(Location).filter(func.upper(Location.name) == func.upper(data["location_name"])).first()
        if not location:
            raise HTTPException(status_code=404, detail=f"Location '{data['location_name']}' not found")
        floor.location_id = location.id
    if "building_name" in data:
        building = db.query(Building).filter(func.upper(Building.name) == func.upper(data["building_name"])).first()
        if not building:
            raise HTTPException(status_code=404, detail=f"Building '{data['building_name']}' not found")
        floor.building_id = building.id
    if "wing_name" in data:
        wing = db.query(Wing).filter(func.upper(Wing.name) == func.upper(data["wing_name"])).first()
        if not wing:
            raise HTTPException(status_code=404, detail=f"Wing '{data['wing_name']}' not found")
        floor.wing_id = wing.id
    if "description" in data:
        floor.description = data["description"]
    
    db.commit()
    db.refresh(floor)
    
    return {"id": floor.id, "name": floor.name}


def update_datacenter(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing datacenter by name."""
    datacenter = db.query(Datacenter).filter(func.upper(Datacenter.name) == func.upper(entity_name)).first()
    if not datacenter:
        raise HTTPException(status_code=404, detail=f"Datacenter with name '{entity_name}' not found")
    
    if "name" in data:
        datacenter.name = data["name"]
    if "location_name" in data:
        location = db.query(Location).filter(func.upper(Location.name) == func.upper(data["location_name"])).first()
        if not location:
            raise HTTPException(status_code=404, detail=f"Location '{data['location_name']}' not found")
        datacenter.location_id = location.id
    if "building_name" in data:
        building = db.query(Building).filter(func.upper(Building.name) == func.upper(data["building_name"])).first()
        if not building:
            raise HTTPException(status_code=404, detail=f"Building '{data['building_name']}' not found")
        datacenter.building_id = building.id
    if "wing_name" in data:
        wing = db.query(Wing).filter(func.upper(Wing.name) == func.upper(data["wing_name"])).first()
        if not wing:
            raise HTTPException(status_code=404, detail=f"Wing '{data['wing_name']}' not found")
        datacenter.wing_id = wing.id
    if "floor_name" in data:
        floor = db.query(Floor).filter(func.upper(Floor.name) == func.upper(data["floor_name"])).first()
        if not floor:
            raise HTTPException(status_code=404, detail=f"Floor '{data['floor_name']}' not found")
        datacenter.floor_id = floor.id
    if "description" in data:
        datacenter.description = data["description"]
    
    db.commit()
    db.refresh(datacenter)
    
    return {"id": datacenter.id, "name": datacenter.name}


def update_rack(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing rack by name."""
    rack = db.query(Rack).filter(func.upper(Rack.name) == func.upper(entity_name)).first()
    if not rack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rack with name '{entity_name}' not found",
        )
    
    # Check if new name conflicts with existing rack (case-insensitive)
    if "name" in data and func.upper(data["name"]) != func.upper(rack.name):
        existing = db.query(Rack).filter(func.upper(Rack.name) == func.upper(data["name"])).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Rack with name '{data['name']}' already exists",
            )
    
    # Verify building exists if updating
    if "building_name" in data:
        building = db.query(Building).filter(func.upper(Building.name) == func.upper(data["building_name"])).first()
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building with name '{data['building_name']}' not found",
            )
        rack.building_id = building.id
    
    # Verify location exists if updating
    if "location_name" in data:
        location = db.query(Location).filter(func.upper(Location.name) == func.upper(data["location_name"])).first()
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location with name '{data['location_name']}' not found",
            )
        rack.location_id = location.id
    
    # Verify wing exists if updating
    if "wing_name" in data:
        wing = db.query(Wing).filter(func.upper(Wing.name) == func.upper(data["wing_name"])).first()
        if not wing:
            raise HTTPException(status_code=404, detail=f"Wing '{data['wing_name']}' not found")
        rack.wing_id = wing.id
    
    # Verify floor exists if updating
    if "floor_name" in data:
        floor = db.query(Floor).filter(func.upper(Floor.name) == func.upper(data["floor_name"])).first()
        if not floor:
            raise HTTPException(status_code=404, detail=f"Floor '{data['floor_name']}' not found")
        rack.floor_id = floor.id
    
    # Verify datacenter exists if updating
    if "datacenter_name" in data:
        datacenter = db.query(Datacenter).filter(func.upper(Datacenter.name) == func.upper(data["datacenter_name"])).first()
        if not datacenter:
            raise HTTPException(status_code=404, detail=f"Datacenter '{data['datacenter_name']}' not found")
        rack.datacenter_id = datacenter.id
    
    # Update other fields
    updatable_fields = ["status", "description"]
    for field in updatable_fields:
        if field in data:
            setattr(rack, field, data[field])
    
    # Update name separately if provided (after uniqueness check)
    if "name" in data:
        rack.name = data["name"]

    if "height" in data:
        new_height = data["height"]
        if new_height is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rack height cannot be null",
            )
        if new_height < (rack.space_used or 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot reduce rack height below the used space "
                    f"({rack.space_used or 0}U)"
                ),
            )
        rack.height = new_height
        rack.space_available = max(new_height - (rack.space_used or 0), 0)
    
    db.commit()
    db.refresh(rack)
    
    return {
        "id": rack.id,
        "name": rack.name,
        "building_id": rack.building_id,
        "location_id": rack.location_id,
        "status": rack.status,
        "height": rack.height,
        "space_used": rack.space_used,
        "space_available": rack.space_available,
        "last_updated": rack.last_updated,
    }


def update_device(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing device by name with proper exception handling."""
    with db_operation(db, "update device"):
        device = get_entity_by_name(db, Device, entity_name)
        
        # Verify building exists if updating
        if "building_name" in data:
            building = get_entity_by_name(db, Building, data["building_name"])
            device.building_id = building.id
    
        original_rack = device.rack
        target_rack = device.rack

        # Verify rack exists if updating
        if "rack_name" in data:
            rack_name = data["rack_name"]
            if rack_name:
                rack = get_entity_by_name(db, Rack, rack_name)
                target_rack = rack
                device.rack_id = rack.id
            else:
                target_rack = None
                device.rack_id = None
        
        # Verify device type exists if updating
        if "devicetype_name" in data:
            device_type = get_entity_by_name(db, DeviceType, data["devicetype_name"])
            device.devicetype_id = device_type.id
        
        # Verify location exists if updating
        if "location_name" in data:
            location = get_entity_by_name(db, Location, data["location_name"])
            device.location_id = location.id
        
        # Verify make exists if updating
        if "make_name" in data:
            make = get_entity_by_name(db, Make, data["make_name"])
            device.make_id = make.id
        
        # Verify datacenter exists if updating
        if "datacenter_name" in data:
            datacenter = get_entity_by_name(db, Datacenter, data["datacenter_name"])
            device.dc_id = datacenter.id
        
        # Verify wing exists if updating
        if "wing_name" in data:
            wing = get_entity_by_name(db, Wing, data["wing_name"])
            device.wings_id = wing.id
        
        # Verify floor exists if updating
        if "floor_name" in data:
            floor = get_entity_by_name(db, Floor, data["floor_name"])
            device.floor_id = floor.id
        
        # Verify application exists if updating
        if "application_name" in data:
            application = get_entity_by_name(db, ApplicationMapped, data["application_name"])
            device.applications_mapped_id = application.id
    
        # Handle face value from frontend (Front/Rear) - case insensitive
        face_value = data.pop("face", None)
        if face_value:
            # Convert face value to face_front and face_rear booleans
            # - face=Front -> face_front=True, face_rear=True
            # - face=Rear -> face_front=False, face_rear=True
            if face_value.lower() == "front":
                data["face_front"] = True
                data["face_rear"] = True
            elif face_value.lower() == "rear":
                data["face_front"] = False
                data["face_rear"] = True

        # Update other fields
        # Note: front_image_path and rear_image_path are now on Model, not Device
        updatable_fields = [
            "name",
            "serial_no",
            "position",
            "face_front",
            "face_rear",
            "status",
            "ip",
            "po_number",
            "asset_user",
            "warranty_start_date",
            "warranty_end_date",
            "amc_start_date",
            "amc_end_date",
            "space_required",
            "description",
        ]
        
        # Determine new/effective space requirements before mutating rack capacity
        def _effective_space(value: Any, rack_present: bool) -> int:
            if value and value > 0:
                return value
            return 1 if rack_present else 0

        original_space_effective = _effective_space(device.space_required, bool(original_rack))

        if "space_required" in data:
            new_space_value = data["space_required"]
            if new_space_value is None or new_space_value <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="space_required must be greater than zero",
                )
        else:
            new_space_value = device.space_required

        target_rack_obj = target_rack
        effective_space_required = _effective_space(new_space_value, bool(target_rack_obj))

        # Validate position and continuous space availability
        position = data.get("position", device.position)
        if target_rack_obj and position is not None:
            # Validate continuous space availability (excluding current device from overlap check)
            ensure_continuous_space(
                db,
                target_rack_obj,
                position,
                effective_space_required,
                exclude_device_id=device.id,
            )

        same_rack = original_rack and target_rack_obj and original_rack.id == target_rack_obj.id
        if same_rack:
            if effective_space_required != original_space_effective:
                release_rack_capacity(original_rack, original_space_effective)
                try:
                    reserve_rack_capacity(target_rack_obj, effective_space_required)
                except HTTPException:
                    reserve_rack_capacity(original_rack, original_space_effective)
                    raise
        else:
            if original_rack:
                release_rack_capacity(original_rack, original_space_effective)
            if target_rack_obj:
                reserve_rack_capacity(target_rack_obj, effective_space_required)

        for field in updatable_fields:
            if field in data:
                setattr(device, field, data[field])
        
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
            "building_id": device.building_id,
            "rack_id": device.rack_id,
            "last_updated": device.last_updated,
        }


def update_device_type(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing device type by name."""
    device_type = db.query(DeviceType).filter(func.upper(DeviceType.name) == func.upper(entity_name)).first()
    if not device_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device type with name '{entity_name}' not found",
        )
    
    # Check if new name conflicts with existing device type (case-insensitive)
    if "name" in data and func.upper(data["name"]) != func.upper(device_type.name):
        existing = db.query(DeviceType).filter(func.upper(DeviceType.name) == func.upper(data["name"])).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device type with name '{data['name']}' already exists",
            )
    
    # Verify make exists if updating
    if "make_name" in data:
        make = db.query(Make).filter(func.upper(Make.name) == func.upper(data["make_name"])).first()
        if not make:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Make with name '{data['make_name']}' not found",
            )
        device_type.make_id = make.id
    
    if "name" in data:
        device_type.name = data["name"]
    if "description" in data:
        device_type.description = data["description"]
    
    db.commit()
    db.refresh(device_type)
    
    return {
        "id": device_type.id,
        "name": device_type.name,
        "make_id": device_type.make_id,
    }


def update_asset_owner(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing asset owner by name."""
    asset_owner = db.query(AssetOwner).filter(func.upper(AssetOwner.name) == func.upper(entity_name)).first()
    if not asset_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset owner with name '{entity_name}' not found",
        )
    
    # Verify location exists if updating
    if "location_name" in data:
        location = db.query(Location).filter(func.upper(Location.name) == func.upper(data["location_name"])).first()
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location with name '{data['location_name']}' not found",
            )
        asset_owner.location_id = location.id
    
    if "name" in data:
        asset_owner.name = data["name"]
    if "description" in data:
        asset_owner.description = data["description"]
    
    db.commit()
    db.refresh(asset_owner)
    
    return {
        "id": asset_owner.id,
        "name": asset_owner.name,
        "location_id": asset_owner.location_id,
    }


def update_make(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing make by name."""
    make = db.query(Make).filter(func.upper(Make.name) == func.upper(entity_name)).first()
    if not make:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Make with name '{entity_name}' not found",
        )
    
    # Check if new name conflicts with existing make (case-insensitive)
    if "name" in data and func.upper(data["name"]) != func.upper(make.name):
        existing = db.query(Make).filter(func.upper(Make.name) == func.upper(data["name"])).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Make with name '{data['name']}' already exists",
            )
    
    if "name" in data:
        make.name = data["name"]
    if "description" in data:
        make.description = data["description"]
    
    db.commit()
    db.refresh(make)
    
    return {
        "id": make.id,
        "name": make.name,
    }


def update_model(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing model by name."""
    model = db.query(Model).filter(func.upper(Model.name) == func.upper(entity_name)).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with name '{entity_name}' not found",
        )
    
    # Check if new name conflicts with existing model (case-insensitive)
    if "name" in data and func.upper(data["name"]) != func.upper(model.name):
        existing = db.query(Model).filter(func.upper(Model.name) == func.upper(data["name"])).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Model with name '{data['name']}' already exists",
            )
    
    # Verify make exists if updating
    if "make_name" in data:
        make = db.query(Make).filter(func.upper(Make.name) == func.upper(data["make_name"])).first()
        if not make:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Make with name '{data['make_name']}' not found",
            )
        model.make_id = make.id
    
    if "devicetype_name" in data:
        device_type = db.query(DeviceType).filter(func.upper(DeviceType.name) == func.upper(data["devicetype_name"])).first()
        if not device_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device type with name '{data['devicetype_name']}' not found",
            )
        model.device_type_id = device_type.id
    
    if "height" in data:
        model.height = data["height"]
    
    if "name" in data:
        model.name = data["name"]
    if "description" in data:
        model.description = data["description"]
    
    # Handle image paths
    if "front_image_path" in data:
        model.front_image_path = data["front_image_path"]
    if "rear_image_path" in data:
        model.rear_image_path = data["rear_image_path"]
    
    db.commit()
    db.refresh(model)
    
    return {
        "id": model.id,
        "name": model.name,
        "make_id": model.make_id,
        "device_type_id": model.device_type_id,
        "height": model.height,
        "front_image_path": model.front_image_path,
        "rear_image_path": model.rear_image_path,
    }


def update_application(db: Session, entity_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing application by name."""
    application = db.query(ApplicationMapped).filter(func.upper(ApplicationMapped.name) == func.upper(entity_name)).first()
    if not application:
        raise HTTPException(status_code=404, detail=f"Application with name '{entity_name}' not found")
    
    if "name" in data:
        application.name = data["name"]
    if "asset_owner_name" in data:
        asset_owner = db.query(AssetOwner).filter(func.upper(AssetOwner.name) == func.upper(data["asset_owner_name"])).first()
        if not asset_owner:
            raise HTTPException(status_code=404, detail=f"Asset owner '{data['asset_owner_name']}' not found")
        application.asset_owner_id = asset_owner.id
    if "description" in data:
        application.description = data["description"]
    
    db.commit()
    db.refresh(application)
    
    return {"id": application.id, "name": application.name, "asset_owner_id": application.asset_owner_id}


# =============================================================================
# Entity handler mapping
# =============================================================================

ENTITY_UPDATE_HANDLERS: Dict[ListingType, Callable[[Session, str, Dict[str, Any]], Dict[str, Any]]] = {
    ListingType.locations: update_location,
    ListingType.buildings: update_building,
    ListingType.wings: update_wing,
    ListingType.floors: update_floor,
    ListingType.datacenters: update_datacenter,
    ListingType.racks: update_rack,
    ListingType.devices: update_device,
    ListingType.device_types: update_device_type,
    ListingType.asset_owner: update_asset_owner,
    ListingType.makes: update_make,
    ListingType.models: update_model,
    ListingType.applications: update_application,
}

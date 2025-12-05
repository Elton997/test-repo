# app/helpers/delete_entity_helper.py
"""
Helper functions for deleting DCIM entities.
Contains all entity-specific deletion logic with validation.
Updated to match Alembic migrations.
Optimized: Uses utility functions, proper exception handling.
"""
from typing import Any, Dict, Callable

from fastapi import HTTPException, status
from sqlalchemy import func, exc
from sqlalchemy.orm import Session

from app.helpers.listing_types import ListingType
from app.helpers.db_utils import get_entity_by_name, db_operation
from app.helpers.rack_capacity_helper import release_rack_capacity
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
# Entity-specific delete functions
# =============================================================================

def delete_location(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a location by name with proper exception handling."""
    with db_operation(db, "delete location"):
        location = get_entity_by_name(db, Location, entity_name)
        
        location_data = {
            "id": location.id,
            "name": location.name,
        }
        
        db.delete(location)
        db.commit()
        
        return location_data


def delete_building(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a building by name."""
    building = db.query(Building).filter(func.upper(Building.name) == func.upper(entity_name)).first()
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with name '{entity_name}' not found",
        )
    
    building_data = {
        "id": building.id,
        "name": building.name,
        "status": building.status,
        "location_id": building.location_id,
    }
    
    db.delete(building)
    db.commit()
    
    return building_data


def delete_wing(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a wing by name."""
    wing = db.query(Wing).filter(func.upper(Wing.name) == func.upper(entity_name)).first()
    if not wing:
        raise HTTPException(status_code=404, detail=f"Wing with name '{entity_name}' not found")
    
    wing_data = {"id": wing.id, "name": wing.name}
    db.delete(wing)
    db.commit()
    return wing_data


def delete_floor(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a floor by name."""
    floor = db.query(Floor).filter(func.upper(Floor.name) == func.upper(entity_name)).first()
    if not floor:
        raise HTTPException(status_code=404, detail=f"Floor with name '{entity_name}' not found")
    
    floor_data = {"id": floor.id, "name": floor.name}
    db.delete(floor)
    db.commit()
    return floor_data


def delete_datacenter(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a datacenter by name."""
    datacenter = db.query(Datacenter).filter(func.upper(Datacenter.name) == func.upper(entity_name)).first()
    if not datacenter:
        raise HTTPException(status_code=404, detail=f"Datacenter with name '{entity_name}' not found")
    
    datacenter_data = {"id": datacenter.id, "name": datacenter.name}
    db.delete(datacenter)
    db.commit()
    return datacenter_data


def delete_rack(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a rack by name."""
    rack = db.query(Rack).filter(func.upper(Rack.name) == func.upper(entity_name)).first()
    if not rack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rack with name '{entity_name}' not found",
        )
    
    rack_data = {
        "id": rack.id,
        "name": rack.name,
        "building_id": rack.building_id,
        "location_id": rack.location_id,
        "status": rack.status,
    }
    
    db.delete(rack)
    db.commit()
    
    return rack_data


def delete_device(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a device by name with proper exception handling."""
    with db_operation(db, "delete device"):
        device = get_entity_by_name(db, Device, entity_name)
        
        device_data = {
            "id": device.id,
            "name": device.name,
            "serial_no": device.serial_no,
            "position": device.position,
            "face_front": device.face_front,
            "face_rear": device.face_rear,
            "status": device.status,
            "building_id": device.building_id,
            "rack_id": device.rack_id,
            "front_image_path": device.front_image_path,
            "rear_image_path": device.rear_image_path,
        }
        
        # Delete associated image files if they exist
        from app.helpers.image_helper import delete_device_image
        if device.front_image_path:
            delete_device_image(device.front_image_path)
        if device.rear_image_path:
            delete_device_image(device.rear_image_path)
        
        if device.rack:
            used_space = device.space_required if device.space_required and device.space_required > 0 else 1
            release_rack_capacity(device.rack, used_space)

        db.delete(device)
        db.commit()
        
        return device_data


def delete_device_type(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a device type by name."""
    device_type = db.query(DeviceType).filter(func.upper(DeviceType.name) == func.upper(entity_name)).first()
    if not device_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device type with name '{entity_name}' not found",
        )
    
    device_type_data = {
        "id": device_type.id,
        "name": device_type.name,
        "make_id": device_type.make_id,
    }
    
    db.delete(device_type)
    db.commit()
    
    return device_type_data


def delete_asset_owner(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete an asset owner by name."""
    asset_owner = db.query(AssetOwner).filter(func.upper(AssetOwner.name) == func.upper(entity_name)).first()
    if not asset_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset owner with name '{entity_name}' not found",
        )
    
    asset_owner_data = {
        "id": asset_owner.id,
        "name": asset_owner.name,
        "location_id": asset_owner.location_id,
    }
    
    db.delete(asset_owner)
    db.commit()
    
    return asset_owner_data


def delete_make(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a make by name."""
    make = db.query(Make).filter(func.upper(Make.name) == func.upper(entity_name)).first()
    if not make:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Make with name '{entity_name}' not found",
        )
    
    make_data = {
        "id": make.id,
        "name": make.name,
    }
    
    db.delete(make)
    db.commit()
    
    return make_data


def delete_model(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete a model by name."""
    model = db.query(Model).filter(func.upper(Model.name) == func.upper(entity_name)).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with name '{entity_name}' not found",
        )
    
    model_data = {
        "id": model.id,
        "name": model.name,
        "make_id": model.make_id,
    }
    
    db.delete(model)
    db.commit()
    
    return model_data


def delete_application(db: Session, entity_name: str) -> Dict[str, Any]:
    """Delete an application by name."""
    application = db.query(ApplicationMapped).filter(func.upper(ApplicationMapped.name) == func.upper(entity_name)).first()
    if not application:
        raise HTTPException(status_code=404, detail=f"Application with name '{entity_name}' not found")
    
    application_data = {"id": application.id, "name": application.name}
    db.delete(application)
    db.commit()
    return application_data


# =============================================================================
# Entity handler mapping
# =============================================================================

ENTITY_DELETE_HANDLERS: Dict[ListingType, Callable[[Session, str], Dict[str, Any]]] = {
    ListingType.locations: delete_location,
    ListingType.buildings: delete_building,
    ListingType.wings: delete_wing,
    ListingType.floors: delete_floor,
    ListingType.datacenters: delete_datacenter,
    ListingType.racks: delete_rack,
    ListingType.devices: delete_device,
    ListingType.device_types: delete_device_type,
    ListingType.asset_owner: delete_asset_owner,
    ListingType.makes: delete_make,
    ListingType.models: delete_model,
    ListingType.applications: delete_application,
}

# app/helpers/details_helper.py
"""
Helper functions for retrieving detailed DCIM entity information.
Contains all entity-specific detail logic with nested relationships.
Updated to match Alembic migrations.
Optimized for performance with combined queries and eager loading.
"""
from typing import Any, Dict, Callable

from fastapi import HTTPException, status
from sqlalchemy import func, exc
from sqlalchemy.orm import Session, joinedload

from app.helpers.listing_types import ListingType
from app.helpers.db_utils import get_entity_by_name, db_operation
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
# Entity-specific detail functions
# =============================================================================

def get_wing_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific wing by name."""
    wing = (
        db.query(Wing)
        .options(
            joinedload(Wing.location),
            joinedload(Wing.building),
        )
        .filter(func.upper(Wing.name) == func.upper(entity_name))
        .first()
    )
    
    if not wing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wing with name '{entity_name}' not found",
        )

    # Get floors in this wing
    floors = db.query(Floor).filter(Floor.wing_id == wing.id).all()
    
    # Get stats
    total_racks = (
        db.query(func.count(Rack.id))
        .filter(Rack.wing_id == wing.id)
        .scalar() or 0
    )
    
    total_devices = (
        db.query(func.count(Device.id))
        .filter(Device.wings_id == wing.id)
        .scalar() or 0
    )

    return {
        "id": wing.id,
        "name": wing.name,
        "description": wing.description,
        "location": {
            "id": wing.location.id if wing.location else None,
            "name": wing.location.name if wing.location else None,
        },
        "building": {
            "id": wing.building.id if wing.building else None,
            "name": wing.building.name if wing.building else None,
        },
        "floors": [
            {"id": f.id, "name": f.name}
            for f in floors
        ],
        "stats": {
            "total_floors": len(floors),
            "total_racks": total_racks,
            "total_devices": total_devices,
        },
    }


def get_floor_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific floor by name."""
    floor = (
        db.query(Floor)
        .options(
            joinedload(Floor.location),
            joinedload(Floor.building),
            joinedload(Floor.wing),
        )
        .filter(func.upper(Floor.name) == func.upper(entity_name))
        .first()
    )
    
    if not floor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor with name '{entity_name}' not found",
        )

    # Get datacenters on this floor
    datacenters = db.query(Datacenter).filter(Datacenter.floor_id == floor.id).all()
    
    # Get stats
    total_racks = (
        db.query(func.count(Rack.id))
        .filter(Rack.floor_id == floor.id)
        .scalar() or 0
    )
    
    total_devices = (
        db.query(func.count(Device.id))
        .filter(Device.floor_id == floor.id)
        .scalar() or 0
    )

    return {
        "id": floor.id,
        "name": floor.name,
        "description": floor.description,
        "location": {
            "id": floor.location.id if floor.location else None,
            "name": floor.location.name if floor.location else None,
        },
        "building": {
            "id": floor.building.id if floor.building else None,
            "name": floor.building.name if floor.building else None,
        },
        "wing": {
            "id": floor.wing.id if floor.wing else None,
            "name": floor.wing.name if floor.wing else None,
        },
        "datacenters": [
            {"id": dc.id, "name": dc.name}
            for dc in datacenters
        ],
        "stats": {
            "total_datacenters": len(datacenters),
            "total_racks": total_racks,
            "total_devices": total_devices,
        },
    }


def get_datacenter_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific datacenter by name."""
    datacenter = (
        db.query(Datacenter)
        .options(
            joinedload(Datacenter.location),
            joinedload(Datacenter.building),
            joinedload(Datacenter.wing),
            joinedload(Datacenter.floor),
        )
        .filter(func.upper(Datacenter.name) == func.upper(entity_name))
        .first()
    )
    
    if not datacenter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datacenter with name '{entity_name}' not found",
        )

    # Get racks in this datacenter
    racks = db.query(Rack).filter(Rack.datacenter_id == datacenter.id).all()
    
    # Calculate stats
    total_devices = (
        db.query(func.count(Device.id))
        .filter(Device.dc_id == datacenter.id)
        .scalar() or 0
    )

    total_capacity = sum(r.height or 0 for r in racks)
    used_space = sum(r.space_used or 0 for r in racks)
    available_space = sum(
        (r.space_available if r.space_available is not None else max((r.height or 0) - (r.space_used or 0), 0))
        for r in racks
    )

    return {
        "id": datacenter.id,
        "name": datacenter.name,
        "description": datacenter.description,
        "location": {
            "id": datacenter.location.id if datacenter.location else None,
            "name": datacenter.location.name if datacenter.location else None,
        },
        "building": {
            "id": datacenter.building.id if datacenter.building else None,
            "name": datacenter.building.name if datacenter.building else None,
        },
        "wing": {
            "id": datacenter.wing.id if datacenter.wing else None,
            "name": datacenter.wing.name if datacenter.wing else None,
        },
        "floor": {
            "id": datacenter.floor.id if datacenter.floor else None,
            "name": datacenter.floor.name if datacenter.floor else None,
        },
        "racks": [
            {
                "id": r.id,
                "name": r.name,
                "status": r.status,
                "height": r.height,
            }
            for r in racks
        ],
        "stats": {
            "total_racks": len(racks),
            "total_devices": total_devices,
            "total_capacity": total_capacity,
            "used_space": used_space,
            "available_space": available_space,
        },
    }


def get_rack_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific rack by name.
    Optimized: Explicit joins instead of lazy loading, single query for devices.
    """
    try:
        # Optimize: Use explicit joins instead of lazy loading
        rack_data = (
            db.query(
                Rack,
                Location,
                Building,
                Wing,
                Floor,
                Datacenter
            )
            .outerjoin(Location, Rack.location_id == Location.id)
            .outerjoin(Building, Rack.building_id == Building.id)
            .outerjoin(Wing, Rack.wing_id == Wing.id)
            .outerjoin(Floor, Rack.floor_id == Floor.id)
            .outerjoin(Datacenter, Rack.datacenter_id == Datacenter.id)
            .filter(func.upper(Rack.name) == func.upper(entity_name))
            .first()
        )
        
        if not rack_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rack with name '{entity_name}' not found",
            )
        
        rack, location, building, wing, floor, datacenter = rack_data

        # Optimize: Get devices with related info in single query (including Model for image paths)
        devices_data = (
            db.query(
                Device,
                DeviceType,
                Make,
                Model
            )
            .outerjoin(DeviceType, Device.devicetype_id == DeviceType.id)
            .outerjoin(Make, Device.make_id == Make.id)
            .outerjoin(Model, Model.device_type_id == DeviceType.id)
            .filter(Device.rack_id == rack.id)
            .order_by(Device.position.asc())
            .all()
        )

        used_space = rack.space_used or 0
        available_space = rack.space_available
        if available_space is None:
            available_space = (rack.height or 0) - used_space

        return {
            "id": rack.id,
            "name": rack.name,
            "status": rack.status,
            "width": rack.width,
            "height": rack.height,
            "description": rack.description,
            "created_at": rack.created_at,
            "last_updated": rack.last_updated,
            "location": {
                "id": location.id if location else None,
                "name": location.name if location else None,
            },
            "building": {
                "id": building.id if building else None,
                "name": building.name if building else None,
            },
            "wing": {
                "id": wing.id if wing else None,
                "name": wing.name if wing else None,
            },
            "floor": {
                "id": floor.id if floor else None,
                "name": floor.name if floor else None,
            },
            "datacenter": {
                "id": datacenter.id if datacenter else None,
                "name": datacenter.name if datacenter else None,
            },
            "devices": [
                {
                    "id": device.id,
                    "name": device.name,
                    "position": device.position,
                    "face_front": device.face_front,
                    "face_rear": device.face_rear,
                    "status": device.status,
                    "space_required": device.space_required,
                    "device_type": device_type.name if device_type else None,
                    "make": make.name if make else None,
                    "front_image_path": model.front_image_path if model else None,
                    "rear_image_path": model.rear_image_path if model else None,
                }
                for device, device_type, make, model in devices_data
            ],
            "stats": {
                "total_devices": len(devices_data),
                "total_height": rack.height or 0,
                "used_space": used_space,
                "available_space": available_space,
                "utilization_percent": (
                    round((used_space / rack.height * 100), 2) if rack.height else 0
                ),
            },
        }
    except HTTPException:
        raise
    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error in get_rack_details: {str(e)}",
        )


def get_device_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific device by name.
    Optimized: Explicit joins instead of lazy loading, single query for devices in same rack.
    """
    try:
        device = (
            db.query(Device)
            .options(
                joinedload(Device.location),
                joinedload(Device.building),
                joinedload(Device.wing),
                joinedload(Device.floor),
                joinedload(Device.datacenter),
                joinedload(Device.rack),
                joinedload(Device.device_type).joinedload(DeviceType.models),
                joinedload(Device.make),
                joinedload(Device.application_mapped).joinedload(ApplicationMapped.asset_owner),
            )
            .filter(func.upper(Device.name) == func.upper(entity_name))
            .first()
        )
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with name '{entity_name}' not found",
            )

        primary_model = None
        if device.device_type and device.device_type.models:
            primary_model = device.device_type.models[0]

        # Optimize: Get devices in the same rack with related info in single query (including Model for image paths)
        devices_data = []
        if device.rack_id:
            devices_data = (
                db.query(
                    Device,
                    DeviceType,
                    Make,
                    Model
                )
                .outerjoin(DeviceType, Device.devicetype_id == DeviceType.id)
                .outerjoin(Make, Device.make_id == Make.id)
                .outerjoin(Model, Model.device_type_id == DeviceType.id)
                .filter(Device.rack_id == device.rack_id)
                .order_by(Device.position.asc())
                .all()
            )

        return {
            "id": device.id,
            "name": device.name,
            "serial_no": device.serial_no,
            "status": device.status,
            "position": device.position,
            "face_front": device.face_front,
            "face_rear": device.face_rear,
            "space_required": device.space_required,
            "ip": device.ip,
            "po_number": device.po_number,
            "asset_user": device.asset_user,
            "description": device.description,
            "front_image_path": primary_model.front_image_path if primary_model else None,
            "rear_image_path": primary_model.rear_image_path if primary_model else None,
            "created_at": device.created_at,
            "last_updated": device.last_updated,
            "location": {
                "id": device.location.id if device.location else None,
                "name": device.location.name if device.location else None,
            },
            "building": {
                "id": device.building.id if device.building else None,
                "name": device.building.name if device.building else None,
            },
            "wing": {
                "id": device.wing.id if device.wing else None,
                "name": device.wing.name if device.wing else None,
            },
            "floor": {
                "id": device.floor.id if device.floor else None,
                "name": device.floor.name if device.floor else None,
            },
            "datacenter": {
                "id": device.datacenter.id if device.datacenter else None,
                "name": device.datacenter.name if device.datacenter else None,
            },
            "rack": {
                "id": device.rack.id if device.rack else None,
                "name": device.rack.name if device.rack else None,
            },
            "device_type": {
                "id": device.device_type.id if device.device_type else None,
                "name": device.device_type.name if device.device_type else None,
                "height": primary_model.height if primary_model else None,
                "model": {
                    "id": primary_model.id if primary_model else None,
                    "name": primary_model.name if primary_model else None,
                    "height": primary_model.height if primary_model else None,
                },
            },
            "make": {
                "id": device.make.id if device.make else None,
                "name": device.make.name if device.make else None,
            },
            "application": {
                "id": device.application_mapped.id if device.application_mapped else None,
                "name": device.application_mapped.name if device.application_mapped else None,
                "asset_owner": {
                    "id": device.application_mapped.asset_owner.id if device.application_mapped and device.application_mapped.asset_owner else None,
                    "name": device.application_mapped.asset_owner.name if device.application_mapped and device.application_mapped.asset_owner else None,
                } if device.application_mapped else None,
            },
            "devices": [
                {
                    "id": d.id,
                    "name": d.name,
                    "position": d.position,
                    "face_front": d.face_front,
                    "face_rear": d.face_rear,
                    "status": d.status,
                    "space_required": d.space_required,
                    "device_type": dt.name if dt else None,
                    "make": make.name if make else None,
                    "front_image_path": m.front_image_path if m else None,
                    "rear_image_path": m.rear_image_path if m else None,
                }
                for d, dt, make, m in devices_data
            ],
            "warranty": {
                "start_date": device.warranty_start_date,
                "end_date": device.warranty_end_date,
            },
            "amc": {
                "start_date": device.amc_start_date,
                "end_date": device.amc_end_date,
            },
        }
    except HTTPException:
        raise
    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error in get_device_details: {str(e)}",
        )


def get_device_type_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific device type by name."""
    device_type = (
        db.query(DeviceType)
        .options(
            joinedload(DeviceType.make),
            joinedload(DeviceType.models),
        )
        .filter(func.upper(DeviceType.name) == func.upper(entity_name))
        .first()
    )
    
    if not device_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device type with name '{entity_name}' not found",
        )

    # Count devices using this type
    device_count = (
        db.query(func.count(Device.id))
        .filter(Device.devicetype_id == device_type.id)
        .scalar() or 0
    )

    primary_model = device_type.models[0] if device_type.models else None

    return {
        "id": device_type.id,
        "name": device_type.name,
        "description": device_type.description,
        "make": {
            "id": device_type.make.id if device_type.make else None,
            "name": device_type.make.name if device_type.make else None,
        },
        "model": {
            "id": primary_model.id if primary_model else None,
            "name": primary_model.name if primary_model else None,
            "height": primary_model.height if primary_model else None,
            "front_image_path": primary_model.front_image_path if primary_model else None,
            "rear_image_path": primary_model.rear_image_path if primary_model else None,
        },
        "height": primary_model.height if primary_model else None,
        "front_image_path": primary_model.front_image_path if primary_model else None,
        "rear_image_path": primary_model.rear_image_path if primary_model else None,
        "stats": {
            "device_count": device_count,
            "model_count": len(device_type.models),
        },
    }


def get_asset_owner_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific asset owner by name."""
    asset_owner = (
        db.query(AssetOwner)
        .options(joinedload(AssetOwner.location))
        .filter(func.upper(AssetOwner.name) == func.upper(entity_name))
        .first()
    )
    
    if not asset_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset owner with name '{entity_name}' not found",
        )

    # Get applications for this owner
    applications = (
        db.query(ApplicationMapped)
        .filter(ApplicationMapped.asset_owner_id == asset_owner.id)
        .all()
    )

    return {
        "id": asset_owner.id,
        "name": asset_owner.name,
        "description": asset_owner.description,
        "location": {
            "id": asset_owner.location.id if asset_owner.location else None,
            "name": asset_owner.location.name if asset_owner.location else None,
        },
        "applications": [
            {"id": app.id, "name": app.name}
            for app in applications
        ],
        "stats": {
            "total_applications": len(applications),
        },
    }


def get_make_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific make by name."""
    make = (
        db.query(Make)
        .filter(func.upper(Make.name) == func.upper(entity_name))
        .first()
    )
    
    if not make:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Make with name '{entity_name}' not found",
        )

    # Get models
    models = (
        db.query(Model)
        .filter(Model.make_id == make.id)
        .all()
    )

    # Get device types
    device_types = (
        db.query(DeviceType)
        .filter(DeviceType.make_id == make.id)
        .all()
    )

    # Stats
    device_count = (
        db.query(func.count(Device.id))
        .filter(Device.make_id == make.id)
        .scalar() or 0
    )
    
    rack_count = (
        db.query(func.count(func.distinct(Device.rack_id)))
        .filter(Device.make_id == make.id)
        .scalar() or 0
    )

    return {
        "id": make.id,
        "name": make.name,
        "description": make.description,
        "models": [
            {"id": m.id, "name": m.name}
            for m in models
        ],
        "device_types": [
            {
                "id": dt.id,
                "name": dt.name,
                "height": dt.models[0].height if dt.models else None,
            }
            for dt in device_types
        ],
        "stats": {
            "total_models": len(models),
            "total_device_types": len(device_types),
            "total_devices": device_count,
            "total_racks": rack_count,
        },
    }


def get_model_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific model by name."""
    model = (
        db.query(Model)
        .options(
            joinedload(Model.make),
            joinedload(Model.device_type),
        )
        .filter(func.upper(Model.name) == func.upper(entity_name))
        .first()
    )
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with name '{entity_name}' not found",
        )

    device_types = []
    if model.device_type:
        device_types.append(
            {
                "id": model.device_type.id,
                "name": model.device_type.name,
                "height": model.height,
            }
        )

    return {
        "id": model.id,
        "name": model.name,
        "height": model.height,
        "description": model.description,
        "front_image_path": model.front_image_path,
        "rear_image_path": model.rear_image_path,
        "make": {
            "id": model.make.id if model.make else None,
            "name": model.make.name if model.make else None,
        },
        "device_type": device_types[0] if device_types else None,
        "stats": {
            "total_device_types": len(device_types),
        },
    }


def get_application_details(db: Session, entity_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific application by name."""
    application = (
        db.query(ApplicationMapped)
        .options(joinedload(ApplicationMapped.asset_owner))
        .filter(func.upper(ApplicationMapped.name) == func.upper(entity_name))
        .first()
    )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with name '{entity_name}' not found",
        )

    # Get devices using this application
    devices = (
        db.query(Device)
        .filter(Device.applications_mapped_id == application.id)
        .all()
    )

    return {
        "id": application.id,
        "name": application.name,
        "description": application.description,
        "asset_owner": {
            "id": application.asset_owner.id if application.asset_owner else None,
            "name": application.asset_owner.name if application.asset_owner else None,
        },
        "devices": [
            {"id": d.id, "name": d.name, "status": d.status}
            for d in devices
        ],
        "stats": {
            "total_devices": len(devices),
        },
    }


# =============================================================================
# Entity handler mapping
# =============================================================================

ENTITY_DETAIL_HANDLERS: Dict[ListingType, Callable[[Session, str], Dict[str, Any]]] = {
    ListingType.wings: get_wing_details,
    ListingType.floors: get_floor_details,
    ListingType.datacenters: get_datacenter_details,
    ListingType.racks: get_rack_details,
    ListingType.devices: get_device_details,
    ListingType.device_types: get_device_type_details,
    ListingType.asset_owner: get_asset_owner_details,
    ListingType.makes: get_make_details,
    ListingType.models: get_model_details,
    ListingType.applications: get_application_details,
}
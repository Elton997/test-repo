# app/schemas/entity_schemas.py
"""
Pydantic schemas for DCIM entity validation.
Includes output (response), create, and update schemas for all entities.
Updated to match Alembic migrations.
"""
from datetime import datetime, date
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.helpers.listing_types import ListingType


# =============================================================================
# Location Schemas
# =============================================================================

class LocationOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class LocationCreate(BaseModel):
    """Schema for creating a new location."""
    name: str = Field(..., min_length=1, max_length=255, description="Location name")
    description: str = Field(..., min_length=1, max_length=255, description="Location description")


class LocationUpdate(BaseModel):
    """Schema for updating a location."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Building Schemas
# =============================================================================

class BuildingOut(BaseModel):
    id: int
    name: str
    status: str
    location_id: int
    description: Optional[str] = None

    class Config:
        from_attributes = True


class BuildingCreate(BaseModel):
    """Schema for creating a new building."""
    name: str = Field(..., min_length=1, max_length=255, description="Building name")
    status: str = Field(..., min_length=1, max_length=255, description="Building status")
    location_name: str = Field(..., min_length=1, max_length=255, description="Location name")
    description: str = Field(..., min_length=1, max_length=255, description="Building description")


class BuildingUpdate(BaseModel):
    """Schema for updating a building."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, max_length=255)
    location_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Wing Schemas
# =============================================================================

class WingOut(BaseModel):
    id: int
    name: str
    location_id: int
    building_id: int
    description: Optional[str] = None

    class Config:
        from_attributes = True


class WingCreate(BaseModel):
    """Schema for creating a new wing."""
    name: str = Field(..., min_length=1, max_length=255, description="Wing name")
    location_name: str = Field(..., min_length=1, max_length=255, description="Location name")
    building_name: str = Field(..., min_length=1, max_length=255, description="Building name")
    description: str = Field(..., min_length=1, max_length=255, description="Wing description")


class WingUpdate(BaseModel):
    """Schema for updating a wing."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location_id: Optional[int] = Field(None, gt=0)
    building_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Floor Schemas
# =============================================================================

class FloorOut(BaseModel):
    id: int
    name: str
    location_id: int
    building_id: int
    wing_id: int
    description: Optional[str] = None

    class Config:
        from_attributes = True


class FloorCreate(BaseModel):
    """Schema for creating a new floor."""
    name: str = Field(..., min_length=1, max_length=255, description="Floor name")
    location_name: str = Field(..., min_length=1, max_length=255, description="Location name")
    building_name: str = Field(..., min_length=1, max_length=255, description="Building name")
    wing_name: str = Field(..., min_length=1, max_length=255, description="Wing name")
    description: str = Field(..., min_length=1, max_length=255, description="Floor description")


class FloorUpdate(BaseModel):
    """Schema for updating a floor."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location_id: Optional[int] = Field(None, gt=0)
    building_id: Optional[int] = Field(None, gt=0)
    wing_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Datacenter Schemas
# =============================================================================

class DatacenterOut(BaseModel):
    id: int
    name: str
    location_id: int
    building_id: int
    wing_id: int
    floor_id: int
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DatacenterCreate(BaseModel):
    """Schema for creating a new datacenter."""
    name: str = Field(..., min_length=1, max_length=255, description="Datacenter name")
    location_name: str = Field(..., min_length=1, max_length=255, description="Location name")
    building_name: str = Field(..., min_length=1, max_length=255, description="Building name")
    wing_name: str = Field(..., min_length=1, max_length=255, description="Wing name")
    floor_name: str = Field(..., min_length=1, max_length=255, description="Floor name")
    description: str = Field(..., min_length=1, max_length=255, description="Datacenter description")


class DatacenterUpdate(BaseModel):
    """Schema for updating a datacenter."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location_id: Optional[int] = Field(None, gt=0)
    building_id: Optional[int] = Field(None, gt=0)
    wing_id: Optional[int] = Field(None, gt=0)
    floor_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Rack Schemas
# =============================================================================

class RackOut(BaseModel):
    id: int
    name: str
    building_id: int
    location_id: int
    wing_id: int
    floor_id: int
    datacenter_id: int
    status: str
    width: Optional[int] = None
    height: Optional[int] = None
    space_used: int
    space_available: int
    created_at: datetime
    last_updated: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RackCreate(BaseModel):
    """Schema for creating a new rack."""
    name: str = Field(..., min_length=1, max_length=255, description="Rack name")
    location_name: str = Field(..., min_length=1, max_length=255, description="Location name")
    building_name: str = Field(..., min_length=1, max_length=255, description="Building name")
    wing_name: str = Field(..., min_length=1, max_length=255, description="Wing name")
    floor_name: str = Field(..., min_length=1, max_length=255, description="Floor name")
    datacenter_name: str = Field(..., min_length=1, max_length=255, description="Datacenter name (data center)")
    status: str = Field(..., min_length=1, max_length=255, description="Rack status")
    width: int = Field(..., gt=0, description="Rack width")
    height: int = Field(..., gt=0, description="Rack height in U (required)")
    description: str = Field(..., min_length=1, max_length=255, description="Rack description")


class RackUpdate(BaseModel):
    """Schema for updating a rack."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    building_id: Optional[int] = Field(None, gt=0)
    location_id: Optional[int] = Field(None, gt=0)
    wing_id: Optional[int] = Field(None, gt=0)
    floor_id: Optional[int] = Field(None, gt=0)
    datacenter_id: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(None, max_length=255)
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Make Schemas
# =============================================================================

class MakeOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class MakeCreate(BaseModel):
    """Schema for creating a new make."""
    name: str = Field(..., min_length=1, max_length=255, description="Make name")
    description: str = Field(..., min_length=1, max_length=255, description="Make description")


class MakeUpdate(BaseModel):
    """Schema for updating a make."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Model Schemas (formerly Module)
# =============================================================================

class ModelOut(BaseModel):
    id: int
    name: str
    make_id: int
    device_type_id: int
    height: int
    description: Optional[str] = None
    front_image_path: Optional[str] = None
    rear_image_path: Optional[str] = None

    class Config:
        from_attributes = True


class ModelCreate(BaseModel):
    """Schema for creating a new model."""
    name: str = Field(..., min_length=1, max_length=255, description="Model name")
    make_name: str = Field(..., min_length=1, max_length=255, description="Make name")
    devicetype_name: str = Field(..., min_length=1, max_length=255, description="Device type name")
    height: int = Field(..., gt=0, description="Model height in U")
    description: str = Field(..., min_length=1, max_length=255, description="Model description")


class ModelUpdate(BaseModel):
    """Schema for updating a model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    make_id: Optional[int] = Field(None, gt=0)
    make_name: Optional[str] = Field(None, min_length=1, max_length=255)
    devicetype_name: Optional[str] = Field(None, max_length=255)
    height: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Device Type Schemas
# =============================================================================

class DeviceTypeOut(BaseModel):
    id: int
    name: str
    make_id: int
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DeviceTypeCreate(BaseModel):
    """Schema for creating a new device type."""
    name: str = Field(..., min_length=1, max_length=255, description="Device type name")
    make_name: str = Field(..., min_length=1, max_length=255, description="Make name")
    description: str = Field(..., min_length=1, max_length=255, description="Device type description")


class DeviceTypeUpdate(BaseModel):
    """Schema for updating a device type."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    make_id: Optional[int] = Field(None, gt=0)
    make_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Asset Owner Schemas
# =============================================================================

class AssetOwnerOut(BaseModel):
    id: int
    name: str
    location_id: Optional[int] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AssetOwnerCreate(BaseModel):
    """Schema for creating a new asset owner."""
    name: str = Field(..., min_length=1, max_length=255, description="Asset owner name")
    location_name: str = Field(..., min_length=1, max_length=255, description="Location name")
    description: str = Field(..., min_length=1, max_length=255, description="Asset owner description")


class AssetOwnerUpdate(BaseModel):
    """Schema for updating an asset owner."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Application Mapped Schemas
# =============================================================================

class ApplicationMappedOut(BaseModel):
    id: int
    name: str
    asset_owner_id: Optional[int] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ApplicationMappedCreate(BaseModel):
    """Schema for creating a new application mapped."""
    name: str = Field(..., min_length=1, max_length=255, description="Application name")
    asset_owner_name: str = Field(..., min_length=1, max_length=255, description="Asset Owner name")
    description: str = Field(..., min_length=1, max_length=255, description="Application description")


class ApplicationMappedUpdate(BaseModel):
    """Schema for updating an application mapped."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    asset_owner_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=255)


# =============================================================================
# Device Schemas
# =============================================================================

class DeviceOut(BaseModel):
    id: int
    name: str
    serial_no: Optional[str] = None
    position: Optional[int] = None
    face_front: bool
    face_rear: bool
    status: str
    devicetype_id: Optional[int] = None
    building_id: int
    location_id: int
    rack_id: Optional[int] = None
    dc_id: Optional[int] = None
    wings_id: Optional[int] = None
    floor_id: Optional[int] = None
    make_id: Optional[int] = None
    ip: Optional[str] = None
    po_number: Optional[str] = None
    asset_user: str
    applications_mapped_id: Optional[int] = None
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    amc_start_date: Optional[date] = None
    amc_end_date: Optional[date] = None
    space_required: Optional[int] = None
    created_at: datetime
    last_updated: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True


class DeviceCreate(BaseModel):
    """Schema for creating a new device."""
    name: str = Field(..., min_length=1, max_length=255, description="Device name")
    serial_no: str = Field(..., min_length=1, max_length=255, description="Serial number")
    position: int = Field(..., ge=0, description="Position in rack (U)")
    face: str = Field(..., min_length=1, max_length=255, description="Device face (Front/Rear)")
    status: str = Field(..., min_length=1, max_length=255, description="Device status")
    
    devicetype_name: str = Field(..., min_length=1, max_length=255, description="Device Type name")
    location_name: str = Field(..., min_length=1, max_length=255, description="Location name (required)")
    building_name: str = Field(..., min_length=1, max_length=255, description="Building name (required)")
    rack_name: str = Field(..., min_length=1, max_length=255, description="Rack name")
    datacenter_name: str = Field(..., min_length=1, max_length=255, description="Datacenter name")
    wing_name: str = Field(..., min_length=1, max_length=255, description="Wing name")
    floor_name: str = Field(..., min_length=1, max_length=255, description="Floor name")
    make_name: str = Field(..., min_length=1, max_length=255, description="Make name")
    model_name: str = Field(..., min_length=1, max_length=255, description="Model name")
    
    ip: str = Field(..., min_length=1, max_length=255, description="IP address")
    po_number: str = Field(..., min_length=1, max_length=255, description="PO number")
    asset_user: str = Field(..., min_length=1, max_length=255, description="Asset user status")
    asset_owner_name: str = Field(..., min_length=1, max_length=255, description="Asset owner name")
    application_name: str = Field(..., min_length=1, max_length=255, description="Application name (applications_mapped_name)")
    
    warranty_start_date: date = Field(..., description="Warranty start date")
    warranty_end_date: date = Field(..., description="Warranty end date")
    amc_start_date: date = Field(..., description="AMC start date")
    amc_end_date: date = Field(..., description="AMC end date")
    
    description: str = Field(..., min_length=1, max_length=255, description="Device description")
    # Note: image is handled separately via multipart form data, not in this schema

    model_config = ConfigDict(protected_namespaces=())


class DeviceUpdate(BaseModel):
    """Schema for updating a device."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    serial_no: Optional[str] = Field(None, max_length=255)
    position: Optional[int] = Field(None, ge=0)
    face: Optional[str] = Field(None, max_length=255, description="Device face (Front/Rear)")
    status: Optional[str] = Field(None, max_length=255)
    
    devicetype_id: Optional[int] = None
    building_id: Optional[int] = Field(None, gt=0)
    location_id: Optional[int] = Field(None, gt=0)
    rack_id: Optional[int] = None
    dc_id: Optional[int] = None
    wings_id: Optional[int] = None
    floor_id: Optional[int] = None
    make_id: Optional[int] = None
    
    ip: Optional[str] = Field(None, max_length=255)
    po_number: Optional[str] = Field(None, max_length=255)
    asset_user: Optional[str] = Field(None, max_length=255)
    applications_mapped_id: Optional[int] = None
    
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    amc_start_date: Optional[date] = None
    amc_end_date: Optional[date] = None
    
    description: Optional[str] = Field(None, max_length=255)
    # Note: images are handled separately via multipart form data, not in this schema


# =============================================================================
# Schema mapping for validation
# =============================================================================

ENTITY_CREATE_SCHEMAS: Dict[ListingType, type[BaseModel]] = {
    ListingType.locations: LocationCreate,
    ListingType.buildings: BuildingCreate,
    ListingType.wings: WingCreate,
    ListingType.floors: FloorCreate,
    ListingType.datacenters: DatacenterCreate,
    ListingType.racks: RackCreate,
    ListingType.devices: DeviceCreate,
    ListingType.device_types: DeviceTypeCreate,
    ListingType.asset_owner: AssetOwnerCreate,
    ListingType.makes: MakeCreate,
    ListingType.models: ModelCreate,
    ListingType.applications: ApplicationMappedCreate,
}

ENTITY_UPDATE_SCHEMAS: Dict[ListingType, type[BaseModel]] = {
    ListingType.locations: LocationUpdate,
    ListingType.buildings: BuildingUpdate,
    ListingType.wings: WingUpdate,
    ListingType.floors: FloorUpdate,
    ListingType.datacenters: DatacenterUpdate,
    ListingType.racks: RackUpdate,
    ListingType.devices: DeviceUpdate,
    ListingType.device_types: DeviceTypeUpdate,
    ListingType.asset_owner: AssetOwnerUpdate,
    ListingType.makes: MakeUpdate,
    ListingType.models: ModelUpdate,
    ListingType.applications: ApplicationMappedUpdate,
}

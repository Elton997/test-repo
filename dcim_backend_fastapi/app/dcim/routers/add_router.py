"""
DCIM Add Router - Generic API for creating new DCIM entities.
Supports creating entities of any type via a single parameterized endpoint.
"""
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.helpers.rbac_helper import AccessLevel, require_editor_or_admin
from app.helpers.listing_types import ListingType
from app.helpers.auth_helper import get_current_user
from app.helpers.audit_helper import build_audit_context, log_create
from app.helpers.listing_cache import invalidate_listing_cache_for_entity
from app.helpers.summary_cache import invalidate_location_summary_cache
from app.models.auth_models import User
from app.helpers.image_helper import save_device_image, delete_device_image

router = APIRouter(prefix="/api/dcim", tags=["DCIM Add"])


def _get_create_handlers():
    """Lazy import to avoid loading heavy helper modules at startup."""
    from app.helpers.add_entity_helper import ENTITY_CREATE_HANDLERS

    return ENTITY_CREATE_HANDLERS


def _get_create_schemas():
    """Lazy import for schema definitions."""
    from app.schemas.entity_schemas import ENTITY_CREATE_SCHEMAS

    return ENTITY_CREATE_SCHEMAS


def check_required_fields(entity: ListingType, data: Dict[str, Any]) -> None:
    """
    Field checker function to validate that all required fields are present in the data.
    
    Args:
        entity: The entity type being created
        data: The data dictionary to validate
        
    Raises:
        HTTPException: If any required fields are missing
    """
    # Get the schema class to determine required fields
    schema_class = _get_create_schemas().get(entity)
    if not schema_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {entity}",
        )
    
    # Get all field names from the schema
    schema_fields = set(schema_class.model_fields.keys())
    
    # Get fields present in the data
    data_fields = set(data.keys())
    
    # Find missing required fields
    missing_fields = schema_fields - data_fields
    
    if missing_fields:
        missing_fields_list = sorted(list(missing_fields))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields for {entity.value}: {', '.join(missing_fields_list)}",
        )
    
    # Check for empty string values (which should be considered missing)
    empty_fields = []
    for field in schema_fields:
        if field in data:
            value = data[field]
            # Check if value is None, empty string, or empty after stripping
            if value is None or (isinstance(value, str) and not value.strip()):
                empty_fields.append(field)
    
    if empty_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Empty or null values found for required fields in {entity.value}: {', '.join(empty_fields)}",
        )
    
    # Check for extra fields that are not in the schema (optional validation)
    extra_fields = data_fields - schema_fields
    if extra_fields:
        # Log warning but don't fail - just ignore extra fields
        pass


def check_row_uniqueness(entity: ListingType, data: Dict[str, Any], db: Session) -> None:
    """
    Check if a complete row already exists in the database.
    This is important for entities that don't have name as a unique key.
    
    Args:
        entity: The entity type being created
        data: The data dictionary containing all field values
        db: Database session
        
    Raises:
        HTTPException: If a duplicate row is found
    """
    from app.helpers.add_entity_helper import (
        get_location_by_name,
        get_building_by_name,
        get_wing_by_name,
        get_floor_by_name,
        get_datacenter_by_name,
        get_asset_owner_by_name,
    )
    from app.models.entity_models import Wing, Floor, Datacenter, ApplicationMapped
    
    # Entities that don't have name as unique key need full row uniqueness check
    if entity == ListingType.wings:
        # Wing: unique by (name, location_id, building_id)
        location = get_location_by_name(db, data["location_name"])
        building = get_building_by_name(db, data["building_name"])
        
        existing = (
            db.query(Wing)
            .filter(func.upper(Wing.name) == func.upper(data["name"]))
            .filter(Wing.location_id == location.id)
            .filter(Wing.building_id == building.id)
            .first()
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Wing with name '{data['name']}' already exists in location '{data['location_name']}' and building '{data['building_name']}'",
            )
    
    elif entity == ListingType.floors:
        # Floor: unique by (name, location_id, building_id, wing_id)
        location = get_location_by_name(db, data["location_name"])
        building = get_building_by_name(db, data["building_name"])
        wing = get_wing_by_name(db, data["wing_name"])
        
        existing = (
            db.query(Floor)
            .filter(func.upper(Floor.name) == func.upper(data["name"]))
            .filter(Floor.location_id == location.id)
            .filter(Floor.building_id == building.id)
            .filter(Floor.wing_id == wing.id)
            .first()
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Floor with name '{data['name']}' already exists in location '{data['location_name']}', building '{data['building_name']}', and wing '{data['wing_name']}'",
            )
    
    elif entity == ListingType.datacenters:
        # Datacenter: unique by (name, location_id, building_id, wing_id, floor_id)
        location = get_location_by_name(db, data["location_name"])
        building = get_building_by_name(db, data["building_name"])
        wing = get_wing_by_name(db, data["wing_name"])
        floor = get_floor_by_name(db, data["floor_name"])
        
        existing = (
            db.query(Datacenter)
            .filter(func.upper(Datacenter.name) == func.upper(data["name"]))
            .filter(Datacenter.location_id == location.id)
            .filter(Datacenter.building_id == building.id)
            .filter(Datacenter.wing_id == wing.id)
            .filter(Datacenter.floor_id == floor.id)
            .first()
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Datacenter with name '{data['name']}' already exists in location '{data['location_name']}', building '{data['building_name']}', wing '{data['wing_name']}', and floor '{data['floor_name']}'",
            )
    
    elif entity == ListingType.applications:
        # ApplicationMapped: unique by (name, asset_owner_id)
        asset_owner = get_asset_owner_by_name(db, data["asset_owner_name"])
        
        existing = (
            db.query(ApplicationMapped)
            .filter(func.upper(ApplicationMapped.name) == func.upper(data["name"]))
            .filter(ApplicationMapped.asset_owner_id == asset_owner.id)
            .first()
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Application with name '{data['name']}' already exists for asset owner '{data['asset_owner_name']}'",
            )
    
    # For entities with unique name constraints (locations, buildings, racks, etc.),
    # the uniqueness check is already handled in their respective create handlers


@router.post(
    "/add",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Generic DCIM add API - Create new entity by type",
)
async def add_entity(
    request: Request,
    entity: ListingType = Query(
        ...,
        description=(
            "Entity type to create: racks | devices | device_types | "
            "locations | buildings | datacenters | asset_owner | makes | models"
        ),
    ),
    access_level: AccessLevel = Depends(require_editor_or_admin),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Single endpoint to create any DCIM entity.
    
    **Required access level:** Editor or Admin
    
    **Note:** All foreign key references use names instead of IDs for easier API usage.
    
    **For models with images:**
    - Use `multipart/form-data` content type
    - Send `data` as a JSON string in a form field
    - Optional file fields: `front_image` and/or `rear_image`
    
    **For other entities or models without images:**
    - Use `application/json` content type  
    - Send JSON object directly in request body (will be parsed automatically)
    
    **Entity types and required fields (ALL FIELDS ARE MANDATORY):**
    
    - **locations**: `name`, `description`
    - **buildings**: `name`, `status`, `location_name`, `description`
    - **datacenters**: `name`, `location_name`, `building_name`, `wing_name`, `floor_name`, `description`
    - **racks**: `name`, `location_name`, `building_name`, `wing_name`, `floor_name`, `datacenter_name`, `status`, `width`, `height`, `description`
    - **devices**: `name`, `serial_no`, `position`, `face`, `status`, `devicetype_name`, `location_name`, `building_name`, `rack_name`, `datacenter_name`, `wing_name`, `floor_name`, `make_name`, `model_name`, `ip`, `po_number`, `asset_user`, `asset_owner_name`, `application_name`, `warranty_start_date`, `warranty_end_date`, `amc_start_date`, `amc_end_date`, `description`
    - **device_types**: `name`, `make_name`, `description`
    - **asset_owner**: `name`, `location_name`, `description`
    - **makes**: `name`, `description`
    - **models**: `name`, `make_name`, `devicetype_name`, `height`, `description`
    - **applications**: `name`, `asset_owner_name`, `description`
    
    **Note:** For bulk upload of wings, floors, and datacenters, use the `/bulk-upload-hierarchy` endpoint.
    
    Returns the created entity with its generated ID.
    """
    # Check content type and parse accordingly
    content_type = request.headers.get("content-type", "").lower()
    data_dict = None
    front_image_file = None
    rear_image_file = None
    
    if "multipart/form-data" in content_type:
        # Handle multipart/form-data (for devices with images)
        form = await request.form()
        
        # Debug: Check what fields are available
        form_keys = list(form.keys()) if hasattr(form, 'keys') else []
        
        # Try to get data field - check both 'data' and possible variations
        data_str = form.get("data")
        if not data_str:
            # Try alternative field names
            data_str = form.get("json") or form.get("body") or form.get("payload")
        
        front_image_file = form.get("front_image")
        rear_image_file = form.get("rear_image")
        
        if not data_str:
            available_fields = ", ".join(form_keys) if form_keys else "none"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'data' field is required when using multipart/form-data. Available form fields: {available_fields}. Please send device data as a JSON string in a form field named 'data'.",
            )
        
        # Ensure data_str is a string
        if not isinstance(data_str, str):
            data_str = str(data_str)
        
        # Check if data_str is empty after stripping
        if not data_str.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="'data' field cannot be empty. Please provide device data as a JSON string.",
            )
        
        try:
            data_dict = json.loads(data_str)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in data field: {str(e)}. Make sure 'data' contains a valid JSON string. Received: {data_str[:100] if len(data_str) > 100 else data_str}",
            )
    else:
        # Handle application/json (for regular requests)
        try:
            data_dict = await request.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request body. For devices with images, use multipart/form-data with 'data' field. For others, use application/json. Error: {str(e)}",
            )
    
    # Validate image is only provided for models
    if (front_image_file or rear_image_file) and entity != ListingType.models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image upload is only supported for models, not {entity.value}",
        )
    
    # Prevent creating wings and floors through this endpoint (use bulk upload instead)
    if entity in [ListingType.wings, ListingType.floors]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Creating {entity.value} is not supported through this endpoint. Please use the /bulk-upload-hierarchy endpoint for bulk upload of wings, floors, and datacenters.",
        )
    
    # Field checker: Validate all required fields are present
    check_required_fields(entity, data_dict)
    
    # Get the schema for validation
    schema_class = _get_create_schemas().get(entity)
    if not schema_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {entity}",
        )
    
    # Validate input data against schema
    try:
        validated_data = schema_class(**data_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}",
        )
    
    # Check for complete row uniqueness (for entities without unique name constraints)
    check_row_uniqueness(entity, validated_data.model_dump(), db)
    
    # Handle image upload for models
    front_image_path = None
    rear_image_path = None
    if entity == ListingType.models:
        model_name_for_image = (data_dict or {}).get("name", "model")

        def _save_image(upload_file):
            filename = getattr(upload_file, "filename", None)
            if upload_file and filename:
                return save_device_image(upload_file, model_name_for_image)
            return None

        try:
            front_image_path = _save_image(front_image_file)
            rear_image_path = _save_image(rear_image_file)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save model image: {str(e)}",
            )
    
    # Get the handler
    handler = _get_create_handlers().get(entity)
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {entity}",
        )
    
    # Add image_path to data for models
    create_data = validated_data.model_dump()
    if entity == ListingType.models:
        if front_image_path:
            create_data["front_image_path"] = front_image_path
        if rear_image_path:
            create_data["rear_image_path"] = rear_image_path
    
    audit_entry = None
    # Execute create with error handling
    try:
        result = handler(db, create_data)
        
        # Log the create action to audit log
        object_id = result.get("id") or result.get(f"{entity.value}_id")
        audit_context = build_audit_context(
            router="dcim.add",
            action="create",
            entity=entity.value,
            request=request,
        )
        audit_entry = log_create(
            db=db,
            user=current_user,
            entity_type=entity.value,
            object_id=object_id,
            entity_data=result,
            context=audit_context,
        )
        db.commit()
        invalidate_listing_cache_for_entity(entity)
        invalidate_location_summary_cache()
    except IntegrityError as e:
        db.rollback()
        # Clean up image if model creation failed
        if entity == ListingType.models:
            if front_image_path:
                delete_device_image(front_image_path)
            if rear_image_path:
                delete_device_image(rear_image_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database integrity error: {str(e.orig)}",
        )
    except HTTPException:
        db.rollback()
        # Clean up image if model creation failed
        if entity == ListingType.models:
            if front_image_path:
                delete_device_image(front_image_path)
            if rear_image_path:
                delete_device_image(rear_image_path)
        raise
    except Exception as e:
        db.rollback()
        # Clean up image if model creation failed
        if entity == ListingType.models:
            if front_image_path:
                delete_device_image(front_image_path)
            if rear_image_path:
                delete_device_image(rear_image_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entity: {str(e)}",
        )
    
    return {
        "entity": entity,
        "message": f"{entity.value} created successfully",
        "data": result,
        "change_log_id": audit_entry.id if audit_entry else None,
    }

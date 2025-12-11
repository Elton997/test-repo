"""
DCIM Update Router - Generic API for updating existing DCIM entities.
Supports updating entities of any type via a single parameterized endpoint.
"""
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.helpers.rbac_helper import AccessLevel, require_editor_or_admin
from app.helpers.listing_types import ListingType
from app.helpers.auth_helper import get_current_user
from app.helpers.audit_helper import build_audit_context, log_update
from app.helpers.listing_cache import invalidate_listing_cache_for_entity
from app.helpers.summary_cache import invalidate_location_summary_cache
from app.models.auth_models import User
from app.helpers.image_helper import update_device_image, delete_device_image

router = APIRouter(prefix="/api/dcim", tags=["DCIM Update"])


def _get_update_handlers():
    """Lazy import to keep startup fast."""
    from app.helpers.update_entity_helper import ENTITY_UPDATE_HANDLERS

    return ENTITY_UPDATE_HANDLERS


def _get_update_schemas():
    from app.schemas.entity_schemas import ENTITY_UPDATE_SCHEMAS

    return ENTITY_UPDATE_SCHEMAS


@router.put(
    "/update/{entity_name}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Generic DCIM update API - Update existing entity by type and name",
)
async def update_entity(
    request: Request,
    entity_name: str = Path(
        ...,
        min_length=1,
        description="The name of the entity to update",
    ),
    entity: ListingType = Query(
        ...,
        description=(
            "Entity type to update: racks | devices | device_types | "
            "locations | buildings | asset_owner | makes | models"
        ),
    ),
    access_level: AccessLevel = Depends(require_editor_or_admin),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Single endpoint to update any DCIM entity by name.
    
    **Required access level:** Editor or Admin
    
    **For models with images:**
    - Use `multipart/form-data` content type
    - Send `data` as a JSON string in a form field
    - Optional file fields: `front_image`, `rear_image`
    - Optional deletion flags: `delete_front_image=true`, `delete_rear_image=true`
    
    **For other entities or models without images:**
    - Use `application/json` content type
    - Send JSON object directly in request body (will be parsed automatically)
    
    **Entity types and updatable fields:**
    
    - **locations**: `name`
    - **buildings**: `name`, `status`, `location_name`
    - **racks**: `name`, `building_name`, `location_name`, `status`, `height`
    - **devices**: All device fields (device_name, serial_no, position, face or face_front/face_rear, status, etc.)
    - **device_types**: `device_name`, `make_name`, `model_name`
    - **asset_owner**: `owner_name`, `location_name`
    - **makes**: `make_name`
    - **models**: `name`, `make_name`
    
    All fields are optional - only provided fields will be updated.
    Name lookup is case-insensitive.
    Returns the updated entity data.
    """
    # Check content type and parse accordingly
    content_type = request.headers.get("content-type", "").lower()
    data_dict = None
    front_image = None
    rear_image = None
    delete_front_image = False
    delete_rear_image = False
    
    if "multipart/form-data" in content_type:
        # Handle multipart/form-data (for devices with images)
        form = await request.form()
        data_str = form.get("data")
        front_image = form.get("front_image")
        rear_image = form.get("rear_image")
        delete_front_image = form.get("delete_front_image") or form.get("delete_image")
        delete_rear_image = form.get("delete_rear_image")
        
        if data_str:
            try:
                data_dict = json.loads(data_str)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid JSON in data field: {str(e)}",
                )
        else:
            data_dict = {}
        
        def _is_truthy(value: Optional[str]) -> bool:
            return isinstance(value, str) and value.lower() in {"true", "1", "yes", "on"}

        delete_front_image = _is_truthy(delete_front_image)
        delete_rear_image = _is_truthy(delete_rear_image)
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
    if (front_image or rear_image) and entity != ListingType.models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image upload is only supported for models, not {entity.value}",
        )
    
    if (delete_front_image or delete_rear_image) and entity != ListingType.models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image deletion is only supported for models, not {entity.value}",
        )
    
    # Get the schema for validation
    schema_class = _get_update_schemas().get(entity)
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
    
    # Get the handler
    handler = _get_update_handlers().get(entity)
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {entity}",
        )
    
    # Filter out None values (only update provided fields)
    update_data = {k: v for k, v in validated_data.model_dump().items() if v is not None}
    
    # Handle images for models
    if entity == ListingType.models:
        from app.models.entity_models import Model
        from app.helpers.db_utils import get_entity_by_name

        model = get_entity_by_name(db, Model, entity_name)

        def _validate_image_ops(upload, delete_flag, label: str) -> None:
            if upload and delete_flag:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot upload and delete {label} image simultaneously.",
                )

        _validate_image_ops(front_image, delete_front_image, "front")
        _validate_image_ops(rear_image, delete_rear_image, "rear")

        if delete_front_image and model.front_image_path:
            delete_device_image(model.front_image_path)
            update_data["front_image_path"] = None
        elif front_image:
            try:
                new_front_path = update_device_image(front_image, entity_name, model.front_image_path)
                update_data["front_image_path"] = new_front_path
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update front image: {str(e)}",
                )

        if delete_rear_image and model.rear_image_path:
            delete_device_image(model.rear_image_path)
            update_data["rear_image_path"] = None
        elif rear_image:
            try:
                new_rear_path = update_device_image(rear_image, entity_name, model.rear_image_path)
                update_data["rear_image_path"] = new_rear_path
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update rear image: {str(e)}",
                )
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for update",
        )
    
    audit_entry = None
    # Execute update with error handling
    try:
        result = handler(db, entity_name, update_data)
        
        # Log the update action to audit log
        object_id = result.get("id")
        audit_context = build_audit_context(
            router="dcim.update",
            action="update",
            entity=entity.value,
            request=request,
            extra={"entity_name": entity_name},
        )
        audit_entry = log_update(
            db=db,
            user=current_user,
            entity_type=entity.value,
            object_id=object_id,
            changes=update_data,
            context=audit_context,
        )
        db.commit()
        invalidate_listing_cache_for_entity(entity)
        invalidate_location_summary_cache()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database integrity error: {str(e.orig)}",
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update entity: {str(e)}",
        )
    
    return {
        "entity": entity,
        "entity_name": entity_name,
        "message": f"{entity.value} updated successfully",
        "data": result,
        "change_log_id": audit_entry.id if audit_entry else None,
    }


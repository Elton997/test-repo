"""
DCIM Delete Router - Generic API for deleting DCIM entities.
Supports deleting entities of any type via a single parameterized endpoint.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.helpers.rbac_helper import AccessLevel, require_admin
from app.helpers.listing_types import ListingType
from app.helpers.auth_helper import get_current_user
from app.helpers.audit_helper import build_audit_context, log_delete
from app.helpers.listing_cache import invalidate_listing_cache_for_entity
from app.helpers.summary_cache import invalidate_location_summary_cache
from app.models.auth_models import User

router = APIRouter(prefix="/api/dcim", tags=["DCIM Delete"])


def _get_delete_handlers():
    """Lazy import to defer heavy helper module loading."""
    from app.helpers.delete_entity_helper import ENTITY_DELETE_HANDLERS

    return ENTITY_DELETE_HANDLERS


@router.delete(
    "/delete/{entity_name}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Generic DCIM delete API - Delete entity by type and name",
)
def delete_entity(
    request: Request,
    entity_name: str = Path(
        ...,
        description="The name of the entity to delete",
        min_length=1,
    ),
    entity: ListingType = Query(
        ...,
        description=(
            "Entity type to delete: racks | devices | device_types | "
            "locations | buildings | asset_owner | makes | models"
        ),
    ),
    access_level: AccessLevel = Depends(require_admin),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Single endpoint to delete any DCIM entity by name.
    
    **Required access level:** Editor or Admin
    
    **Entity types:**
    
    - **locations**: Delete by name (cascades to buildings, racks, devices, asset_owners)
    - **buildings**: Delete by name (cascades to racks, devices)
    - **racks**: Delete by name
    - **devices**: Delete by name
    - **device_types**: Delete by name
    - **asset_owner**: Delete by name
    - **makes**: Delete by name (cascades to models, device_types)
    - **models**: Delete by name (cascades to device_types)
    
    **Note:** Cascade deletes will remove all related child entities.
    Name lookup is case-insensitive.
    
    Returns the deleted entity data.
    """
    # Get the handler
    handler = _get_delete_handlers().get(entity)
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {entity}",
        )
    
    audit_entry = None
    # Execute delete with error handling
    try:
        result = handler(db, entity_name)
        
        # Log the delete action to audit log
        object_id = result.get("id")
        audit_context = build_audit_context(
            router="dcim.delete",
            action="delete",
            entity=entity.value,
            request=request,
            extra={"entity_name": entity_name},
        )
        audit_entry = log_delete(
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database integrity error: Cannot delete entity due to existing references. {str(e.orig)}",
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete entity: {str(e)}",
        )
    
    return {
        "entity": entity,
        "message": f"{entity.value} deleted successfully",
        "data": result,
        "change_log_id": audit_entry.id if audit_entry else None,
    }


"""
DCIM Change Log Router - API for viewing audit logs of entity changes.
Provides endpoints to query and filter audit log entries.
Uses names instead of IDs for entity lookups.
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
from threading import RLock

from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, exc

from app.db.session import get_db
from app.helpers.rbac_helper import AccessLevel, require_at_least_viewer
from app.helpers.listing_types import ListingType
from app.core.config import settings
from app.models.auth_models import AuditLog, User
from app.models.entity_models import (
    Location, Building, Wing, Floor, Datacenter,
    Rack, Device, DeviceType, Make, Model,
    AssetOwner, ApplicationMapped,
)


# Mapping of entity types to their model classes
ENTITY_MODEL_MAP = {
    ListingType.locations: Location,
    ListingType.buildings: Building,
    ListingType.wings: Wing,
    ListingType.floors: Floor,
    ListingType.datacenters: Datacenter,
    ListingType.racks: Rack,
    ListingType.devices: Device,
    ListingType.device_types: DeviceType,
    ListingType.makes: Make,
    ListingType.models: Model,
    ListingType.asset_owner: AssetOwner,
    ListingType.applications: ApplicationMapped,
}


_ENTITY_NAME_ID_CACHE: Dict[Tuple[str, str], Tuple[int, float]] = {}
_CACHE_LOCK = RLock()


def get_entity_id_by_name(db: Session, entity_type: ListingType, entity_name: str) -> int:
    """Get entity ID by name (case-insensitive) with proper exception handling."""
    normalized_name = entity_name.strip()
    cache_key = (entity_type.value, normalized_name.lower())
    now = time.time()
    ttl = settings.CHANGELOG_ENTITY_CACHE_TTL_SECONDS

    if ttl > 0:
        with _CACHE_LOCK:
            cached = _ENTITY_NAME_ID_CACHE.get(cache_key)
            if cached and cached[1] > now:
                return cached[0]

    try:
        model = ENTITY_MODEL_MAP.get(entity_type)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported entity type: {entity_type}",
            )
        
        entity = db.query(model).filter(func.upper(model.name) == func.upper(normalized_name)).first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_type.value} with name '{normalized_name}' not found",
            )
        entity_id = entity.id
        if ttl > 0:
            with _CACHE_LOCK:
                _ENTITY_NAME_ID_CACHE[cache_key] = (entity_id, now + ttl)
        return entity_id
    except HTTPException:
        raise
    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while fetching entity: {str(e)}",
        )

router = APIRouter(prefix="/api/dcim", tags=["DCIM Change Log"])


@router.get(
    "/change-logs",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get audit logs with optional filters",
)
def get_change_logs(
    entity: Optional[ListingType] = Query(
        None,
        description="Filter by entity type: racks | devices | device_types | locations | buildings | asset_owner | makes | models",
    ),
    action: Optional[str] = Query(
        None,
        description="Filter by action type: create | update | delete",
    ),
    object_name: Optional[str] = Query(
        None,
        description="Filter by specific object name (requires entity type to be specified)",
    ),
    username: Optional[str] = Query(
        None,
        description="Filter by username who performed the action",
    ),
    from_date: Optional[datetime] = Query(
        None,
        description="Filter logs from this date (ISO format: YYYY-MM-DDTHH:MM:SS)",
    ),
    to_date: Optional[datetime] = Query(
        None,
        description="Filter logs up to this date (ISO format: YYYY-MM-DDTHH:MM:SS)",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of records per page"),
    access_level: AccessLevel = Depends(require_at_least_viewer),
    db: Session = Depends(get_db),
):
    """
    Retrieve audit logs with optional filtering.
    
    **Required access level:** Viewer or higher
    
    **Filters:**
    - `entity`: Filter by entity type (rack, device, etc.)
    - `action`: Filter by action (create, update, delete)
    - `object_name`: Filter by specific entity name (requires entity type)
    - `username`: Filter by username who performed the action
    - `from_date`: Start date filter
    - `to_date`: End date filter
    
    **Pagination:**
    - `page`: Page number (default: 1)
    - `page_size`: Records per page (default: 50, max: 100)
    
    Returns paginated audit logs with user information.
    """
    try:
        base_query = db.query(AuditLog)
        
        if entity:
            base_query = base_query.filter(AuditLog.type == entity.value)
        
        if action:
            base_query = base_query.filter(AuditLog.action == action.lower())
        
        if object_name:
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Entity type is required when filtering by object_name",
                )
            object_id = get_entity_id_by_name(db, entity, object_name)
            base_query = base_query.filter(AuditLog.object_id == object_id)
        
        if username:
            user = db.query(User).filter(func.upper(User.name) == func.upper(username)).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with username '{username}' not found",
                )
            base_query = base_query.filter(AuditLog.user_id == user.id)
        
        if from_date:
            base_query = base_query.filter(AuditLog.time >= from_date)
        
        if to_date:
            base_query = base_query.filter(AuditLog.time <= to_date)
        
        total_count = base_query.order_by(None).count()
        
        offset = (page - 1) * page_size
        logs = (
            base_query.options(joinedload(AuditLog.user))
            .order_by(desc(AuditLog.time))
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        # Build response with user information (already loaded)
        result = []
        for log in logs:
            user_info = None
            if log.user:
                user_info = {
                    "user_id": log.user.id,
                    "username": log.user.name,
                    "full_name": log.user.full_name,
                }
            
            result.append({
                "id": log.id,
                "time": log.time.isoformat() if log.time else None,
                "action": log.action,
                "entity_type": log.type,
                "object_id": log.object_id,
                "message": log.message,
                "user": user_info,
            })
    except HTTPException:
        raise
    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while fetching change logs: {str(e)}",
        )
    
    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size,
        "data": result,
    }


@router.get(
    "/change-logs/{log_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get a specific audit log entry by ID",
)
def get_change_log_by_id(
    log_id: int,
    access_level: AccessLevel = Depends(require_at_least_viewer),
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific audit log entry by its ID.
    
    **Required access level:** Viewer or higher
    
    Returns the full audit log entry with user information.
    """
    try:
        # Optimize: Eager load user relationship
        log = (
            db.query(AuditLog)
            .options(joinedload(AuditLog.user))
            .filter(AuditLog.id == log_id)
            .first()
        )
        
        if not log:
            return {
                "error": "Audit log entry not found",
                "data": None,
            }
        
        user_info = None
        if log.user:
            user_info = {
                "user_id": log.user.id,
                "username": log.user.name,
                "full_name": log.user.full_name,
            }
    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while fetching change log: {str(e)}",
        )
    
    return {
        "data": {
            "id": log.id,
            "time": log.time.isoformat() if log.time else None,
            "action": log.action,
            "entity_type": log.type,
            "object_id": log.object_id,
            "message": log.message,
            "user": user_info,
        }
    }


@router.get(
    "/change-logs/entity/{entity_type}/{entity_name}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get change history for a specific entity by name",
)
def get_entity_change_history(
    entity_type: ListingType = Path(
        ...,
        description="Entity type: racks | devices | device_types | locations | buildings | asset_owner | makes | models | applications",
    ),
    entity_name: str = Path(
        ...,
        description="The name of the entity to get change history for",
        min_length=1,
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of records per page"),
    access_level: AccessLevel = Depends(require_at_least_viewer),
    db: Session = Depends(get_db),
):
    """
    Get the complete change history for a specific entity by name.
    
    **Required access level:** Viewer or higher
    
    Returns all audit log entries for the specified entity type and name,
    ordered by most recent first. Entity name lookup is case-insensitive.
    """
    try:
        # Resolve entity name to ID
        object_id = get_entity_id_by_name(db, entity_type, entity_name)
        
        # Optimize: Eager load user relationship
        query = (
            db.query(AuditLog)
            .options(joinedload(AuditLog.user))
            .filter(AuditLog.type == entity_type.value)
            .filter(AuditLog.object_id == object_id)
        )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        logs = (
            query
            .order_by(desc(AuditLog.time))
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        # Build response (user already loaded)
        result = []
        for log in logs:
            user_info = None
            if log.user:
                user_info = {
                    "user_id": log.user.id,
                    "username": log.user.name,
                    "full_name": log.user.full_name,
                }
            
            result.append({
                "id": log.id,
                "time": log.time.isoformat() if log.time else None,
                "action": log.action,
                "message": log.message,
                "user": user_info,
            })
    except HTTPException:
        raise
    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while fetching entity change history: {str(e)}",
        )
    
    return {
        "entity_type": entity_type.value,
        "entity_name": entity_name,
        "object_id": object_id,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size,
        "history": result,
    }


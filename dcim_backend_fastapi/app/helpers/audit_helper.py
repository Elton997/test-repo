# app/helpers/audit_helper.py
"""
Audit logging helper for tracking entity changes.
Provides functions to create audit log entries for create, update, delete operations.
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.auth_models import AuditLog, User

if TYPE_CHECKING:  # pragma: no cover - hint only
    from fastapi import Request


def create_audit_log(
    db: Session,
    user: Optional[User],
    action: str,
    entity_type: str,
    object_id: Optional[int] = None,
    message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Create an audit log entry.
    
    Args:
        db: Database session
        user: Current user (can be None for system actions)
        action: Action type - "create", "update", "delete"
        entity_type: Type of entity - "rack", "device", "location", etc.
        object_id: ID of the affected object
        message: Optional message string
        data: Optional data dict to be stored as JSON in message
    
    Returns:
        Created AuditLog instance
    """
    payload: Dict[str, Any] = {}
    if context:
        payload["context"] = context

    if data:
        payload.update(data)

    if payload and not message:
        message = json.dumps(payload, default=str)
    
    audit_log = AuditLog(
        time=datetime.utcnow(),
        user_id=user.id if user else None,
        action=action,
        type=entity_type,
        object_id=object_id,
        message=message,
    )
    
    db.add(audit_log)
    # Don't commit here - let the caller handle transaction
    return audit_log


def log_create(
    db: Session,
    user: Optional[User],
    entity_type: str,
    object_id: int,
    entity_data: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Log a create action.
    
    Args:
        db: Database session
        user: Current user
        entity_type: Type of entity created
        object_id: ID of the created object
        entity_data: Data of the created entity
    """
    return create_audit_log(
        db=db,
        user=user,
        action="create",
        entity_type=entity_type,
        object_id=object_id,
        context=context,
        data={"created": entity_data},
    )


def log_update(
    db: Session,
    user: Optional[User],
    entity_type: str,
    object_id: int,
    changes: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Log an update action.
    
    Args:
        db: Database session
        user: Current user
        entity_type: Type of entity updated
        object_id: ID of the updated object
        changes: Dictionary of changed fields
    """
    return create_audit_log(
        db=db,
        user=user,
        action="update",
        entity_type=entity_type,
        object_id=object_id,
        context=context,
        data={"updated_fields": changes},
    )


def log_delete(
    db: Session,
    user: Optional[User],
    entity_type: str,
    object_id: int,
    entity_data: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Log a delete action.
    
    Args:
        db: Database session
        user: Current user
        entity_type: Type of entity deleted
        object_id: ID of the deleted object
        entity_data: Optional snapshot of deleted entity data
    """
    return create_audit_log(
        db=db,
        user=user,
        action="delete",
        entity_type=entity_type,
        object_id=object_id,
        context=context,
        data={"deleted": entity_data} if entity_data else None,
    )


def build_audit_context(
    *,
    router: str,
    action: str,
    entity: Optional[str] = None,
    request: Optional["Request"] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Helper to compose consistent context payload for audit logs.
    """
    context: Dict[str, Any] = {
        "router": router,
        "action": action,
    }

    if entity:
        context["entity"] = entity

    if request is not None:
        context["path"] = request.url.path
        context["method"] = request.method

    if extra:
        context.update(extra)

    return context


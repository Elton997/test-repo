# app/helpers/db_utils.py
"""
Database utility functions for optimized queries and exception handling.
Reduces code duplication and improves performance.
"""
from typing import TypeVar, Type, Optional, Dict, Any, List, Tuple
from contextlib import contextmanager

from fastapi import HTTPException, status
from sqlalchemy import func, exc
from sqlalchemy.orm import Session, Query

from app.models.entity_models import (
    Location, Building, Wing, Floor, Datacenter,
    Rack, Device, DeviceType, Make, Model,
    AssetOwner, ApplicationMapped,
)

# Type variable for model classes
ModelType = TypeVar('ModelType')


def get_entity_by_name(
    db: Session,
    model_class: Type[ModelType],
    name: str,
    error_message: Optional[str] = None,
) -> ModelType:
    """
    Get entity by name (case-insensitive) with proper exception handling.
    
    Args:
        db: Database session
        model_class: SQLAlchemy model class
        name: Entity name to search for
        error_message: Custom error message (optional)
    
    Returns:
        Entity instance
    
    Raises:
        HTTPException: If entity not found
    """
    try:
        entity = (
            db.query(model_class)
            .filter(func.upper(model_class.name) == func.upper(name))
            .first()
        )
        if not entity:
            msg = error_message or f"{model_class.__name__} with name '{name}' not found"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            )
        return entity
    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while fetching {model_class.__name__}: {str(e)}",
        )


def check_entity_exists(
    db: Session,
    model_class: Type[ModelType],
    name: str,
    exclude_id: Optional[int] = None,
) -> bool:
    """
    Check if entity with given name exists (case-insensitive).
    
    Args:
        db: Database session
        model_class: SQLAlchemy model class
        name: Entity name to check
        exclude_id: Optional ID to exclude from check (for updates)
    
    Returns:
        True if entity exists, False otherwise
    """
    try:
        query = db.query(model_class).filter(func.upper(model_class.name) == func.upper(name))
        if exclude_id:
            query = query.filter(model_class.id != exclude_id)
        return query.first() is not None
    except exc.SQLAlchemyError:
        return False


def batch_get_entities_by_name(
    db: Session,
    lookups: List[Tuple[Type[ModelType], str]],
) -> Dict[Tuple[Type[ModelType], str], ModelType]:
    """
    Batch fetch multiple entities by name in a single optimized query per model type.
    
    Args:
        db: Database session
        lookups: List of (model_class, name) tuples
    
    Returns:
        Dictionary mapping (model_class, name) to entity instance
    """
    result = {}
    
    # Group by model class to optimize queries
    by_model: Dict[Type[ModelType], List[str]] = {}
    for model_class, name in lookups:
        if model_class not in by_model:
            by_model[model_class] = []
        by_model[model_class].append(name)
    
    # Fetch each model type in batch
    for model_class, names in by_model.items():
        try:
            # Use IN clause for batch lookup
            entities = (
                db.query(model_class)
                .filter(
                    func.upper(model_class.name).in_([n.upper() for n in names])
                )
                .all()
            )
            
            # Create lookup map (case-insensitive)
            entity_map = {e.name.upper(): e for e in entities}
            
            # Map results
            for model_class_inner, name in lookups:
                if model_class_inner == model_class:
                    upper_name = name.upper()
                    if upper_name in entity_map:
                        result[(model_class_inner, name)] = entity_map[upper_name]
        except exc.SQLAlchemyError:
            # If batch fails, fall back to individual lookups
            for model_class_inner, name in lookups:
                if model_class_inner == model_class:
                    try:
                        entity = get_entity_by_name(db, model_class_inner, name)
                        result[(model_class_inner, name)] = entity
                    except HTTPException:
                        pass
    
    return result


@contextmanager
def db_operation(db: Session, operation_name: str = "database operation"):
    """
    Context manager for database operations with proper exception handling.
    
    Usage:
        with db_operation(db, "create device"):
            # database operations
            db.commit()
    """
    try:
        yield
    except HTTPException:
        db.rollback()
        raise
    except exc.IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database integrity error during {operation_name}: {str(e)}",
        )
    except exc.SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during {operation_name}: {str(e)}",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during {operation_name}: {str(e)}",
        )


def optimize_count_query(db: Session, query: Query) -> int:
    """
    Optimize count query by using subquery when possible.
    
    Args:
        db: Database session
        query: SQLAlchemy query object
    
    Returns:
        Count result
    """
    try:
        # Use subquery for better performance on complex queries
        return db.query(func.count()).select_from(query.subquery()).scalar() or 0
    except Exception:
        # Fallback to regular count
        return query.count()


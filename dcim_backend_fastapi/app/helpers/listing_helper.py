# app/helpers/listing_helper.py
"""
Helper functions for listing DCIM entities.
Contains all entity-specific listing logic with filters and aggregation.
Updated to match Alembic migrations.
Optimized for performance with combined queries and eager loading.
"""
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

from sqlalchemy import func, exc
from sqlalchemy.orm import Session, Query as SQLQuery, joinedload, selectinload

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
from app.helpers.db_utils import db_operation
from app.helpers.listing_types import ListingType


# =============================================================================
# Helper Functions
# =============================================================================


def _restrict_to_locations(query, column, allowed_location_ids: Optional[Set[int]]):
    if allowed_location_ids is None:
        return query
    return query.filter(column.in_(allowed_location_ids))

def apply_filters(
    query: SQLQuery,
    filters: Dict[str, Any],
    filter_config: Dict[str, Tuple[Any, str]],
) -> SQLQuery:
    """
    Apply filters to a query dynamically based on filter configuration.
    
    Args:
        query: SQLAlchemy query object
        filters: Dictionary of filter name -> filter value
        filter_config: Dictionary mapping filter names to (model_attribute, filter_type)
            filter_type can be:
            - 'exact': Exact match (case-insensitive for strings)
            - 'contains': Contains match (case-insensitive for strings)
            - 'exact_int': Exact match for integers
            - 'exact_date': Exact match for dates
    
    Returns:
        Query with filters applied
    """
    for filter_name, filter_value in filters.items():
        # Skip None values, empty strings, and whitespace-only strings
        # (FastAPI converts empty query params to "")
        if filter_value is None:
            continue
        if isinstance(filter_value, str) and (filter_value == "" or not filter_value.strip()):
            continue
        
        if filter_name not in filter_config:
            continue
        
        model_attr, filter_type = filter_config[filter_name]
        
        if filter_type == 'exact':
            # Case-insensitive exact match for strings
            # Handle NULL values properly - if model_attr is NULL, the comparison will be NULL (falsy)
            query = query.filter(func.upper(model_attr) == func.upper(filter_value))
        elif filter_type == 'contains':
            # Case-insensitive contains match for strings
            query = query.filter(func.upper(model_attr).contains(func.upper(filter_value)))
        elif filter_type == 'exact_int':
            # Exact match for integers
            query = query.filter(model_attr == filter_value)
        elif filter_type == 'exact_date':
            # Exact match for dates
            query = query.filter(model_attr == filter_value)
    
    return query


def get_paginated_results(
    query: SQLQuery,
    offset: int,
    page_size: int,
    order_by_column: Any,
) -> Tuple[int, List[Any]]:
    """
    Get paginated results with total count in a single database query using window function.
    This avoids making two separate queries (one for count, one for data).
    
    Args:
        query: SQLAlchemy query object with filters already applied
        offset: Offset for pagination
        page_size: Number of results per page
        order_by_column: Column to order by (e.g., Device.id)
    
    Returns:
        Tuple of (total_count, list of results)
    """
    # Apply ordering - this will replace any existing ordering
    # Filters are already applied to the query before this function is called
    query = query.order_by(order_by_column.asc())
    
    # Use window function to get total count in the same query
    # This adds COUNT(*) OVER() which gives us the total without a separate query
    # The window function respects WHERE clauses, so filters are applied correctly
    total_count_expr = func.count().over()
    
    # Add the count as an additional column to the query
    # This works with both single and multi-column queries
    query_with_count = query.add_columns(total_count_expr.label('_total_count'))
    
    # Apply pagination
    query_with_count = query_with_count.offset(offset).limit(page_size)
    
    # Execute single query - this gets both data and total count
    results = query_with_count.all()
    
    # Extract total count and process results
    if results:
        # Extract total count from first result (all results have the same total)
        # The count is always the last element in the result tuple/row
        first_result = results[0]
        # Get the number of columns (excluding the count column we added)
        num_columns = len(first_result) - 1  # Subtract 1 for the count column we added
        
        # Extract total count (last element)
        total = first_result[-1] if len(first_result) > 0 else 0
        
        # Remove the count column from results (it's always the last element)
        # Convert Row objects to tuples and slice to remove the count column
        data = []
        for row in results:
            # Convert to tuple if it's a Row object, otherwise use as-is
            if hasattr(row, '_asdict'):
                # SQLAlchemy Row object - convert to tuple
                row_tuple = tuple(row)
            else:
                row_tuple = tuple(row) if isinstance(row, (tuple, list)) else (row,)
            
            # Remove the last element (the count) and keep the rest
            if num_columns == 1:
                # Single column result
                data.append(row_tuple[0])
            else:
                # Multi-column result - return tuple without the count
                data.append(row_tuple[:num_columns])
    else:
        # No results - need to get count separately for accuracy
        # This is a fallback when window function returns no rows
        total = query.count()
        data = []
    
    return total, data


# =============================================================================
# Entity-specific listing functions
# =============================================================================

def list_locations(
    db: Session,
    offset: int,
    page_size: int,
    location_name: Optional[str] = None,
    location_description: Optional[str] = None,
    building_name: Optional[str] = None,
    allowed_location_ids: Optional[Set[int]] = None,
    **kwargs,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    List locations with building counts.
    Returns: (total_count, list of location dicts)
    Optimized: Single query for counts, efficient pagination.
    """
    try:
        # Optimize: Get building counts in a single query for all locations
        # This is more efficient than querying all and filtering
        building_counts_subq = (
            db.query(
                Building.location_id,
                func.count(Building.id).label('count')
            )
            .group_by(Building.location_id)
            .subquery()
        )
        
        # Main query with left join for counts
        base_q = (
            db.query(
                Location,
                func.coalesce(building_counts_subq.c.count, 0).label('building_count')
            )
            .outerjoin(
                building_counts_subq,
                Location.id == building_counts_subq.c.location_id
            )
            .order_by(Location.id.asc())
        )
        base_q = _restrict_to_locations(base_q, Location.id, allowed_location_ids)
        
        # Apply filters dynamically
        filter_config = {
            'location_name': (Location.name, 'exact'),
            'location_description': (Location.description, 'contains'),
        }
        filters = {
            'location_name': location_name,
            'location_description': location_description,
        }
        base_q = apply_filters(base_q, filters, filter_config)
        
        if building_name and building_name.strip():
            base_q = (
                base_q.join(Building, Location.id == Building.location_id)
                .filter(func.upper(Building.name) == func.upper(building_name))
                .distinct()
            )
        
        # Use optimized pagination that gets count and data in single query
        total, rows = get_paginated_results(base_q, offset, page_size, Location.id)

        data = [
            {
                "id": loc.id,
                "name": loc.name,
                "description": loc.description,
                "buildings": int(building_count),
            }
            for loc, building_count in rows
        ]

        return total, data
    except exc.SQLAlchemyError as e:
        raise Exception(f"Database error in list_locations: {str(e)}")


def list_buildings(
    db: Session,
    offset: int,
    page_size: int,
    location_name: Optional[str] = None,
    building_name: Optional[str] = None,
    building_status: Optional[str] = None,
    building_description: Optional[str] = None,
    rack_name: Optional[str] = None,
    device_name: Optional[str] = None,
    allowed_location_ids: Optional[Set[int]] = None,
    **kwargs,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    List buildings with rack/device counts.
    Optimized: Combined count queries, eager loading, single query for stats.
    """
    try:
        # Optimize: Get all counts in a single query using subqueries
        rack_counts_subq = (
            db.query(
                Rack.building_id,
                func.count(Rack.id).label('rack_count')
            )
            .group_by(Rack.building_id)
            .subquery()
        )
        device_counts_subq = (
            db.query(
                Device.building_id,
                func.count(Device.id).label('device_count')
            )
            .group_by(Device.building_id)
            .subquery()
        )
        
        base_q = (
            db.query(
                Building,
                Location,
                func.coalesce(rack_counts_subq.c.rack_count, 0).label('rack_count'),
                func.coalesce(device_counts_subq.c.device_count, 0).label('device_count')
            )
            .join(Location, Building.location_id == Location.id)
            .outerjoin(rack_counts_subq, Building.id == rack_counts_subq.c.building_id)
            .outerjoin(device_counts_subq, Building.id == device_counts_subq.c.building_id)
            .order_by(Building.id.asc())
        )
        base_q = _restrict_to_locations(base_q, Building.location_id, allowed_location_ids)
        
        # Apply filters dynamically
        filter_config = {
            'location_name': (Location.name, 'exact'),
            'building_name': (Building.name, 'exact'),
            'building_status': (Building.status, 'exact'),
            'building_description': (Building.description, 'contains'),
        }
        filters = {
            'location_name': location_name,
            'building_name': building_name,
            'building_status': building_status,
            'building_description': building_description,
        }
        base_q = apply_filters(base_q, filters, filter_config)
        
        if rack_name and rack_name.strip():
            base_q = (
                base_q.join(Rack, Building.id == Rack.building_id)
                .filter(func.upper(Rack.name) == func.upper(rack_name))
                .distinct()
            )
        if device_name and device_name.strip():
            base_q = (
                base_q.join(Device, Building.id == Device.building_id)
                .filter(func.upper(Device.name) == func.upper(device_name))
                .distinct()
            )
        
        # Use optimized pagination that gets count and data in single query
        total, rows = get_paginated_results(base_q, offset, page_size, Building.id)

        data = [
            {
                "id": building.id,
                "name": building.name,
                "status": building.status,
                "description": building.description,
                "location_name": location.name if location else None,
                "devices": int(device_count),
                "racks": int(rack_count),
            }
            for building, location, rack_count, device_count in rows
        ]

        return total, data
    except exc.SQLAlchemyError as e:
        raise Exception(f"Database error in list_buildings: {str(e)}")


def list_racks(
    db: Session,
    offset: int,
    page_size: int,
    location_name: Optional[str] = None,
    building_name: Optional[str] = None,
    wing_name: Optional[str] = None,
    floor_name: Optional[str] = None,
    rack_name: Optional[str] = None,
    rack_status: Optional[str] = None,
    rack_height: Optional[int] = None,
    rack_description: Optional[str] = None,
    datacenter_name: Optional[str] = None,
    device_name: Optional[str] = None,
    allowed_location_ids: Optional[Set[int]] = None,
    **kwargs,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    List racks with device counts and remaining space.
    Optimized: Combined query with device counts, eager loading.
    """
    try:
        # Optimize: Get device counts in a single subquery
        device_counts_subq = (
            db.query(
                Device.rack_id,
                func.count(Device.id).label("device_count")
            )
            .group_by(Device.rack_id)
            .subquery()
        )
        
        base_q = (
            db.query(
                Rack,
                Location,
                Building,
                Wing,
                Floor,
                Datacenter,
                func.coalesce(device_counts_subq.c.device_count, 0).label("device_count")
            )
            .join(Location, Rack.location_id == Location.id)
            .join(Building, Rack.building_id == Building.id)
            .outerjoin(Wing, Rack.wing_id == Wing.id)
            .outerjoin(Floor, Rack.floor_id == Floor.id)
            .outerjoin(Datacenter, Rack.datacenter_id == Datacenter.id)
            .outerjoin(device_counts_subq, Rack.id == device_counts_subq.c.rack_id)
            .order_by(Rack.id.asc())
        )
        base_q = _restrict_to_locations(base_q, Rack.location_id, allowed_location_ids)
        
        # Apply filters dynamically
        filter_config = {
            'location_name': (Location.name, 'exact'),
            'building_name': (Building.name, 'exact'),
            'wing_name': (Wing.name, 'exact'),
            'floor_name': (Floor.name, 'exact'),
            'rack_name': (Rack.name, 'exact'),
            'rack_status': (Rack.status, 'exact'),
            'rack_height': (Rack.height, 'exact_int'),
            'rack_description': (Rack.description, 'contains'),
            'datacenter_name': (Datacenter.name, 'exact'),
        }
        filters = {
            'location_name': location_name,
            'building_name': building_name,
            'wing_name': wing_name,
            'floor_name': floor_name,
            'rack_name': rack_name,
            'rack_status': rack_status,
            'rack_height': rack_height,
            'rack_description': rack_description,
            'datacenter_name': datacenter_name,
        }
        base_q = apply_filters(base_q, filters, filter_config)
        
        if device_name and device_name.strip():
            base_q = (
                base_q.join(Device, Rack.id == Device.rack_id)
                .filter(func.upper(Device.name) == func.upper(device_name))
                .distinct()
            )
        
        # Use optimized pagination that gets count and data in single query
        total, rows = get_paginated_results(base_q, offset, page_size, Rack.id)

        data = []
        for rack, location, building, wing, floor, datacenter, devices_count in rows:
            rack_height = rack.height or 0
            used_space = rack.space_used or 0
            available_space = rack.space_available
            if available_space is None:
                available_space = max(rack_height - used_space, 0)
            remaining_space = max(available_space, 0)
            
            # Calculate available space percentage
            available_space_percent = None
            if rack_height > 0:
                available_space_percent = round((remaining_space / rack_height) * 100, 2)

            data.append({
                "id": rack.id,
                "name": rack.name,
                "location_name": location.name if location else None,
                "building_name": building.name if building else None,
                "wing_name": wing.name if wing else None,
                "floor_name": floor.name if floor else None,
                "datacenter_name": datacenter.name if datacenter else None,
                "status": rack.status,
                "height": rack.height,
                "description": rack.description,
                "devices": int(devices_count),
                "used_space": used_space,
                "available_space": remaining_space,
                "available_space_percent": available_space_percent,
            })

        return total, data
    except exc.SQLAlchemyError as e:
        raise Exception(f"Database error in list_racks: {str(e)}")


def list_devices(
    db: Session,
    offset: int,
    page_size: int,
    location_name: Optional[str] = None,
    building_name: Optional[str] = None,
    wing_name: Optional[str] = None,
    floor_name: Optional[str] = None,
    rack_name: Optional[str] = None,
    device_name: Optional[str] = None,
    device_status: Optional[str] = None,
    device_position: Optional[int] = None,
    device_face: Optional[str] = None,
    device_description: Optional[str] = None,
    serial_number: Optional[str] = None,
    ip_address: Optional[str] = None,
    po_number: Optional[str] = None,
    asset_user: Optional[str] = None,
    asset_owner: Optional[str] = None,
    applications_mapped_name: Optional[str] = None,
    warranty_start_date: Optional[date] = None,
    warranty_end_date: Optional[date] = None,
    amc_start_date: Optional[date] = None,
    amc_end_date: Optional[date] = None,
    device_type: Optional[str] = None,
    make_name: Optional[str] = None,
    model_name: Optional[str] = None,
    datacenter_name: Optional[str] = None,
    allowed_location_ids: Optional[Set[int]] = None,
    **kwargs,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    List devices with all related information.
    Optimized: Explicit joins instead of lazy loading, efficient filtering.
    """
    try:
        # Determine which joins should be inner joins based on filters
        # If filtering by a column from an outerjoined table, use inner join to ensure filter works correctly
        use_inner_join_device_type = (device_type is not None and device_type.strip() != "") or (model_name is not None and model_name.strip() != "")
        use_inner_join_make = make_name is not None and make_name.strip() != ""
        use_inner_join_model = model_name is not None and model_name.strip() != ""
        use_inner_join_location = location_name is not None and location_name.strip() != ""
        use_inner_join_building = building_name is not None and building_name.strip() != ""
        use_inner_join_rack = rack_name is not None and rack_name.strip() != ""
        use_inner_join_datacenter = datacenter_name is not None and datacenter_name.strip() != ""
        use_inner_join_application = applications_mapped_name is not None and applications_mapped_name.strip() != ""
        use_inner_join_asset_owner = asset_owner is not None and asset_owner.strip() != ""
        
        # Use explicit joins for better performance and control
        base_q = (
            db.query(
                Device,
                Location,
                Building,
                Wing,
                Floor,
                Datacenter,
                Rack,
                Make,
                DeviceType,
                Model,
                ApplicationMapped,
                AssetOwner
            )
        )
        
        # Apply joins - use inner join if filtering by that table's columns, otherwise outer join
        if use_inner_join_location:
            base_q = base_q.join(Location, Device.location_id == Location.id)
        else:
            base_q = base_q.outerjoin(Location, Device.location_id == Location.id)
            
        if use_inner_join_building:
            base_q = base_q.join(Building, Device.building_id == Building.id)
        else:
            base_q = base_q.outerjoin(Building, Device.building_id == Building.id)
            
        base_q = base_q.outerjoin(Wing, Device.wings_id == Wing.id)
        base_q = base_q.outerjoin(Floor, Device.floor_id == Floor.id)
        
        if use_inner_join_datacenter:
            base_q = base_q.join(Datacenter, Device.dc_id == Datacenter.id)
        else:
            base_q = base_q.outerjoin(Datacenter, Device.dc_id == Datacenter.id)
            
        if use_inner_join_rack:
            base_q = base_q.join(Rack, Device.rack_id == Rack.id)
        else:
            base_q = base_q.outerjoin(Rack, Device.rack_id == Rack.id)
            
        if use_inner_join_make:
            base_q = base_q.join(Make, Device.make_id == Make.id)
        else:
            base_q = base_q.outerjoin(Make, Device.make_id == Make.id)
            
        if use_inner_join_device_type:
            base_q = base_q.join(DeviceType, Device.devicetype_id == DeviceType.id)
        else:
            base_q = base_q.outerjoin(DeviceType, Device.devicetype_id == DeviceType.id)
            
        if use_inner_join_model:
            base_q = base_q.join(Model, DeviceType.id == Model.device_type_id)
        else:
            base_q = base_q.outerjoin(Model, DeviceType.id == Model.device_type_id)
            
        if use_inner_join_application:
            base_q = base_q.join(ApplicationMapped, Device.applications_mapped_id == ApplicationMapped.id)
        else:
            base_q = base_q.outerjoin(ApplicationMapped, Device.applications_mapped_id == ApplicationMapped.id)
            
        if use_inner_join_asset_owner:
            base_q = base_q.join(AssetOwner, ApplicationMapped.asset_owner_id == AssetOwner.id)
        else:
            base_q = base_q.outerjoin(AssetOwner, ApplicationMapped.asset_owner_id == AssetOwner.id)
        
        # Apply filters dynamically
        filter_config = {
            'location_name': (Location.name, 'exact'),
            'building_name': (Building.name, 'exact'),
            'wing_name': (Wing.name, 'exact'),
            'floor_name': (Floor.name, 'exact'),
            'rack_name': (Rack.name, 'exact'),
            'device_name': (Device.name, 'exact'),
            'device_status': (Device.status, 'exact'),
            'device_position': (Device.position, 'exact_int'),
            # 'device_face' filter removed; face is now derived from face_front/face_rear
            'device_description': (Device.description, 'contains'),
            'serial_number': (Device.serial_no, 'exact'),
            'ip_address': (Device.ip, 'exact'),
            'po_number': (Device.po_number, 'exact'),
            'asset_user': (Device.asset_user, 'exact'),
            'asset_owner': (AssetOwner.name, 'exact'),
            'applications_mapped_name': (ApplicationMapped.name, 'exact'),
            'warranty_start_date': (Device.warranty_start_date, 'exact_date'),
            'warranty_end_date': (Device.warranty_end_date, 'exact_date'),
            'amc_start_date': (Device.amc_start_date, 'exact_date'),
            'amc_end_date': (Device.amc_end_date, 'exact_date'),
            'device_type': (DeviceType.name, 'exact'),
            'make_name': (Make.name, 'exact'),
            'model_name': (Model.name, 'exact'),
            'datacenter_name': (Datacenter.name, 'exact'),
        }
        
        filters = {
            'location_name': location_name,
            'building_name': building_name,
            'wing_name': wing_name,
            'floor_name': floor_name,
            'rack_name': rack_name,
            'device_name': device_name,
            'device_status': device_status,
            'device_position': device_position,
            # 'device_face': device_face,  # removed; see note above
            'device_description': device_description,
            'serial_number': serial_number,
            'ip_address': ip_address,
            'po_number': po_number,
            'asset_user': asset_user,
            'asset_owner': asset_owner,
            'applications_mapped_name': applications_mapped_name,
            'warranty_start_date': warranty_start_date,
            'warranty_end_date': warranty_end_date,
            'amc_start_date': amc_start_date,
            'amc_end_date': amc_end_date,
            'device_type': device_type,
            'make_name': make_name,
            'model_name': model_name,
            'datacenter_name': datacenter_name,
        }
        
        base_q = apply_filters(base_q, filters, filter_config)

        base_q = _restrict_to_locations(base_q, Device.location_id, allowed_location_ids)
        
        # Use optimized pagination that gets count and data in single query
        total, rows = get_paginated_results(base_q, offset, page_size, Device.id)

        data = []
        for (device, location, building, wing, floor, datacenter, rack,
             make, device_type_obj, model, application, asset_owner) in rows:
            # Derive human-readable face from boolean flags
            if device.face_front and device.face_rear:
                face_value = "both"
            elif device.face_front:
                face_value = "front"
            elif device.face_rear:
                face_value = "rear"
            else:
                face_value = None
            data.append({
                "id": device.id,
                "name": device.name,
                "position": device.position,
                "face": face_value,
                "status": device.status,
                "description": device.description,
                "building_name": building.name if building else None,
                "location_name": location.name if location else None,
                "wing_name": wing.name if wing else None,
                "floor_name": floor.name if floor else None,
                "datacenter_name": datacenter.name if datacenter else None,
                "rack_name": rack.name if rack else None,
                "height": model.height if model else None,
                "make": make.name if make else None,
                "model_name": model.name if model else None,
                "device_type": device_type_obj.name if device_type_obj else None,
                "ip_address": device.ip,
                "po_number": device.po_number,
                "asset_owner": asset_owner.name if asset_owner else None,
                "asset_user": device.asset_user,
                "applications_mapped_name": application.name if application else None,
                "warranty_start_date": device.warranty_start_date,
                "warranty_end_date": device.warranty_end_date,
                "amc_start_date": device.amc_start_date,
                "amc_end_date": device.amc_end_date,
                "serial_number": device.serial_no,
            })

        return total, data
    except exc.SQLAlchemyError as e:
        raise Exception(f"Database error in list_devices: {str(e)}")


def list_device_types(
    db: Session,
    offset: int,
    page_size: int,
    device_type: Optional[str] = None,
    device_type_description: Optional[str] = None,
    make_name: Optional[str] = None,
    **kwargs,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    List device types with make info and instance counts.
    Optimized: Combined query with device counts, explicit joins.
    """
    try:
        # Optimize: Get device counts in subquery
        device_counts_subq = (
            db.query(
                Device.devicetype_id,
                func.count(Device.id).label('device_count')
            )
            .group_by(Device.devicetype_id)
            .subquery()
        )
        
        # Get model counts per device type
        model_counts_subq = (
            db.query(
                Model.device_type_id,
                func.count(Model.id).label('models_count')
            )
            .group_by(Model.device_type_id)
            .subquery()
        )
        
        # Get first model per device type (simplified approach)
        first_model_subq = (
            db.query(
                Model.device_type_id,
                func.min(Model.id).label('first_model_id')
            )
            .group_by(Model.device_type_id)
            .subquery()
        )
        
        base_q = (
            db.query(
                DeviceType,
                Make,
                func.coalesce(device_counts_subq.c.device_count, 0).label('device_count'),
                func.coalesce(model_counts_subq.c.models_count, 0).label('models_count'),
                Model.id.label('model_id'),
                Model.name.label('model_name'),
                Model.height.label('model_height')
            )
            .join(Make, DeviceType.make_id == Make.id)
            .outerjoin(device_counts_subq, DeviceType.id == device_counts_subq.c.devicetype_id)
            .outerjoin(model_counts_subq, DeviceType.id == model_counts_subq.c.device_type_id)
            .outerjoin(first_model_subq, DeviceType.id == first_model_subq.c.device_type_id)
            .outerjoin(Model, Model.id == first_model_subq.c.first_model_id)
            .order_by(DeviceType.id.asc())
        )
        
        # Apply filters dynamically
        filter_config = {
            'device_type': (DeviceType.name, 'exact'),
            'device_type_description': (DeviceType.description, 'contains'),
            'make_name': (Make.name, 'exact'),
        }
        filters = {
            'device_type': device_type,
            'device_type_description': device_type_description,
            'make_name': make_name,
        }
        base_q = apply_filters(base_q, filters, filter_config)
        
        # Use optimized pagination that gets count and data in single query
        total, rows = get_paginated_results(base_q, offset, page_size, DeviceType.id)

        data = []
        for (dt, make, device_count, models_count, model_id, model_name, model_height) in rows:
            data.append({
                "id": dt.id,
                "name": dt.name,
                "description": dt.description,
                "make": make.name if make else None,
                "u_height": int(model_height) if model_height else None,
                "devices": int(device_count),
                # "model_id": int(model_id) if model_id else None,
                "model_name": model_name if model_name else None,
                "model_height": int(model_height) if model_height else None,
                "models_count": int(models_count),
            })

        return total, data
    except exc.SQLAlchemyError as e:
        raise Exception(f"Database error in list_device_types: {str(e)}")


def list_makes(
    db: Session,
    offset: int,
    page_size: int,
    make_name: Optional[str] = None,
    make_description: Optional[str] = None,
    device_type: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    List makes with rack, device, and model counts.
    Optimized: Combined query with all stats in single query.
    """
    try:
        # Optimize: Get all stats in subqueries
        device_stats_subq = (
            db.query(
                Device.make_id,
                func.count(Device.id).label("device_count"),
                func.count(func.distinct(Device.rack_id)).label("rack_count")
            )
            .group_by(Device.make_id)
            .subquery()
        )
        
        model_counts_subq = (
            db.query(
                Model.make_id,
                func.count(Model.id).label("model_count")
            )
            .group_by(Model.make_id)
            .subquery()
        )
        
        base_q = (
            db.query(
                Make,
                func.coalesce(device_stats_subq.c.device_count, 0).label("device_count"),
                func.coalesce(device_stats_subq.c.rack_count, 0).label("rack_count"),
                func.coalesce(model_counts_subq.c.model_count, 0).label("model_count")
            )
            .outerjoin(device_stats_subq, Make.id == device_stats_subq.c.make_id)
            .outerjoin(model_counts_subq, Make.id == model_counts_subq.c.make_id)
            .order_by(Make.id.asc())
        )
        
        # Apply filters dynamically
        filter_config = {
            'make_name': (Make.name, 'exact'),
            'make_description': (Make.description, 'contains'),
        }
        filters = {
            'make_name': make_name,
            'make_description': make_description,
        }
        base_q = apply_filters(base_q, filters, filter_config)
        
        if device_type and device_type.strip():
            base_q = (
                base_q.join(DeviceType, Make.id == DeviceType.make_id)
                .filter(func.upper(DeviceType.name) == func.upper(device_type))
                .distinct()
            )
        if model_name and model_name.strip():
            base_q = (
                base_q.join(Model, Make.id == Model.make_id)
                .filter(func.upper(Model.name) == func.upper(model_name))
                .distinct()
            )
        
        # Use optimized pagination that gets count and data in single query
        total, rows = get_paginated_results(base_q, offset, page_size, Make.id)

        data = [
            {
                "id": make.id,
                "name": make.name,
                "description": make.description,
                "racks": int(rack_count),
                "devices": int(device_count),
                "models": int(model_count),
            }
            for make, device_count, rack_count, model_count in rows
        ]

        return total, data
    except exc.SQLAlchemyError as e:
        raise Exception(f"Database error in list_makes: {str(e)}")


def list_models(
    db: Session,
    offset: int,
    page_size: int,
    model_name: Optional[str] = None,
    model_description: Optional[str] = None,
    model_height: Optional[int] = None,
    make_name: Optional[str] = None,
    device_type: Optional[str] = None,
    **kwargs,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    List models with make names.
    Optimized: Explicit joins instead of lazy loading.
    """
    try:
        base_q = (
            db.query(
                Model,
                Make,
                DeviceType
            )
            .join(Make, Model.make_id == Make.id)
            .join(DeviceType, Model.device_type_id == DeviceType.id)
            .order_by(Model.id.asc())
        )
        
        # Apply filters dynamically
        filter_config = {
            'model_name': (Model.name, 'exact'),
            'model_description': (Model.description, 'contains'),
            'model_height': (Model.height, 'exact_int'),
            'make_name': (Make.name, 'exact'),
            'device_type': (DeviceType.name, 'exact'),
        }
        filters = {
            'model_name': model_name,
            'model_description': model_description,
            'model_height': model_height,
            'make_name': make_name,
            'device_type': device_type,
        }
        base_q = apply_filters(base_q, filters, filter_config)
        
        # Use optimized pagination that gets count and data in single query
        total, rows = get_paginated_results(base_q, offset, page_size, Model.id)

        data = [
            {
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "make_name": make.name if make else None,
                # "device_type_id": device_type.id if device_type else None,
                "device_type": device_type.name if device_type else None,
                "height": model.height,
            }
            for model, make, device_type in rows
        ]

        return total, data
    except exc.SQLAlchemyError as e:
        raise Exception(f"Database error in list_models: {str(e)}")


def list_datacenters(
    db: Session,
    offset: int,
    page_size: int,
    location_name: Optional[str] = None,
    building_name: Optional[str] = None,
    wing_name: Optional[str] = None,
    floor_name: Optional[str] = None,
    datacenter_name: Optional[str] = None,
    datacenter_description: Optional[str] = None,
    rack_name: Optional[str] = None,
    device_name: Optional[str] = None,
    allowed_location_ids: Optional[Set[int]] = None,
    **kwargs,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    List datacenters with related information and counts.
    Optimized: Combined query with rack/device counts, explicit joins.
    """
    try:
        # Optimize: Get rack and device counts in subqueries
        rack_counts_subq = (
            db.query(
                Rack.datacenter_id,
                func.count(Rack.id).label("rack_count")
            )
            .group_by(Rack.datacenter_id)
            .subquery()
        )
        
        device_counts_subq = (
            db.query(
                Device.dc_id,
                func.count(Device.id).label("device_count")
            )
            .group_by(Device.dc_id)
            .subquery()
        )
        
        base_q = (
            db.query(
                Datacenter,
                Location,
                Building,
                Wing,
                Floor,
                func.coalesce(rack_counts_subq.c.rack_count, 0).label("rack_count"),
                func.coalesce(device_counts_subq.c.device_count, 0).label("device_count")
            )
            .join(Location, Datacenter.location_id == Location.id)
            .join(Building, Datacenter.building_id == Building.id)
            .outerjoin(Wing, Datacenter.wing_id == Wing.id)
            .outerjoin(Floor, Datacenter.floor_id == Floor.id)
            .outerjoin(rack_counts_subq, Datacenter.id == rack_counts_subq.c.datacenter_id)
            .outerjoin(device_counts_subq, Datacenter.id == device_counts_subq.c.dc_id)
            .order_by(Datacenter.id.asc())
        )
        base_q = _restrict_to_locations(base_q, Datacenter.location_id, allowed_location_ids)
        
        # Apply filters dynamically
        filter_config = {
            'location_name': (Location.name, 'exact'),
            'building_name': (Building.name, 'exact'),
            'wing_name': (Wing.name, 'exact'),
            'floor_name': (Floor.name, 'exact'),
            'datacenter_name': (Datacenter.name, 'exact'),
            'datacenter_description': (Datacenter.description, 'contains'),
        }
        filters = {
            'location_name': location_name,
            'building_name': building_name,
            'wing_name': wing_name,
            'floor_name': floor_name,
            'datacenter_name': datacenter_name,
            'datacenter_description': datacenter_description,
        }
        base_q = apply_filters(base_q, filters, filter_config)
        
        if rack_name and rack_name.strip():
            base_q = (
                base_q.join(Rack, Datacenter.id == Rack.datacenter_id)
                .filter(func.upper(Rack.name) == func.upper(rack_name))
                .distinct()
            )
        if device_name and device_name.strip():
            base_q = (
                base_q.join(Device, Datacenter.id == Device.dc_id)
                .filter(func.upper(Device.name) == func.upper(device_name))
                .distinct()
            )
        
        # Use optimized pagination that gets count and data in single query
        total, rows = get_paginated_results(base_q, offset, page_size, Datacenter.id)

        data = [
            {
                "id": datacenter.id,
                "name": datacenter.name,
                "description": datacenter.description,
                "location_name": location.name if location else None,
                "building_name": building.name if building else None,
                "wing_name": wing.name if wing else None,
                "floor_name": floor.name if floor else None,
                "racks": int(rack_count),
                "devices": int(device_count),
            }
            for datacenter, location, building, wing, floor, rack_count, device_count in rows
        ]

        return total, data
    except exc.SQLAlchemyError as e:
        raise Exception(f"Database error in list_datacenters: {str(e)}")


# =============================================================================
# Entity handler mapping
# =============================================================================

ENTITY_LIST_HANDLERS: Dict[ListingType, Callable[..., Tuple[int, List[Dict[str, Any]]]]] = {
    ListingType.locations: list_locations,
    ListingType.buildings: list_buildings,
    ListingType.racks: list_racks,
    ListingType.devices: list_devices,
    ListingType.device_types: list_device_types,
    ListingType.makes: list_makes,
    ListingType.models: list_models,
    ListingType.datacenters: list_datacenters,
}

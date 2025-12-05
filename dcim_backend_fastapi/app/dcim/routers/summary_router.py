from functools import lru_cache
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.rbac_helper import AccessLevel, require_at_least_viewer
from app.helpers.summary_cache import (
    get_cached_location_summary,
    set_cached_location_summary,
)
from app.helpers.location_scope import get_allowed_location_ids


@lru_cache(maxsize=1)
def _get_entity_models():
    from app.models import entity_models as entity_models_module

    return entity_models_module


router = APIRouter(prefix="/api/dcim", tags=["DCIM Listings"])


@router.get(
    "/summary/locations",
    response_model=Dict[str, Any],
    summary="Summary per location: total devices, racks, device types",
)
def get_location_summary(
    access_level: AccessLevel = Depends(require_at_least_viewer),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Returns a summary per location:

    - id: Location ID
    - name: Location name
    - total_devices: Number of devices in that location
    - total_racks: Number of racks in that location
    - total_device_types: Number of DISTINCT device types used in that location
    """

    allowed_location_ids = get_allowed_location_ids(current_user, access_level)
    use_cache = allowed_location_ids is None

    cached = get_cached_location_summary() if use_cache else None
    if cached:
        return cached

    models = _get_entity_models()
    Location = models.Location
    Rack = models.Rack
    Device = models.Device

    device_agg_query = (
        db.query(
            Device.location_id.label("location_id"),
            func.count(Device.id).label("device_count"),
            func.count(func.distinct(Device.devicetype_id)).label("device_type_count"),
        )
        .group_by(Device.location_id)
    )
    if allowed_location_ids is not None:
        device_agg_query = device_agg_query.filter(Device.location_id.in_(allowed_location_ids))
    device_agg_subq = device_agg_query.subquery()

    rack_agg_query = (
        db.query(
            Rack.location_id.label("location_id"),
            func.count(Rack.id).label("rack_count"),
        )
        .group_by(Rack.location_id)
    )
    if allowed_location_ids is not None:
        rack_agg_query = rack_agg_query.filter(Rack.location_id.in_(allowed_location_ids))
    rack_agg_subq = rack_agg_query.subquery()

    rows_query = (
        db.query(
            Location,
            func.coalesce(device_agg_subq.c.device_count, 0).label("device_count"),
            func.coalesce(device_agg_subq.c.device_type_count, 0).label("device_type_count"),
            func.coalesce(rack_agg_subq.c.rack_count, 0).label("rack_count"),
        )
        .outerjoin(device_agg_subq, Location.id == device_agg_subq.c.location_id)
        .outerjoin(rack_agg_subq, Location.id == rack_agg_subq.c.location_id)
        .order_by(Location.id.asc())
    )
    if allowed_location_ids is not None:
        rows_query = rows_query.filter(Location.id.in_(allowed_location_ids))
    rows = rows_query.all()

    results: List[Dict[str, Any]] = []
    for location, device_count, device_type_count, rack_count in rows:
        results.append(
            {
                "id": location.id,
                "name": location.name,
                "total_devices": int(device_count or 0),
                "total_racks": int(rack_count or 0),
                "total_device_types": int(device_type_count or 0),
            }
        )

    payload = {
        "total_locations": len(results),
        "results": results,
    }
    if use_cache:
        set_cached_location_summary(payload)
    return payload

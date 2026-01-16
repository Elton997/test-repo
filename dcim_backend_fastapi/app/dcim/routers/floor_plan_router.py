from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.rbac_helper import AccessLevel, require_at_least_viewer
from app.models.entity_models import Datacenter, Location, Building, Wing, Floor, Rack
from app.schemas.entity_schemas import DatacenterWithRacksOut

router = APIRouter(prefix="/api/dcim", tags=["Datacenter Hierarchy"])


@router.get("/floor-plan", response_model=List[DatacenterWithRacksOut])
def get_floor_plan(
    location_id: int = Query(..., description="Location ID"),
    building_id: int = Query(..., description="Building ID"),
    wing_id: int = Query(..., description="Wing ID"),
    floor_id: int = Query(..., description="Floor ID"),
    db: Session = Depends(get_db),
    access_level: AccessLevel = Depends(require_at_least_viewer),
    current_user=Depends(get_current_user),
):
    """
    Retrieve floor plan data (datacenters and racks) for a specific hierarchy.
    Location -> Building -> Wing -> Floor -> Datacenters -> Racks.
    """
    
    # Base query for Datacenter
    query = select(Datacenter).join(Location).join(Building).join(Wing).join(Floor)

    # Apply filters
    query = query.where(
        Location.id == location_id,
        Building.id == building_id,
        Wing.id == wing_id,
        Floor.id == floor_id
    )

    # Eager load racks to avoid N+1 and ensure they are included in the response
    query = query.options(
        selectinload(Datacenter.racks)
    )

    datacenters = db.execute(query).scalars().all()

    if not datacenters:
        # Check if the hierarchy itself exists to distinguish between "no datacenters" and "bad path"
        # For simplicity, we just return empty list if no datacenters found, 
        # or we could verify the path exists first. 
        # For now, returning empty list is standard filtering behavior.
        return []

    return datacenters

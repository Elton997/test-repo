"""
Utilities for tracking rack capacity (space used/available).
"""
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.entity_models import Rack, Device


def _recalculate_available_space(rack: Rack) -> None:
    """Recompute available units from height and used space."""
    rack_height = rack.height or 0
    used = rack.space_used or 0
    rack.space_available = max(rack_height - used, 0)


def ensure_rack_capacity(rack: Rack, space_required: int) -> None:
    """
    Validate that the rack has enough free units for the incoming device.
    Raises HTTP 400 if the request exceeds capacity.
    """
    if space_required <= 0:
        return

    if rack.space_available is None:
        _recalculate_available_space(rack)

    available = rack.space_available or 0
    if available < space_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Rack '{rack.name}' only has {available}U available "
                f"but {space_required}U is required"
            ),
        )


def ensure_continuous_space(
    db: Session,
    rack: Rack,
    position: Optional[int],
    space_required: int,
    exclude_device_id: Optional[int] = None,
) -> None:
    """
    Validate that there is continuous space available at the specified position.
    
    This function checks:
    1. Position is valid (>= 1)
    2. Position + space_required doesn't exceed rack height
    3. The requested position range doesn't overlap with any existing devices
    
    Args:
        db: Database session
        rack: The rack to check
        position: Starting position (1-based)
        space_required: Number of continuous units needed
        exclude_device_id: Optional device ID to exclude from overlap check (for updates)
    
    Raises:
        HTTPException: If position is invalid or space is not available
    """
    if space_required <= 0:
        return
    
    if position is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position is required for device placement",
        )
    
    if position < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Position must be >= 1, got {position}",
        )
    
    rack_height = rack.height or 0
    if rack_height == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rack '{rack.name}' has no height defined",
        )
    
    # Calculate the end position (inclusive)
    end_position = position + space_required - 1
    
    # Check if the range exceeds rack height
    if end_position > rack_height:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Device position {position} + space {space_required} "
                f"(ends at position {end_position}) exceeds rack height {rack_height}"
            ),
        )
    
    # Query all devices in the rack (excluding the device being updated if specified)
    query = db.query(Device).filter(Device.rack_id == rack.id)
    if exclude_device_id is not None:
        query = query.filter(Device.id != exclude_device_id)
    
    existing_devices = query.filter(Device.position.isnot(None)).all()
    
    # Check for overlaps with existing devices
    requested_positions = set(range(position, end_position + 1))
    
    for device in existing_devices:
        if device.position is None:
            continue
        
        device_space = device.space_required or 1
        device_start = device.position
        device_end = device_start + device_space - 1
        
        # Calculate occupied positions for this device
        occupied_positions = set(range(device_start, device_end + 1))
        
        # Check for overlap
        overlap = requested_positions & occupied_positions
        if overlap:
            overlap_list = sorted(list(overlap))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot place device at position {position} (requires {space_required}U, "
                    f"positions {position}-{end_position}). "
                    f"Positions {overlap_list[0]}-{overlap_list[-1]} are already occupied by "
                    f"device '{device.name}' (position {device_start}, {device_space}U)"
                ),
            )


def reserve_rack_capacity(rack: Rack, space_required: int) -> None:
    """Consume rack space after a device is added."""
    if space_required <= 0:
        return

    ensure_rack_capacity(rack, space_required)
    rack.space_used = (rack.space_used or 0) + space_required
    _recalculate_available_space(rack)


def release_rack_capacity(rack: Rack, space_released: int) -> None:
    """Give back rack space when a device is removed or resized."""
    if space_released <= 0:
        return

    rack.space_used = max((rack.space_used or 0) - space_released, 0)
    _recalculate_available_space(rack)



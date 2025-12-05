"""
DCIM Export Router - Streams listing data as CSV downloads.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.rbac_helper import AccessLevel, require_at_least_viewer
from app.helpers.listing_types import ListingType
from app.helpers.location_scope import get_allowed_location_ids

router = APIRouter(prefix="/api/dcim", tags=["DCIM Export"])


def _normalize_empty_to_none(value: Union[str, int, date, None]) -> Union[str, int, date, None]:
    """Convert empty strings to None for optional parameters."""
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _parse_optional_int(value: Union[str, int, None]) -> Optional[int]:
    """Parse optional integer parameter, converting empty strings to None."""
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip() == "":
            return None
        try:
            return int(value)
        except ValueError:
            return None
    return int(value)


def _parse_optional_date(value: Union[str, date, None]) -> Optional[date]:
    """Parse optional date parameter, converting empty strings to None."""
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip() == "":
            return None
        try:
            # Try parsing ISO format date (YYYY-MM-DD)
            return date.fromisoformat(value)
        except ValueError:
            return None
    return value if isinstance(value, date) else None

DEFAULT_EXPORT_CHUNK_SIZE = 500

ENTITY_EXPORT_HEADERS: Dict[ListingType, List[str]] = {
    ListingType.device_types: [
        "id",
        "name",
        "description",
        "make",
        "u_height",
        "devices",
        "model_id",
        "model_name",
        "model_height",
        "models_count",
    ],
    ListingType.models: [
        "id",
        "name",
        "description",
        "make_name",
        "device_type_id",
        "device_type_name",
        "device_type_height",
        "height",
    ],
}


def _get_listing_handler(entity: ListingType):
    """Lazy import heavy listing helper only when an export is requested."""
    from app.helpers.listing_helper import ENTITY_LIST_HANDLERS

    return ENTITY_LIST_HANDLERS.get(entity)


def _get_pandas():
    import pandas as pd

    return pd


def _prepare_export_row(entity: ListingType, record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize nested listing payloads into flat rows so CSV exports stay consistent.
    """
    if entity == ListingType.device_types:
        model = record.get("model") or {}
        return {
            "id": record.get("id"),
            "name": record.get("name"),
            "description": record.get("description"),
            "make": record.get("make"),
            "u_height": record.get("u_height"),
            "devices": record.get("devices"),
            "model_id": model.get("id"),
            "model_name": model.get("name"),
            "model_height": model.get("height"),
            "models_count": record.get("models_count"),
        }

    if entity == ListingType.models:
        device_type = record.get("device_type") or {}
        return {
            "id": record.get("id"),
            "name": record.get("name"),
            "description": record.get("description"),
            "make_name": record.get("make_name"),
            "device_type_id": device_type.get("id"),
            "device_type_name": device_type.get("name"),
            "device_type_height": device_type.get("height"),
            "height": record.get("height"),
        }

    return dict(record)


def _resolve_headers(entity: ListingType, row: Dict[str, Any]) -> List[str]:
    """
    Merge predefined headers (for flattened entities) with dynamic keys gathered
    from the listing payload so all available columns are exported.
    """
    configured = ENTITY_EXPORT_HEADERS.get(entity, [])
    if not configured:
        return list(row.keys())

    dynamic_keys = [key for key in row.keys() if key not in configured]
    return configured + dynamic_keys


def _export_stream(
    entity: ListingType,
    handler,
    handler_kwargs: Dict[str, Any],
) -> Any:
    """
    Stream CSV rows in chunks to avoid keeping large payloads in memory.
    """
    pd = _get_pandas()

    headers: Optional[List[str]] = None
    header_written = False
    offset = 0
    total_records: Optional[int] = None

    while True:
        batch_total, records = handler(
            offset=offset,
            page_size=DEFAULT_EXPORT_CHUNK_SIZE,
            **handler_kwargs,
        )
        if total_records is None:
            total_records = batch_total

        if not records:
            break

        chunk_rows: List[Dict[str, Any]] = []
        for record in records:
            row = _prepare_export_row(entity, record)
            if headers is None:
                headers = _resolve_headers(entity, row)
            else:
                for key in row.keys():
                    if key not in headers:
                        headers.append(key)
            chunk_rows.append(row)

        if not chunk_rows:
            continue

        df = pd.DataFrame(chunk_rows)
        if headers:
            for column in headers:
                if column not in df.columns:
                    df[column] = None
            df = df[headers]

        csv_payload = df.to_csv(index=False, header=not header_written)
        header_written = True
        yield csv_payload

        offset += len(records)
        if total_records is not None and offset >= total_records:
            break

    if not header_written:
        fallback_headers = ENTITY_EXPORT_HEADERS.get(entity)
        if fallback_headers:
            df = pd.DataFrame(columns=fallback_headers)
            yield df.to_csv(index=False)


@router.get(
    "/list/export",
    response_class=StreamingResponse,
    summary="Export DCIM listing data to CSV",
)
def export_dcim_entities(
    entity: ListingType = Query(
        ...,
        description="Entity to export: locations | buildings | racks | devices | device_types | makes | models | datacenters",
    ),
    # Location filters
    location_name: Optional[str] = Query(None, description="Filter by location name"),
    location_description: Optional[str] = Query(None, description="Filter by location description"),
    # Building filters
    building_name: Optional[str] = Query(None, description="Filter by building name"),
    building_status: Optional[str] = Query(None, description="Filter by building status"),
    building_description: Optional[str] = Query(None, description="Filter by building description"),
    # Wing filters
    wing_name: Optional[str] = Query(None, description="Filter by wing name"),
    # Floor filters
    floor_name: Optional[str] = Query(None, description="Filter by floor name"),
    # Rack filters
    rack_name: Optional[str] = Query(None, description="Filter by rack name"),
    rack_status: Optional[str] = Query(None, description="Filter by rack status"),
    rack_height: Optional[Union[str, int]] = Query(None, description="Filter by rack height"),
    rack_description: Optional[str] = Query(None, description="Filter by rack description"),
    # Device filters
    device_name: Optional[str] = Query(None, description="Filter by device name"),
    device_status: Optional[str] = Query(None, description="Filter by device status"),
    device_position: Optional[Union[str, int]] = Query(None, description="Filter by device position"),
    device_face: Optional[str] = Query(None, description="Filter by device face (front/rear)"),
    device_description: Optional[str] = Query(None, description="Filter by device description"),
    serial_number: Optional[str] = Query(None, description="Filter by device serial number"),
    ip_address: Optional[str] = Query(None, description="Filter by device IP address"),
    po_number: Optional[str] = Query(None, description="Filter by device PO number"),
    asset_user: Optional[str] = Query(None, description="Filter by device asset user"),
    asset_owner: Optional[str] = Query(None, description="Filter by device asset owner name"),
    applications_mapped_name: Optional[str] = Query(None, description="Filter by application mapped name"),
    warranty_start_date: Optional[Union[str, date]] = Query(None, description="Filter by warranty start date (YYYY-MM-DD)"),
    warranty_end_date: Optional[Union[str, date]] = Query(None, description="Filter by warranty end date (YYYY-MM-DD)"),
    amc_start_date: Optional[Union[str, date]] = Query(None, description="Filter by AMC start date (YYYY-MM-DD)"),
    amc_end_date: Optional[Union[str, date]] = Query(None, description="Filter by AMC end date (YYYY-MM-DD)"),
    # Device type filters
    device_type: Optional[str] = Query(None, description="Filter by device type name"),
    device_type_description: Optional[str] = Query(None, description="Filter by device type description"),
    # Make filters
    make_name: Optional[str] = Query(None, description="Filter by make name"),
    make_description: Optional[str] = Query(None, description="Filter by make description"),
    # Model filters
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    model_description: Optional[str] = Query(None, description="Filter by model description"),
    model_height: Optional[Union[str, int]] = Query(None, description="Filter by model height"),
    # Datacenter filters
    datacenter_name: Optional[str] = Query(None, description="Filter by datacenter name"),
    datacenter_description: Optional[str] = Query(None, description="Filter by datacenter description"),
    access_level: AccessLevel = Depends(require_at_least_viewer),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Export listing data as CSV for the requested entity.
    Uses the same filtering rules as the pagination endpoint but streams the output.
    All filters are applied at the database level for optimal performance.
    """
    handler = _get_listing_handler(entity)

    if not handler:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV export is not supported for entity type: {entity}",
        )

    allowed_location_ids = get_allowed_location_ids(current_user, access_level)

    # Normalize empty strings to None for string parameters
    # Parse integer and date parameters, converting empty strings to None
    rack_height_parsed = _parse_optional_int(rack_height)
    device_position_parsed = _parse_optional_int(device_position)
    model_height_parsed = _parse_optional_int(model_height)
    warranty_start_date_parsed = _parse_optional_date(warranty_start_date)
    warranty_end_date_parsed = _parse_optional_date(warranty_end_date)
    amc_start_date_parsed = _parse_optional_date(amc_start_date)
    amc_end_date_parsed = _parse_optional_date(amc_end_date)
    
    # Collect all filter parameters into a dictionary (same as listing router)
    filter_params = {
        'location_name': _normalize_empty_to_none(location_name),
        'location_description': _normalize_empty_to_none(location_description),
        'building_name': _normalize_empty_to_none(building_name),
        'building_status': _normalize_empty_to_none(building_status),
        'building_description': _normalize_empty_to_none(building_description),
        'wing_name': _normalize_empty_to_none(wing_name),
        'floor_name': _normalize_empty_to_none(floor_name),
        'rack_name': _normalize_empty_to_none(rack_name),
        'rack_status': _normalize_empty_to_none(rack_status),
        'rack_height': rack_height_parsed,
        'rack_description': _normalize_empty_to_none(rack_description),
        'device_name': _normalize_empty_to_none(device_name),
        'device_status': _normalize_empty_to_none(device_status),
        'device_position': device_position_parsed,
        'device_face': _normalize_empty_to_none(device_face),
        'device_description': _normalize_empty_to_none(device_description),
        'serial_number': _normalize_empty_to_none(serial_number),
        'ip_address': _normalize_empty_to_none(ip_address),
        'po_number': _normalize_empty_to_none(po_number),
        'asset_user': _normalize_empty_to_none(asset_user),
        'asset_owner': _normalize_empty_to_none(asset_owner),
        'applications_mapped_name': _normalize_empty_to_none(applications_mapped_name),
        'warranty_start_date': warranty_start_date_parsed,
        'warranty_end_date': warranty_end_date_parsed,
        'amc_start_date': amc_start_date_parsed,
        'amc_end_date': amc_end_date_parsed,
        'device_type': _normalize_empty_to_none(device_type),
        'device_type_description': _normalize_empty_to_none(device_type_description),
        'make_name': _normalize_empty_to_none(make_name),
        'make_description': _normalize_empty_to_none(make_description),
        'model_name': _normalize_empty_to_none(model_name),
        'model_description': _normalize_empty_to_none(model_description),
        'model_height': model_height_parsed,
        'datacenter_name': _normalize_empty_to_none(datacenter_name),
        'datacenter_description': _normalize_empty_to_none(datacenter_description),
    }

    filter_kwargs = {
        "db": db,
        "allowed_location_ids": allowed_location_ids,
        **filter_params,
    }

    filename = f"{entity.value}_listing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        _export_stream(entity, handler, filter_kwargs),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


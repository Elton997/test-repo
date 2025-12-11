"""
DCIM Bulk Upload Router - API for bulk creating DCIM entities via CSV upload.
Supports uploading CSV files for any entity type with detailed row-by-row results.
Uses pandas for robust CSV parsing.

Supported entity types:
- devices: Single device entities
- racks: Single rack entities
- entity_wfd: Wings, Floors, Datacenters (hierarchical)
- entity_asset_details: Asset Owners, Applications Mapped
- entity_devicetypes: Makes, Device Types, Models
"""
import io
import re
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable

import pandas as pd
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from app.core.logger import app_logger
from app.db.session import SessionLocal
from app.helpers.rbac_helper import AccessLevel, require_editor_or_admin
from app.helpers.listing_types import ListingType
from app.helpers.add_entity_helper import ENTITY_CREATE_HANDLERS
from app.helpers.auth_helper import get_current_user
from app.helpers.audit_helper import build_audit_context, log_create
from app.helpers.email_helper import send_bulk_upload_report
from app.schemas.entity_schemas import ENTITY_CREATE_SCHEMAS
from app.models.auth_models import User
from app.helpers.listing_cache import invalidate_listing_cache_for_entity
from app.helpers.summary_cache import invalidate_location_summary_cache

router = APIRouter(prefix="/api/dcim", tags=["DCIM Bulk Upload"])


class BulkUploadEntityType(str, Enum):
    """Supported entity types for bulk upload."""
    devices = "devices"
    racks = "racks"
    entity_wfd = "entity_wfd"  # Wings, Floors, Datacenters
    entity_asset_details = "entity_asset_details"  # Asset Owner, Applications Mapped
    entity_devicetypes = "entity_devicetypes"  # Makes, Device Types, Models


# CSV column to schema field mapping
# Maps common CSV column names (case-insensitive) to schema field names
CSV_COLUMN_MAPPING = {
    # Device mappings
    "hostname": "name",
    "host name": "name",
    "device name": "name",
    "asset status": "status",
    "asset_status": "status",
    "building": "building_name",
    "location": "location_name",
    "wing": "wing_name",
    "floor": "floor_name",
    "room/area": "datacenter_name",
    "room area": "datacenter_name",
    "room_area": "datacenter_name",
    "datacenter": "datacenter_name",
    "rack no": "rack_name",
    "rack_no": "rack_name",
    "rack number": "rack_name",
    "rack_number": "rack_name",
    "rack": "rack_name",
    "manufacturer": "make_name",
    "make": "make_name",
    "model id": "model_name",
    "model_id": "model_name",
    "model": "model_name",
    "asset type": "devicetype_name",
    "asset_type": "devicetype_name",
    "device type": "devicetype_name",
    "device_type": "devicetype_name",
    "ip address": "ip",
    "ip_address": "ip",
    "ip": "ip",
    "asset po number": "po_number",
    "asset_po_number": "po_number",
    "po number": "po_number",
    "po_number": "po_number",
    "asset owner": "asset_owner_name",
    "asset_owner": "asset_owner_name",
    "owner": "asset_owner_name",
    "asset user": "asset_user",
    "asset_user": "asset_user",
    "application mapped": "application_name",
    "application_mapped": "application_name",
    "application": "application_name",
    "warranty start date": "warranty_start_date",
    "warranty_start_date": "warranty_start_date",
    "warranty start": "warranty_start_date",
    "warranty_end_date": "warranty_end_date",
    "warranty end date": "warranty_end_date",
    "warranty end": "warranty_end_date",
    "amc start date": "amc_start_date",
    "amc_start_date": "amc_start_date",
    "amc start": "amc_start_date",
    "amc end date": "amc_end_date",
    "amc_end_date": "amc_end_date",
    "amc end": "amc_end_date",
    # Face field (mandatory for devices)
    "face": "face",
    "device face": "face",
    "rack face": "face",
    # Serial number field
    "serial no": "serial_no",
    "serial_no": "serial_no",
    "serial number": "serial_no",
    "serial_number": "serial_no",
    # Position field
    "position": "position",
    "rack position": "position",
    "rack_position": "position",
    "u position": "position",
    "u_position": "position",
    "start position": "position",
    # Space required field
    "space required": "space_required",
    "space_required": "space_required",
    # Rack-specific mappings
    "rack name": "name",
    "rack_name": "name",
    "height": "height",
    "rack height": "height",
    # Device type mappings
    "device type name": "name",
    "devicetype name": "name",
    "devicetype_name": "devicetype_name",
    # Model mappings
    "model name": "name",
    "model_name": "name",
    "height u": "height",
    "height_u": "height",
    "model height": "height",
    # Make mappings
    "make name": "name",
    "make_name": "name",
    # Application mappings
    "application name": "name",
    "application_name": "name",
    # Asset owner mappings
    "asset owner name": "asset_owner_name",
    # Location hierarchy mappings
    "location name": "location_name",
    "building name": "building_name",
    "wing name": "wing_name",
    "floor name": "floor_name",
    "datacenter name": "datacenter_name",
}

# Integer fields that need type conversion
INT_FIELDS = {"position", "height", "space_required"}

# Date fields that need string format
DATE_FIELDS = {"warranty_start_date", "warranty_end_date", "amc_start_date", "amc_end_date"}

BULK_COMMIT_CHUNK_SIZE = 100

# Entity type configurations for multi-entity processing
ENTITY_CONFIGS = {
    "entity_wfd": {
        "entities": [
            {"type": ListingType.wings, "name_key": "wing_name", "fallback_key": "name"},
            {"type": ListingType.floors, "name_key": "floor_name", "fallback_key": "name"},
            {"type": ListingType.datacenters, "name_key": "datacenter_name", "fallback_key": "name"},
        ],
        "cache_keys": [ListingType.wings, ListingType.floors, ListingType.datacenters],
    },
    "entity_asset_details": {
        "entities": [
            {"type": ListingType.asset_owner, "name_key": "asset_owner_name", "fallback_key": "name"},
            {"type": ListingType.applications, "name_key": "name", "fallback_key": "application_name"},
        ],
        "cache_keys": [ListingType.asset_owner, ListingType.applications],
    },
    "entity_devicetypes": {
        "entities": [
            {"type": ListingType.makes, "name_key": "make_name", "fallback_key": "name"},
            {"type": ListingType.device_types, "name_key": "devicetype_name", "fallback_key": "name"},
            {"type": ListingType.models, "name_key": "model_name", "fallback_key": "name"},
        ],
        "cache_keys": [ListingType.makes, ListingType.device_types, ListingType.models],
    },
}


def check_row_uniqueness_for_bulk(
    entity_type: str, data: Dict[str, Any], db: Session
) -> Optional[str]:
    """
    Check if a complete row already exists in the database for bulk upload.
    Returns an error message if duplicate found, None otherwise.
    """
    from app.helpers.add_entity_helper import (
        get_location_by_name,
        get_building_by_name,
        get_wing_by_name,
        get_floor_by_name,
        get_datacenter_by_name,
        get_asset_owner_by_name,
    )
    from app.models.entity_models import Wing, Floor, Datacenter, ApplicationMapped
    
    try:
        if entity_type == "wing":
            location = get_location_by_name(db, data["location_name"])
            building = get_building_by_name(db, data["building_name"])
            existing = (
                db.query(Wing)
                .filter(func.upper(Wing.name) == func.upper(data["name"]))
                .filter(Wing.location_id == location.id)
                .filter(Wing.building_id == building.id)
                .first()
            )
            if existing:
                return f"Wing with name '{data['name']}' already exists in location '{data['location_name']}' and building '{data['building_name']}'"
        
        elif entity_type == "floor":
            location = get_location_by_name(db, data["location_name"])
            building = get_building_by_name(db, data["building_name"])
            wing = get_wing_by_name(db, data["wing_name"])
            existing = (
                db.query(Floor)
                .filter(func.upper(Floor.name) == func.upper(data["name"]))
                .filter(Floor.location_id == location.id)
                .filter(Floor.building_id == building.id)
                .filter(Floor.wing_id == wing.id)
                .first()
            )
            if existing:
                return f"Floor with name '{data['name']}' already exists in location '{data['location_name']}', building '{data['building_name']}', and wing '{data['wing_name']}'"
        
        elif entity_type == "datacenter":
            location = get_location_by_name(db, data["location_name"])
            building = get_building_by_name(db, data["building_name"])
            wing = get_wing_by_name(db, data["wing_name"])
            floor = get_floor_by_name(db, data["floor_name"])
            existing = (
                db.query(Datacenter)
                .filter(func.upper(Datacenter.name) == func.upper(data["name"]))
                .filter(Datacenter.location_id == location.id)
                .filter(Datacenter.building_id == building.id)
                .filter(Datacenter.wing_id == wing.id)
                .filter(Datacenter.floor_id == floor.id)
                .first()
            )
            if existing:
                return f"Datacenter with name '{data['name']}' already exists in location '{data['location_name']}', building '{data['building_name']}', wing '{data['wing_name']}', and floor '{data['floor_name']}'"
        
        elif entity_type == "application":
            asset_owner = get_asset_owner_by_name(db, data["asset_owner_name"])
            existing = (
                db.query(ApplicationMapped)
                .filter(func.upper(ApplicationMapped.name) == func.upper(data["name"]))
                .filter(ApplicationMapped.asset_owner_id == asset_owner.id)
                .first()
            )
            if existing:
                return f"Application with name '{data['name']}' already exists for asset owner '{data['asset_owner_name']}'"
    except Exception:
        pass
    
    return None


def normalize_column_name(col_name: str) -> str:
    """Normalize CSV column names for consistent mapping."""
    normalized = col_name.strip().lower()
    normalized = re.sub(r'[\s_/]+', ' ', normalized)
    return normalized.strip()


def clean_dataframe_row(row: pd.Series, apply_mapping: bool = True, original_columns: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Convert a pandas DataFrame row to a clean dictionary."""
    result = {}
    for col, value in row.items():
        if pd.isna(value):
            continue
        
        if apply_mapping:
            if original_columns and col in original_columns:
                original_col = original_columns[col]
                if '_' in original_col:
                    schema_field = original_col
                else:
                    schema_field = CSV_COLUMN_MAPPING.get(col, col)
            elif col in CSV_COLUMN_MAPPING:
                schema_field = CSV_COLUMN_MAPPING[col]
            else:
                schema_field = col
        else:
            schema_field = col
        
        if schema_field in INT_FIELDS:
            try:
                result[schema_field] = int(value)
            except (ValueError, TypeError):
                continue
        elif schema_field in DATE_FIELDS:
            if isinstance(value, pd.Timestamp):
                result[schema_field] = value.strftime("%Y-%m-%d")
            elif isinstance(value, str) and value.strip():
                date_str = value.strip()
                try:
                    parsed_date = pd.to_datetime(date_str, errors='raise')
                    result[schema_field] = parsed_date.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    result[schema_field] = date_str
        else:
            str_value = str(value).strip()
            if str_value:
                result[schema_field] = str_value
    
    return result


def _load_dataframe_from_bytes(file_bytes: bytes) -> pd.DataFrame:
    """Parse CSV bytes into a normalized dataframe."""
    try:
        for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=encoding,
                    dtype=str,
                    keep_default_na=True,
                    na_values=["", "NA", "N/A", "null", "NULL", "None"],
                )
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("File encoding not supported. Please use UTF-8 encoding.")
    except pd.errors.EmptyDataError as exc:
        raise ValueError("CSV file is empty") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"Failed to parse CSV file: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Failed to read CSV file: {exc}") from exc

    if df.empty:
        raise ValueError("CSV file must have at least one data row")

    original_columns = {normalize_column_name(col): col for col in df.columns}
    df.columns = [normalize_column_name(col) for col in df.columns]
    df = df.dropna(how="all")

    if df.empty:
        raise ValueError("CSV file has no valid data rows")

    df.attrs['original_columns'] = original_columns
    return df


def _process_row_error(
    exc: Exception,
    row_result: Dict[str, Any],
    db: Session,
    skip_errors: bool,
    pending_commit: int,
) -> Tuple[bool, int]:
    """Handle row processing errors. Returns (aborted_early, new_pending_commit)."""
    db.rollback()
    pending_commit = 0
    row_result["status"] = "error"
    error_msg = str(exc.orig if isinstance(exc, IntegrityError) else exc)
    
    if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
        if isinstance(exc, IntegrityError):
            entity_name = row_result.get("entity_type", "Entity")
            row_result["error"] = f"Duplicate data insertion: {entity_name} already exists"
        else:
            row_result["error"] = error_msg
    else:
        if isinstance(exc, IntegrityError):
            row_result["error"] = f"Database integrity error: {error_msg}"
        else:
            row_result["error"] = error_msg
    
    return (not skip_errors, pending_commit)


def _process_single_entity_rows(
    db: Session,
    file_bytes: bytes,
    skip_errors: bool,
    current_user: Optional[User],
    audit_context: Optional[Dict[str, Any]],
    entity: ListingType,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Generic processor for single entity type per row (devices, racks)."""
    schema_class = ENTITY_CREATE_SCHEMAS.get(entity)
    handler = ENTITY_CREATE_HANDLERS.get(entity)
    
    if not schema_class or not handler:
        raise ValueError(f"Unsupported entity type: {entity}")

    df = _load_dataframe_from_bytes(file_bytes)
    original_columns = df.attrs.get('original_columns', {})

    results: List[Dict[str, Any]] = []
    success_count = 0
    error_count = 0
    aborted_early = False
    pending_commit = 0

    for idx, row in df.iterrows():
        row_number = idx + 2
        row_result: Dict[str, Any] = {
            "row": row_number,
            "status": "pending",
            "data": None,
            "error": None,
        }

        try:
            row_data = clean_dataframe_row(row, original_columns=original_columns)
            row_result["input"] = row_data

            if not row_data:
                row_result["status"] = "skipped"
                row_result["error"] = "Row contained no usable data."
                results.append(row_result)
                continue

            try:
                validated_data = schema_class(**row_data)
            except Exception as exc:
                raise ValueError(f"Validation error: {exc}")

            result = handler(db, validated_data.model_dump())
            object_id = result.get("id") or result.get(f"{entity.value}_id")
            
            if object_id and audit_context:
                row_context = {**audit_context, "row": row_number}
                log_create(
                    db=db,
                    user=current_user,
                    entity_type=entity.value,
                    object_id=object_id,
                    entity_data=result,
                    context=row_context,
                )

            row_result["status"] = "success"
            row_result["data"] = result
            success_count += 1
            pending_commit += 1

            if pending_commit >= BULK_COMMIT_CHUNK_SIZE:
                try:
                    db.commit()
                    pending_commit = 0
                except Exception as exc:
                    db.rollback()
                    pending_commit = 0
                    raise RuntimeError(f"Failed to commit batch ending at row {row_number}: {exc}") from exc

        except (IntegrityError, Exception) as exc:
            aborted, pending_commit = _process_row_error(exc, row_result, db, skip_errors, pending_commit)
            error_count += 1
            if aborted:
                aborted_early = True
                results.append(row_result)
                break

        results.append(row_result)

    if aborted_early:
        db.rollback()
        pending_commit = 0
    elif success_count > 0 and pending_commit > 0:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"Failed to commit changes: {exc}") from exc

    return {
        "entity": entity.value,
        "total_rows": len(df),
        "processed": len(results),
        "success": success_count,
        "errors": error_count,
        "aborted": aborted_early,
        "skip_errors": skip_errors,
    }, results


def _extract_entity_data_from_row(
    row_data: Dict[str, Any],
    raw_row: Dict[str, str],
    entity_config: Dict[str, Any],
    entity_type: ListingType,
) -> Dict[str, Any]:
    """Extract entity-specific data from row based on configuration."""
    name_key = entity_config["name_key"]
    fallback_key = entity_config.get("fallback_key", "name")
    
    # Try to get name from raw row first (before mapping)
    entity_name = None
    for col in raw_row.keys():
        col_lower = normalize_column_name(col)
        if col_lower in [normalize_column_name(name_key), normalize_column_name(fallback_key)]:
            entity_name = str(raw_row[col]).strip()
            break
    
    # Fallback to mapped row_data
    if not entity_name:
        entity_name = row_data.get(name_key) or row_data.get(fallback_key)
    
    # Build entity data based on type
    if entity_type == ListingType.wings:
        return {
            "name": entity_name,
            "location_name": row_data.get("location_name") or row_data.get("location"),
            "building_name": row_data.get("building_name") or row_data.get("building"),
            "description": row_data.get("description", ""),
        }
    elif entity_type == ListingType.floors:
        return {
            "name": entity_name,
            "location_name": row_data.get("location_name") or row_data.get("location"),
            "building_name": row_data.get("building_name") or row_data.get("building"),
            "wing_name": row_data.get("wing_name") or row_data.get("wing"),
            "description": row_data.get("description", ""),
        }
    elif entity_type == ListingType.datacenters:
        return {
            "name": entity_name,
            "location_name": row_data.get("location_name") or row_data.get("location"),
            "building_name": row_data.get("building_name") or row_data.get("building"),
            "wing_name": row_data.get("wing_name") or row_data.get("wing"),
            "floor_name": row_data.get("floor_name") or row_data.get("floor"),
            "description": row_data.get("description", ""),
        }
    elif entity_type == ListingType.asset_owner:
        return {
            "name": entity_name,
            "location_name": row_data.get("location_name") or row_data.get("location"),
            "description": row_data.get("asset_owner_description") or row_data.get("description", ""),
        }
    elif entity_type == ListingType.applications:
        return {
            "name": row_data.get("name") or row_data.get("application_name"),
            "asset_owner_name": row_data.get("asset_owner_name"),
            "description": row_data.get("application_description") or row_data.get("description", ""),
        }
    elif entity_type == ListingType.makes:
        return {
            "name": entity_name,
            "description": row_data.get("make_description") or row_data.get("description", ""),
        }
    elif entity_type == ListingType.device_types:
        make_name = None
        for col in raw_row.keys():
            col_lower = normalize_column_name(col)
            if col_lower in ["make name", "make_name", "manufacturer"]:
                make_name = str(raw_row[col]).strip()
                break
        if not make_name:
            make_name = row_data.get("make_name") or row_data.get("manufacturer")
        
        return {
            "name": entity_name,
            "make_name": make_name,
            "description": row_data.get("devicetype_description") or row_data.get("description", ""),
        }
    elif entity_type == ListingType.models:
        make_name = None
        devicetype_name = None
        for col in raw_row.keys():
            col_lower = normalize_column_name(col)
            if col_lower in ["make name", "make_name", "manufacturer"]:
                make_name = str(raw_row[col]).strip()
            elif col_lower in ["devicetype name", "devicetype_name", "device type name", "device_type", "asset type"]:
                devicetype_name = str(raw_row[col]).strip()
        
        if not make_name:
            make_name = row_data.get("make_name") or row_data.get("manufacturer")
        if not devicetype_name:
            devicetype_name = row_data.get("devicetype_name") or row_data.get("device_type") or row_data.get("asset_type")
        
        height_value = row_data.get("height") or row_data.get("model_height")
        if height_value:
            try:
                height_value = int(height_value)
            except (ValueError, TypeError):
                height_value = None
        
        return {
            "name": entity_name,
            "make_name": make_name,
            "devicetype_name": devicetype_name,
            "height": height_value,
            "description": row_data.get("model_description") or row_data.get("description", ""),
        }
    
    return {}


def _process_multi_entity_rows(
    db: Session,
    file_bytes: bytes,
    skip_errors: bool,
    current_user: Optional[User],
    audit_context: Optional[Dict[str, Any]],
    config_key: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Generic processor for multiple entity types per row."""
    config = ENTITY_CONFIGS[config_key]
    df = _load_dataframe_from_bytes(file_bytes)
    original_columns = df.attrs.get('original_columns', {})
    
    results: List[Dict[str, Any]] = []
    success_counts = {entity["type"].value: 0 for entity in config["entities"]}
    error_counts = {entity["type"].value: 0 for entity in config["entities"]}
    aborted_early = False
    
    # Process each entity type in sequence
    for entity_config in config["entities"]:
        if aborted_early:
            break
            
        entity_type = entity_config["type"]
        schema_class = ENTITY_CREATE_SCHEMAS.get(entity_type)
        handler = ENTITY_CREATE_HANDLERS.get(entity_type)
        
        if not schema_class or not handler:
            raise ValueError(f"Missing handler or schema for {entity_type}")
        
        # Process all rows for this entity type
        for idx, row in df.iterrows():
            if aborted_early:
                break
                
            row_number = idx + 2
            row_data = clean_dataframe_row(row, original_columns=original_columns)
            raw_row = {col: row[col] for col in row.index if pd.notna(row[col])}
            
            entity_result: Dict[str, Any] = {
                "row": row_number,
                "entity_type": entity_type.value,
                "status": "pending",
                "data": None,
                "error": None,
            }
            
            try:
                entity_data = _extract_entity_data_from_row(row_data, raw_row, entity_config, entity_type)
                
                # Check if all required fields are present
                required_fields = set(schema_class.model_fields.keys())
                present_fields = {k for k, v in entity_data.items() if v}
                missing_fields = required_fields - present_fields
                
                if missing_fields:
                    entity_result["status"] = "skipped"
                    entity_result["error"] = f"Missing required fields: {', '.join(sorted(missing_fields))}"
                    results.append(entity_result)
                    continue
                
                # Check for duplicates (for specific entity types)
                entity_type_map = {
                    ListingType.wings: "wing",
                    ListingType.floors: "floor",
                    ListingType.datacenters: "datacenter",
                    ListingType.applications: "application",
                }
                if entity_type in entity_type_map:
                    duplicate_error = check_row_uniqueness_for_bulk(entity_type_map[entity_type], entity_data, db)
                    if duplicate_error:
                        raise ValueError(f"Duplicate data: {duplicate_error}")
                
                try:
                    validated_data = schema_class(**entity_data)
                except Exception as exc:
                    raise ValueError(f"{entity_type.value} validation error: {exc}")
                
                result = handler(db, validated_data.model_dump())
                object_id = result.get("id")
                
                if object_id and audit_context:
                    entity_context = {**audit_context, "entity": entity_type.value, "row": row_number}
                    log_create(
                        db=db,
                        user=current_user,
                        entity_type=entity_type.value,
                        object_id=object_id,
                        entity_data=result,
                        context=entity_context,
                    )
                
                entity_result["status"] = "success"
                entity_result["data"] = result
                success_counts[entity_type.value] += 1
                
            except (IntegrityError, Exception) as exc:
                aborted, _ = _process_row_error(exc, entity_result, db, skip_errors, 0)
                error_counts[entity_type.value] += 1
                if aborted:
                    aborted_early = True
                    results.append(entity_result)
                    break
            
            results.append(entity_result)
    
    if aborted_early:
        db.rollback()
    elif sum(success_counts.values()) > 0:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"Failed to commit changes: {exc}") from exc
    
    entity_names = ", ".join([e["type"].value for e in config["entities"]])
    return {
        "entity": f"{config_key} ({entity_names})",
        "total_rows": len(df),
        "processed": len(results),
        "success": success_counts,
        "errors": error_counts,
        "aborted": aborted_early,
        "skip_errors": skip_errors,
    }, results


def _process_bulk_upload_job(
    job_id: str,
    file_bytes: bytes,
    skip_errors: bool,
    current_user_id: int,
    current_user_email: Optional[str],
    entity_type: BulkUploadEntityType,
) -> None:
    """Unified background task entry point for all entity types."""
    db: Session = SessionLocal()
    summary: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = []
    failure_reason: Optional[str] = None

    try:
        user = db.get(User, current_user_id)
        if not user:
            app_logger.warning(
                "Bulk upload user not found; proceeding without audit attribution",
                extra={"job_id": job_id, "user_id": current_user_id},
            )
        
        router_name = f"dcim.bulk_upload.{entity_type.value}"
        audit_context = build_audit_context(
            router=router_name,
            action="create",
            entity=entity_type.value if entity_type in [BulkUploadEntityType.devices, BulkUploadEntityType.racks] else None,
            extra={"job_id": job_id},
        )
        
        # Process based on entity type
        if entity_type == BulkUploadEntityType.devices:
            summary, results = _process_single_entity_rows(
                db=db, file_bytes=file_bytes, skip_errors=skip_errors,
                current_user=user, audit_context=audit_context, entity=ListingType.devices
            )
            if summary and summary.get("success"):
                invalidate_listing_cache_for_entity(ListingType.devices)
                invalidate_location_summary_cache()
        elif entity_type == BulkUploadEntityType.racks:
            summary, results = _process_single_entity_rows(
                db=db, file_bytes=file_bytes, skip_errors=skip_errors,
                current_user=user, audit_context=audit_context, entity=ListingType.racks
            )
            if summary and summary.get("success"):
                invalidate_listing_cache_for_entity(ListingType.racks)
                invalidate_location_summary_cache()
        elif entity_type == BulkUploadEntityType.entity_wfd:
            summary, results = _process_multi_entity_rows(
                db=db, file_bytes=file_bytes, skip_errors=skip_errors,
                current_user=user, audit_context=audit_context, config_key="entity_wfd"
            )
            success_data = summary.get("success", {}) if summary else {}
            if isinstance(success_data, dict):
                for listing_type in [ListingType.wings, ListingType.floors, ListingType.datacenters]:
                    if success_data.get(listing_type.value):
                        invalidate_listing_cache_for_entity(listing_type)
                if any(success_data.values()):
                    invalidate_location_summary_cache()
        elif entity_type == BulkUploadEntityType.entity_asset_details:
            summary, results = _process_multi_entity_rows(
                db=db, file_bytes=file_bytes, skip_errors=skip_errors,
                current_user=user, audit_context=audit_context, config_key="entity_asset_details"
            )
            success_data = summary.get("success", {}) if summary else {}
            if isinstance(success_data, dict):
                for listing_type in [ListingType.asset_owner, ListingType.applications]:
                    if success_data.get(listing_type.value):
                        invalidate_listing_cache_for_entity(listing_type)
        elif entity_type == BulkUploadEntityType.entity_devicetypes:
            summary, results = _process_multi_entity_rows(
                db=db, file_bytes=file_bytes, skip_errors=skip_errors,
                current_user=user, audit_context=audit_context, config_key="entity_devicetypes"
            )
            success_data = summary.get("success", {}) if summary else {}
            if isinstance(success_data, dict):
                for listing_type in [ListingType.makes, ListingType.device_types, ListingType.models]:
                    if success_data.get(listing_type.value):
                        invalidate_listing_cache_for_entity(listing_type)
        
        app_logger.info(
            f"Bulk {entity_type.value} upload job completed",
            extra={
                "job_id": job_id,
                "success": summary["success"] if summary else 0,
                "errors": summary["errors"] if summary else 0,
            },
        )
    except Exception as exc:
        failure_reason = str(exc)
        app_logger.exception(
            f"Bulk {entity_type.value} upload job failed",
            extra={"job_id": job_id},
        )
    finally:
        try:
            send_bulk_upload_report(
                job_id=job_id,
                summary=summary,
                results=results,
                recipients=[current_user_email],
                failure_reason=failure_reason,
            )
        except Exception:
            app_logger.exception(
                "Failed to send bulk upload report email",
                extra={"job_id": job_id},
            )
        db.close()


@router.post(
    "/bulk-upload",
    response_model=Dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk upload entities via CSV file based on entity type",
)
async def bulk_upload_entities(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(
        ...,
        description="CSV file containing entity data. First row must be headers.",
    ),
    entity_type: BulkUploadEntityType = Query(
        default=BulkUploadEntityType.devices,
        description="Entity type to upload: devices, racks, entity_wfd, entity_asset_details, entity_devicetypes",
    ),
    skip_errors: bool = Query(
        default=False,
        description="If true, continue processing remaining rows on error. If false, stop on first error.",
    ),
    access_level: AccessLevel = Depends(require_editor_or_admin),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk upload entities from a CSV file based on selected entity type.
    
    Supported entity types:
    
    1. **devices** - Single device entities
    2. **racks** - Single rack entities
    3. **entity_wfd** - Wings, Floors, Datacenters (hierarchical)
    4. **entity_asset_details** - Asset Owners, Applications Mapped
    5. **entity_devicetypes** - Makes, Device Types, Models
    
    The API acknowledges receipt immediately (202 Accepted) and performs CSV processing
    in a background task before emailing a detailed report.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file (.csv extension)",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty.",
        )

    job_id = str(uuid.uuid4())
    
    entity_descriptions = {
        BulkUploadEntityType.devices: "devices",
        BulkUploadEntityType.racks: "racks",
        BulkUploadEntityType.entity_wfd: "entity_wfd (wings, floors, datacenters)",
        BulkUploadEntityType.entity_asset_details: "entity_asset_details (asset_owner, applications)",
        BulkUploadEntityType.entity_devicetypes: "entity_devicetypes (makes, device_types, models)",
    }

    background_tasks.add_task(
        _process_bulk_upload_job,
        job_id=job_id,
        file_bytes=file_bytes,
        skip_errors=skip_errors,
        current_user_id=current_user.id,
        current_user_email=current_user.email,
        entity_type=entity_type,
    )

    return {
        "entity": entity_descriptions[entity_type],
        "job_id": job_id,
        "message": (
            "CSV received. Processing will continue in the background. "
            "An email report will be sent after completion."
        ),
        "report_recipient": current_user.email,
    }

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
from typing import Any, Dict, List, Optional, Tuple

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


def check_row_uniqueness_for_bulk(
    entity_type: str, data: Dict[str, Any], db: Session
) -> Optional[str]:
    """
    Check if a complete row already exists in the database for bulk upload.
    Returns an error message if duplicate found, None otherwise.
    
    Args:
        entity_type: The entity type being created (e.g., "wing", "floor", "datacenter", "application")
        data: The data dictionary containing all field values
        db: Database session
        
    Returns:
        Error message string if duplicate found, None otherwise
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
            # Wing: unique by (name, location_id, building_id)
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
            # Floor: unique by (name, location_id, building_id, wing_id)
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
            # Datacenter: unique by (name, location_id, building_id, wing_id, floor_id)
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
            # ApplicationMapped: unique by (name, asset_owner_id)
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
        # If helper functions fail (e.g., entity not found), let the handler deal with it
        # We only check for duplicates here, not for missing references
        pass
    
    return None


def normalize_column_name(col_name: str) -> str:
    """
    Normalize CSV column names for consistent mapping.
    Converts to lowercase, strips whitespace, and normalizes separators.
    """
    # Convert to lowercase and strip
    normalized = col_name.strip().lower()
    # Replace multiple spaces/underscores/slashes with single space
    normalized = re.sub(r'[\s_/]+', ' ', normalized)
    # Strip again after normalization
    return normalized.strip()


def clean_dataframe_row(row: pd.Series, apply_mapping: bool = True, original_columns: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Convert a pandas DataFrame row to a clean dictionary.
    Handles NaN values, type conversions, empty strings, and CSV column mapping.
    Maps CSV column names to schema field names when apply_mapping is True.
    """
    result = {}
    for col, value in row.items():
        # Skip NaN/None values
        if pd.isna(value):
            continue
        
        # Map CSV column name to schema field name if apply_mapping is True
        # Column names are already normalized to lowercase in _load_dataframe_from_bytes
        if apply_mapping:
            # First, check if the original column name (before normalization) is already a valid schema field name
            # (e.g., "devicetype_name", "rack_name", "make_name", "model_name", "application_name")
            # This handles CSVs that use exact schema field names - preserve them directly
            if original_columns and col in original_columns:
                original_col = original_columns[col]
                # If original column has underscores (schema field pattern like "devicetype_name"),
                # always use the original column name directly to preserve exact schema field names
                # This prevents incorrect mapping (e.g., "devicetype name" -> "name")
                if '_' in original_col:
                    schema_field = original_col
                else:
                    # Original column doesn't have underscores, use mapping if available
                    schema_field = CSV_COLUMN_MAPPING.get(col, col)
            elif col in CSV_COLUMN_MAPPING:
                schema_field = CSV_COLUMN_MAPPING[col]
            else:
                schema_field = col
        else:
            schema_field = col
        
        # Convert to appropriate type
        if schema_field in INT_FIELDS:
            try:
                result[schema_field] = int(value)
            except (ValueError, TypeError):
                continue
        elif schema_field in DATE_FIELDS:
            # Convert date to string format for Pydantic
            if isinstance(value, pd.Timestamp):
                result[schema_field] = value.strftime("%Y-%m-%d")
            elif isinstance(value, str) and value.strip():
                # Try to parse and normalize date format
                date_str = value.strip()
                # Handle common date formats
                try:
                    # Try parsing with pandas to normalize format
                    parsed_date = pd.to_datetime(date_str, errors='raise')
                    result[schema_field] = parsed_date.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    # If parsing fails, use as-is (Pydantic will validate)
                    result[schema_field] = date_str
        else:
            # String fields - strip whitespace
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

    # Store original column names before normalization for exact field name matching
    original_columns = {normalize_column_name(col): col for col in df.columns}
    
    # Normalize column names for consistent mapping
    df.columns = [normalize_column_name(col) for col in df.columns]
    df = df.dropna(how="all")

    if df.empty:
        raise ValueError("CSV file has no valid data rows")

    # Store original columns as dataframe attribute for use in clean_dataframe_row
    df.attrs['original_columns'] = original_columns

    return df


# =============================================================================
# Device Bulk Upload Handler
# =============================================================================

def _process_device_rows(
    db: Session,
    file_bytes: bytes,
    skip_errors: bool,
    current_user: Optional[User],
    audit_context: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Process CSV rows and insert device entities."""
    entity = ListingType.devices

    schema_class = ENTITY_CREATE_SCHEMAS.get(entity)
    if not schema_class:
        raise ValueError(f"Unsupported entity type: {entity}")

    handler = ENTITY_CREATE_HANDLERS.get(entity)
    if not handler:
        raise ValueError(f"No handler found for entity type: {entity}")

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
            if object_id:
                row_context = None
                if audit_context:
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

        except IntegrityError as exc:
            db.rollback()
            pending_commit = 0
            error_count += 1
            row_result["status"] = "error"
            error_msg = str(exc.orig)
            # Check if it's a duplicate/unique constraint violation
            if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                row_result["error"] = f"Duplicate data insertion: Device already exists"
            else:
                row_result["error"] = f"Database integrity error: {error_msg}"
            if not skip_errors:
                aborted_early = True
                results.append(row_result)
                break
        except Exception as exc:
            db.rollback()
            pending_commit = 0
            error_count += 1
            row_result["status"] = "error"
            error_msg = str(exc)
            # Check if it's a duplicate error message
            if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                row_result["error"] = error_msg
            else:
                row_result["error"] = error_msg
            if not skip_errors:
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

    summary = {
        "entity": entity.value,
        "total_rows": len(df),
        "processed": len(results),
        "success": success_count,
        "errors": error_count,
        "aborted": aborted_early,
        "skip_errors": skip_errors,
    }

    return summary, results


def _process_device_bulk_upload_job(
    job_id: str,
    file_bytes: bytes,
    skip_errors: bool,
    current_user_id: int,
    current_user_email: Optional[str],
) -> None:
    """Background task entry point for processing and emailing results."""
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
        audit_context = build_audit_context(
            router="dcim.bulk_upload.devices",
            action="create",
            entity=ListingType.devices.value,
            extra={"job_id": job_id},
        )
        summary, results = _process_device_rows(
            db=db,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user=user,
            audit_context=audit_context,
        )
        if summary and summary.get("success"):
            invalidate_listing_cache_for_entity(ListingType.devices)
            invalidate_location_summary_cache()
        app_logger.info(
            "Bulk device upload job completed",
            extra={
                "job_id": job_id,
                "success": summary["success"] if summary else 0,
                "errors": summary["errors"] if summary else 0,
            },
        )
    except Exception as exc:
        failure_reason = str(exc)
        app_logger.exception(
            "Bulk device upload job failed",
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


# =============================================================================
# Rack Bulk Upload Handler
# =============================================================================

def _process_rack_rows(
    db: Session,
    file_bytes: bytes,
    skip_errors: bool,
    current_user: Optional[User],
    audit_context: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Process CSV rows and insert rack entities."""
    entity = ListingType.racks

    schema_class = ENTITY_CREATE_SCHEMAS.get(entity)
    if not schema_class:
        raise ValueError(f"Unsupported entity type: {entity}")

    handler = ENTITY_CREATE_HANDLERS.get(entity)
    if not handler:
        raise ValueError(f"No handler found for entity type: {entity}")

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

            object_id = result.get("id")
            if object_id:
                row_context = None
                if audit_context:
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

        except IntegrityError as exc:
            db.rollback()
            pending_commit = 0
            error_count += 1
            row_result["status"] = "error"
            error_msg = str(exc.orig)
            # Check if it's a duplicate/unique constraint violation
            if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                row_result["error"] = f"Duplicate data insertion: Device already exists"
            else:
                row_result["error"] = f"Database integrity error: {error_msg}"
            if not skip_errors:
                aborted_early = True
                results.append(row_result)
                break
        except Exception as exc:
            db.rollback()
            pending_commit = 0
            error_count += 1
            row_result["status"] = "error"
            error_msg = str(exc)
            # Check if it's a duplicate error message
            if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                row_result["error"] = error_msg
            else:
                row_result["error"] = error_msg
            if not skip_errors:
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

    summary = {
        "entity": entity.value,
        "total_rows": len(df),
        "processed": len(results),
        "success": success_count,
        "errors": error_count,
        "aborted": aborted_early,
        "skip_errors": skip_errors,
    }

    return summary, results


def _process_rack_bulk_upload_job(
    job_id: str,
    file_bytes: bytes,
    skip_errors: bool,
    current_user_id: int,
    current_user_email: Optional[str],
) -> None:
    """Background task entry point for processing rack uploads and emailing results."""
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
        audit_context = build_audit_context(
            router="dcim.bulk_upload.racks",
            action="create",
            entity=ListingType.racks.value,
            extra={"job_id": job_id},
        )
        summary, results = _process_rack_rows(
            db=db,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user=user,
            audit_context=audit_context,
        )
        if summary and summary.get("success"):
            invalidate_listing_cache_for_entity(ListingType.racks)
            invalidate_location_summary_cache()
        app_logger.info(
            "Bulk rack upload job completed",
            extra={
                "job_id": job_id,
                "success": summary["success"] if summary else 0,
                "errors": summary["errors"] if summary else 0,
            },
        )
    except Exception as exc:
        failure_reason = str(exc)
        app_logger.exception(
            "Bulk rack upload job failed",
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


# =============================================================================
# Hierarchy (Wings, Floors, Datacenters) Bulk Upload Handler
# =============================================================================

def _process_hierarchy_rows(
    db: Session,
    file_bytes: bytes,
    skip_errors: bool,
    current_user: Optional[User],
    audit_context: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Process CSV rows and insert wing, floor, and datacenter entities in hierarchical order.
    Processes wings first, then floors, then datacenters.
    Each row should contain data for all three entity types.
    """
    df = _load_dataframe_from_bytes(file_bytes)
    
    results: List[Dict[str, Any]] = []
    success_counts = {"wings": 0, "floors": 0, "datacenters": 0}
    error_counts = {"wings": 0, "floors": 0, "datacenters": 0}
    aborted_early = False
    
    # Get handlers and schemas
    wing_handler = ENTITY_CREATE_HANDLERS.get(ListingType.wings)
    floor_handler = ENTITY_CREATE_HANDLERS.get(ListingType.floors)
    datacenter_handler = ENTITY_CREATE_HANDLERS.get(ListingType.datacenters)
    
    wing_schema = ENTITY_CREATE_SCHEMAS.get(ListingType.wings)
    floor_schema = ENTITY_CREATE_SCHEMAS.get(ListingType.floors)
    datacenter_schema = ENTITY_CREATE_SCHEMAS.get(ListingType.datacenters)
    
    if not all([wing_handler, floor_handler, datacenter_handler, wing_schema, floor_schema, datacenter_schema]):
        raise ValueError("Missing handlers or schemas for hierarchy entities")
    
    # Process all rows: wings first, then floors, then datacenters
    original_columns = df.attrs.get('original_columns', {})
    for idx, row in df.iterrows():
        row_number = idx + 2
        row_data = clean_dataframe_row(row, original_columns=original_columns)
        
        # Process wing from this row
        wing_result: Dict[str, Any] = {
            "row": row_number,
            "entity_type": "wing",
            "status": "pending",
            "data": None,
            "error": None,
        }
        
        try:
            wing_data = {
                "name": row_data.get("wing_name") or row_data.get("name"),
                "location_name": row_data.get("location_name") or row_data.get("location"),
                "building_name": row_data.get("building_name") or row_data.get("building"),
                "description": row_data.get("description", ""),
            }
            
            # Schema requires: name, location_name, building_name, and description (all with min_length=1)
            if all([wing_data.get("name"), wing_data.get("location_name"), wing_data.get("building_name"), wing_data.get("description")]):
                # Check for duplicate before insertion
                duplicate_error = check_row_uniqueness_for_bulk("wing", wing_data, db)
                if duplicate_error:
                    raise ValueError(f"Duplicate data: {duplicate_error}")
                
                try:
                    validated_data = wing_schema(**wing_data)
                except Exception as exc:
                    raise ValueError(f"Wing validation error: {exc}")
                
                result = wing_handler(db, validated_data.model_dump())
                
                object_id = result.get("id")
                if object_id:
                    wing_context = None
                    if audit_context:
                        wing_context = {
                            **audit_context,
                            "entity": ListingType.wings.value,
                            "row": row_number,
                        }
                    log_create(
                        db=db,
                        user=current_user,
                        entity_type="wings",
                        object_id=object_id,
                        entity_data=result,
                        context=wing_context,
                    )
                
                wing_result["status"] = "success"
                wing_result["data"] = result
                success_counts["wings"] += 1
            else:
                wing_result["status"] = "skipped"
                missing_fields = []
                if not wing_data.get("name"):
                    missing_fields.append("wing_name (or 'name' column)")
                if not wing_data.get("location_name"):
                    missing_fields.append("location_name")
                if not wing_data.get("building_name"):
                    missing_fields.append("building_name")
                if not wing_data.get("description"):
                    missing_fields.append("description")
                wing_result["error"] = f"Missing required fields for wing: {', '.join(missing_fields)}"
        except IntegrityError as exc:
            db.rollback()
            error_counts["wings"] += 1
            wing_result["status"] = "error"
            error_msg = str(exc.orig)
            # Check if it's a duplicate/unique constraint violation
            if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                wing_result["error"] = f"Duplicate data insertion: Wing already exists"
            else:
                wing_result["error"] = f"Database integrity error: {error_msg}"
            if not skip_errors:
                aborted_early = True
                results.append(wing_result)
                break
        except Exception as exc:
            db.rollback()
            error_counts["wings"] += 1
            wing_result["status"] = "error"
            error_msg = str(exc)
            # Preserve duplicate error messages from check_row_uniqueness_for_bulk
            if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                wing_result["error"] = error_msg
            else:
                wing_result["error"] = error_msg
            if not skip_errors:
                aborted_early = True
                results.append(wing_result)
                break
        
        results.append(wing_result)
        if aborted_early:
            break
    
    if not aborted_early:
        # Process floors (depend on wings)
        for idx, row in df.iterrows():
            row_number = idx + 2
            row_data = clean_dataframe_row(row)
            
            floor_result: Dict[str, Any] = {
                "row": row_number,
                "entity_type": "floor",
                "status": "pending",
                "data": None,
                "error": None,
            }
            
            try:
                floor_data = {
                    "name": row_data.get("floor_name") or row_data.get("name"),
                    "location_name": row_data.get("location_name") or row_data.get("location"),
                    "building_name": row_data.get("building_name") or row_data.get("building"),
                    "wing_name": row_data.get("wing_name") or row_data.get("wing"),
                    "description": row_data.get("description", ""),
                }
                
                # Schema requires: name, location_name, building_name, wing_name, and description (all with min_length=1)
                if all([floor_data.get("name"), floor_data.get("location_name"), 
                       floor_data.get("building_name"), floor_data.get("wing_name"), floor_data.get("description")]):
                    # Check for duplicate before insertion
                    duplicate_error = check_row_uniqueness_for_bulk("floor", floor_data, db)
                    if duplicate_error:
                        raise ValueError(f"Duplicate data: {duplicate_error}")
                    
                    try:
                        validated_data = floor_schema(**floor_data)
                    except Exception as exc:
                        raise ValueError(f"Floor validation error: {exc}")
                    
                    result = floor_handler(db, validated_data.model_dump())
                    
                    object_id = result.get("id")
                    if object_id:
                        floor_context = None
                        if audit_context:
                            floor_context = {
                                **audit_context,
                                "entity": ListingType.floors.value,
                                "row": row_number,
                            }
                        log_create(
                            db=db,
                            user=current_user,
                            entity_type="floors",
                            object_id=object_id,
                            entity_data=result,
                            context=floor_context,
                        )
                    
                    floor_result["status"] = "success"
                    floor_result["data"] = result
                    success_counts["floors"] += 1
                else:
                    floor_result["status"] = "skipped"
                    missing_fields = []
                    if not floor_data.get("name"):
                        missing_fields.append("floor_name (or 'name' column)")
                    if not floor_data.get("location_name"):
                        missing_fields.append("location_name")
                    if not floor_data.get("building_name"):
                        missing_fields.append("building_name")
                    if not floor_data.get("wing_name"):
                        missing_fields.append("wing_name")
                    if not floor_data.get("description"):
                        missing_fields.append("description")
                    floor_result["error"] = f"Missing required fields for floor: {', '.join(missing_fields)}"
            except IntegrityError as exc:
                db.rollback()
                error_counts["floors"] += 1
                floor_result["status"] = "error"
                error_msg = str(exc.orig)
                # Check if it's a duplicate/unique constraint violation
                if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                    floor_result["error"] = f"Duplicate data insertion: Floor already exists"
                else:
                    floor_result["error"] = f"Database integrity error: {error_msg}"
                if not skip_errors:
                    aborted_early = True
                    results.append(floor_result)
                    break
            except Exception as exc:
                db.rollback()
                error_counts["floors"] += 1
                floor_result["status"] = "error"
                error_msg = str(exc)
                # Preserve duplicate error messages from check_row_uniqueness_for_bulk
                if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                    floor_result["error"] = error_msg
                else:
                    floor_result["error"] = error_msg
                if not skip_errors:
                    aborted_early = True
                    results.append(floor_result)
                    break
            
            results.append(floor_result)
            if aborted_early:
                break
        
        if not aborted_early:
            # Process datacenters (depend on floors)
            for idx, row in df.iterrows():
                row_number = idx + 2
                row_data = clean_dataframe_row(row)
                
                datacenter_result: Dict[str, Any] = {
                    "row": row_number,
                    "entity_type": "datacenter",
                    "status": "pending",
                    "data": None,
                    "error": None,
                }
                
                try:
                    datacenter_data = {
                        "name": row_data.get("datacenter_name") or row_data.get("name"),
                        "location_name": row_data.get("location_name") or row_data.get("location"),
                        "building_name": row_data.get("building_name") or row_data.get("building"),
                        "wing_name": row_data.get("wing_name") or row_data.get("wing"),
                        "floor_name": row_data.get("floor_name") or row_data.get("floor"),
                        "description": row_data.get("description", ""),
                    }
                    
                    # Schema requires: name, location_name, building_name, wing_name, floor_name, and description (all with min_length=1)
                    if all([datacenter_data.get("name"), datacenter_data.get("location_name"),
                           datacenter_data.get("building_name"), datacenter_data.get("wing_name"),
                           datacenter_data.get("floor_name"), datacenter_data.get("description")]):
                        # Check for duplicate before insertion
                        duplicate_error = check_row_uniqueness_for_bulk("datacenter", datacenter_data, db)
                        if duplicate_error:
                            raise ValueError(f"Duplicate data: {duplicate_error}")
                        
                        try:
                            validated_data = datacenter_schema(**datacenter_data)
                        except Exception as exc:
                            raise ValueError(f"Datacenter validation error: {exc}")
                        
                        result = datacenter_handler(db, validated_data.model_dump())
                        
                        object_id = result.get("id")
                        if object_id:
                            datacenter_context = None
                            if audit_context:
                                datacenter_context = {
                                    **audit_context,
                                    "entity": ListingType.datacenters.value,
                                    "row": row_number,
                                }
                            log_create(
                                db=db,
                                user=current_user,
                                entity_type="datacenters",
                                object_id=object_id,
                                entity_data=result,
                                context=datacenter_context,
                            )
                        
                        datacenter_result["status"] = "success"
                        datacenter_result["data"] = result
                        success_counts["datacenters"] += 1
                    else:
                        datacenter_result["status"] = "skipped"
                        missing_fields = []
                        if not datacenter_data.get("name"):
                            missing_fields.append("datacenter_name (or 'name' column)")
                        if not datacenter_data.get("location_name"):
                            missing_fields.append("location_name")
                        if not datacenter_data.get("building_name"):
                            missing_fields.append("building_name")
                        if not datacenter_data.get("wing_name"):
                            missing_fields.append("wing_name")
                        if not datacenter_data.get("floor_name"):
                            missing_fields.append("floor_name")
                        if not datacenter_data.get("description"):
                            missing_fields.append("description")
                        datacenter_result["error"] = f"Missing required fields for datacenter: {', '.join(missing_fields)}"
                except IntegrityError as exc:
                    db.rollback()
                    error_counts["datacenters"] += 1
                    datacenter_result["status"] = "error"
                    error_msg = str(exc.orig)
                    # Check if it's a duplicate/unique constraint violation
                    if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                        datacenter_result["error"] = f"Duplicate data insertion: Datacenter already exists"
                    else:
                        datacenter_result["error"] = f"Database integrity error: {error_msg}"
                    if not skip_errors:
                        aborted_early = True
                        results.append(datacenter_result)
                        break
                except Exception as exc:
                    db.rollback()
                    error_counts["datacenters"] += 1
                    datacenter_result["status"] = "error"
                    error_msg = str(exc)
                    # Preserve duplicate error messages from check_row_uniqueness_for_bulk
                    if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                        datacenter_result["error"] = error_msg
                    else:
                        datacenter_result["error"] = error_msg
                    if not skip_errors:
                        aborted_early = True
                        results.append(datacenter_result)
                        break
                
                results.append(datacenter_result)
                if aborted_early:
                    break
    
    if aborted_early:
        db.rollback()
    elif sum(success_counts.values()) > 0:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"Failed to commit changes: {exc}") from exc
    
    summary = {
        "entity": "entity_wfd (wings, floors, datacenters)",
        "total_rows": len(df),
        "processed": len(results),
        "success": {
            "wings": success_counts["wings"],
            "floors": success_counts["floors"],
            "datacenters": success_counts["datacenters"],
        },
        "errors": {
            "wings": error_counts["wings"],
            "floors": error_counts["floors"],
            "datacenters": error_counts["datacenters"],
        },
        "aborted": aborted_early,
        "skip_errors": skip_errors,
    }
    
    return summary, results


def _process_hierarchy_bulk_upload_job(
    job_id: str,
    file_bytes: bytes,
    skip_errors: bool,
    current_user_id: int,
    current_user_email: Optional[str],
) -> None:
    """Background task entry point for processing hierarchy entities and emailing results."""
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
        audit_context = build_audit_context(
            router="dcim.bulk_upload.hierarchy",
            action="create",
            extra={"job_id": job_id},
        )
        summary, results = _process_hierarchy_rows(
            db=db,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user=user,
            audit_context=audit_context,
        )
        # Invalidate caches if any entities were created
        success_data = summary.get("success", {}) if summary else {}
        if isinstance(success_data, dict):
            if success_data.get("wings"):
                invalidate_listing_cache_for_entity(ListingType.wings)
            if success_data.get("floors"):
                invalidate_listing_cache_for_entity(ListingType.floors)
            if success_data.get("datacenters"):
                invalidate_listing_cache_for_entity(ListingType.datacenters)
            if any(success_data.values()):
                invalidate_location_summary_cache()
        app_logger.info(
            "Bulk hierarchy upload job completed",
            extra={
                "job_id": job_id,
                "success": summary["success"] if summary else {},
                "errors": summary["errors"] if summary else {},
            },
        )
    except Exception as exc:
        failure_reason = str(exc)
        app_logger.exception(
            "Bulk hierarchy upload job failed",
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


# =============================================================================
# Asset Details (Asset Owner, Applications Mapped) Bulk Upload Handler
# =============================================================================

def _process_asset_details_rows(
    db: Session,
    file_bytes: bytes,
    skip_errors: bool,
    current_user: Optional[User],
    audit_context: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Process CSV rows and insert asset_owner and applications_mapped entities.
    Processes asset_owners first, then applications (which depend on asset_owners).
    Each row should contain data for both entity types.
    """
    df = _load_dataframe_from_bytes(file_bytes)
    
    results: List[Dict[str, Any]] = []
    success_counts = {"asset_owners": 0, "applications": 0}
    error_counts = {"asset_owners": 0, "applications": 0}
    aborted_early = False
    
    # Get handlers and schemas
    asset_owner_handler = ENTITY_CREATE_HANDLERS.get(ListingType.asset_owner)
    application_handler = ENTITY_CREATE_HANDLERS.get(ListingType.applications)
    
    asset_owner_schema = ENTITY_CREATE_SCHEMAS.get(ListingType.asset_owner)
    application_schema = ENTITY_CREATE_SCHEMAS.get(ListingType.applications)
    
    if not all([asset_owner_handler, application_handler, asset_owner_schema, application_schema]):
        raise ValueError("Missing handlers or schemas for asset detail entities")
    
    # Process asset owners first
    original_columns = df.attrs.get('original_columns', {})
    for idx, row in df.iterrows():
        row_number = idx + 2
        row_data = clean_dataframe_row(row, original_columns=original_columns)
        
        asset_owner_result: Dict[str, Any] = {
            "row": row_number,
            "entity_type": "asset_owner",
            "status": "pending",
            "data": None,
            "error": None,
        }
        
        try:
            asset_owner_data = {
                "name": row_data.get("asset_owner_name") or row_data.get("name"),
                "location_name": row_data.get("location_name") or row_data.get("location"),
                "description": row_data.get("asset_owner_description") or row_data.get("description", ""),
            }
            
            # Schema requires: name, location_name, and description (all with min_length=1)
            if all([asset_owner_data.get("name"), asset_owner_data.get("location_name"), asset_owner_data.get("description")]):
                try:
                    validated_data = asset_owner_schema(**asset_owner_data)
                except Exception as exc:
                    raise ValueError(f"Asset owner validation error: {exc}")
                
                result = asset_owner_handler(db, validated_data.model_dump())
                
                object_id = result.get("id")
                if object_id:
                    ao_context = None
                    if audit_context:
                        ao_context = {
                            **audit_context,
                            "entity": ListingType.asset_owner.value,
                            "row": row_number,
                        }
                    log_create(
                        db=db,
                        user=current_user,
                        entity_type="asset_owner",
                        object_id=object_id,
                        entity_data=result,
                        context=ao_context,
                    )
                
                asset_owner_result["status"] = "success"
                asset_owner_result["data"] = result
                success_counts["asset_owners"] += 1
            else:
                asset_owner_result["status"] = "skipped"
                missing_fields = []
                if not asset_owner_data.get("name"):
                    missing_fields.append("asset_owner_name (or 'name' column)")
                if not asset_owner_data.get("location_name"):
                    missing_fields.append("location_name")
                if not asset_owner_data.get("description"):
                    missing_fields.append("description (or 'asset_owner_description' column)")
                asset_owner_result["error"] = f"Missing required fields for asset owner: {', '.join(missing_fields)}"
        except IntegrityError as exc:
            db.rollback()
            error_counts["asset_owners"] += 1
            asset_owner_result["status"] = "error"
            error_msg = str(exc.orig)
            # Check if it's a duplicate/unique constraint violation
            if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                asset_owner_result["error"] = f"Duplicate data insertion: Asset owner already exists"
            else:
                asset_owner_result["error"] = f"Database integrity error: {error_msg}"
            if not skip_errors:
                aborted_early = True
                results.append(asset_owner_result)
                break
        except Exception as exc:
            db.rollback()
            error_counts["asset_owners"] += 1
            asset_owner_result["status"] = "error"
            error_msg = str(exc)
            # Preserve duplicate error messages
            if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                asset_owner_result["error"] = error_msg
            else:
                asset_owner_result["error"] = error_msg
            if not skip_errors:
                aborted_early = True
                results.append(asset_owner_result)
                break
        
        results.append(asset_owner_result)
        if aborted_early:
            break
    
    if not aborted_early:
        # Process applications (depend on asset owners)
        for idx, row in df.iterrows():
            row_number = idx + 2
            row_data = clean_dataframe_row(row)
            
            application_result: Dict[str, Any] = {
                "row": row_number,
                "entity_type": "application",
                "status": "pending",
                "data": None,
                "error": None,
            }
            
            try:
                # CSV column mapping:
                # - "application_name" CSV column → normalized to "application name" → maps to "name" in row_data
                # - "application" CSV column → maps to "application_name" in row_data
                # So we need to check "name" first (from "application_name" CSV), then "application_name" (from "application" CSV)
                application_name = row_data.get("name") or row_data.get("application_name")
                
                application_data = {
                    "name": application_name,
                    "asset_owner_name": row_data.get("asset_owner_name"),
                    "description": row_data.get("application_description") or row_data.get("description", ""),
                }
                
                # Schema requires: name, asset_owner_name, and description (all with min_length=1)
                if all([application_data.get("name"), application_data.get("asset_owner_name"), application_data.get("description")]):
                    # Check for duplicate before insertion
                    duplicate_error = check_row_uniqueness_for_bulk("application", application_data, db)
                    if duplicate_error:
                        raise ValueError(f"Duplicate data: {duplicate_error}")
                    
                    try:
                        validated_data = application_schema(**application_data)
                    except Exception as exc:
                        raise ValueError(f"Application validation error: {exc}")
                    
                    result = application_handler(db, validated_data.model_dump())
                    
                    object_id = result.get("id")
                    if object_id:
                        app_context = None
                        if audit_context:
                            app_context = {
                                **audit_context,
                                "entity": ListingType.applications.value,
                                "row": row_number,
                            }
                        log_create(
                            db=db,
                            user=current_user,
                            entity_type="applications",
                            object_id=object_id,
                            entity_data=result,
                            context=app_context,
                        )
                    
                    application_result["status"] = "success"
                    application_result["data"] = result
                    success_counts["applications"] += 1
                else:
                    application_result["status"] = "skipped"
                    missing_fields = []
                    if not application_data.get("name"):
                        missing_fields.append("application_name (or 'name' column)")
                    if not application_data.get("asset_owner_name"):
                        missing_fields.append("asset_owner_name")
                    if not application_data.get("description"):
                        missing_fields.append("description (or 'application_description' column)")
                    application_result["error"] = f"Missing required fields for application: {', '.join(missing_fields)}"
            except IntegrityError as exc:
                db.rollback()
                error_counts["applications"] += 1
                application_result["status"] = "error"
                error_msg = str(exc.orig)
                # Check if it's a duplicate/unique constraint violation
                if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                    application_result["error"] = f"Duplicate data insertion: Application already exists"
                else:
                    application_result["error"] = f"Database integrity error: {error_msg}"
                if not skip_errors:
                    aborted_early = True
                    results.append(application_result)
                    break
            except Exception as exc:
                db.rollback()
                error_counts["applications"] += 1
                application_result["status"] = "error"
                error_msg = str(exc)
                # Preserve duplicate error messages from check_row_uniqueness_for_bulk
                if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                    application_result["error"] = error_msg
                else:
                    application_result["error"] = error_msg
                if not skip_errors:
                    aborted_early = True
                    results.append(application_result)
                    break
            
            results.append(application_result)
            if aborted_early:
                break
    
    if aborted_early:
        db.rollback()
    elif sum(success_counts.values()) > 0:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"Failed to commit changes: {exc}") from exc
    
    summary = {
        "entity": "entity_asset_details (asset_owner, applications)",
        "total_rows": len(df),
        "processed": len(results),
        "success": {
            "asset_owners": success_counts["asset_owners"],
            "applications": success_counts["applications"],
        },
        "errors": {
            "asset_owners": error_counts["asset_owners"],
            "applications": error_counts["applications"],
        },
        "aborted": aborted_early,
        "skip_errors": skip_errors,
    }
    
    return summary, results


def _process_asset_details_bulk_upload_job(
    job_id: str,
    file_bytes: bytes,
    skip_errors: bool,
    current_user_id: int,
    current_user_email: Optional[str],
) -> None:
    """Background task entry point for processing asset detail entities and emailing results."""
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
        audit_context = build_audit_context(
            router="dcim.bulk_upload.asset_details",
            action="create",
            extra={"job_id": job_id},
        )
        summary, results = _process_asset_details_rows(
            db=db,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user=user,
            audit_context=audit_context,
        )
        # Invalidate caches if any entities were created
        success_data = summary.get("success", {}) if summary else {}
        if isinstance(success_data, dict):
            if success_data.get("asset_owners"):
                invalidate_listing_cache_for_entity(ListingType.asset_owner)
            if success_data.get("applications"):
                invalidate_listing_cache_for_entity(ListingType.applications)
        app_logger.info(
            "Bulk asset details upload job completed",
            extra={
                "job_id": job_id,
                "success": summary["success"] if summary else {},
                "errors": summary["errors"] if summary else {},
            },
        )
    except Exception as exc:
        failure_reason = str(exc)
        app_logger.exception(
            "Bulk asset details upload job failed",
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


# =============================================================================
# Device Types (Makes, Device Types, Models) Bulk Upload Handler
# =============================================================================

def _process_devicetypes_rows(
    db: Session,
    file_bytes: bytes,
    skip_errors: bool,
    current_user: Optional[User],
    audit_context: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Process CSV rows and insert make, device_type, and model entities.
    Processes in hierarchical order: makes first, then device_types, then models.
    Each row should contain data for all three entity types.
    """
    df = _load_dataframe_from_bytes(file_bytes)
    
    results: List[Dict[str, Any]] = []
    success_counts = {"makes": 0, "device_types": 0, "models": 0}
    error_counts = {"makes": 0, "device_types": 0, "models": 0}
    aborted_early = False
    
    # Get handlers and schemas
    make_handler = ENTITY_CREATE_HANDLERS.get(ListingType.makes)
    device_type_handler = ENTITY_CREATE_HANDLERS.get(ListingType.device_types)
    model_handler = ENTITY_CREATE_HANDLERS.get(ListingType.models)
    
    make_schema = ENTITY_CREATE_SCHEMAS.get(ListingType.makes)
    device_type_schema = ENTITY_CREATE_SCHEMAS.get(ListingType.device_types)
    model_schema = ENTITY_CREATE_SCHEMAS.get(ListingType.models)
    
    if not all([make_handler, device_type_handler, model_handler, make_schema, device_type_schema, model_schema]):
        raise ValueError("Missing handlers or schemas for device type entities")
    
    # Process makes first
    for idx, row in df.iterrows():
        row_number = idx + 2
        # Get raw values from original row before mapping (to avoid conflicts when multiple columns map to "name")
        raw_row = {col: row[col] for col in row.index if pd.notna(row[col])}
        row_data = clean_dataframe_row(row)
        
        make_result: Dict[str, Any] = {
            "row": row_number,
            "entity_type": "make",
            "status": "pending",
            "data": None,
            "error": None,
        }
        
        try:
            # Extract make_name directly from raw row (before mapping)
            # Check common column name variations
            make_name = None
            for col in raw_row.keys():
                col_lower = normalize_column_name(col)
                if col_lower in ["make name", "make_name", "manufacturer"]:
                    make_name = str(raw_row[col]).strip()
                    break
            
            # Fallback to mapped row_data
            if not make_name:
                make_name = row_data.get("name") or row_data.get("make_name") or row_data.get("manufacturer")
            
            make_data = {
                "name": make_name,
                "description": row_data.get("make_description") or row_data.get("description", ""),
            }
            
            # Schema requires: name and description (both with min_length=1)
            if all([make_data.get("name"), make_data.get("description")]):
                try:
                    validated_data = make_schema(**make_data)
                except Exception as exc:
                    raise ValueError(f"Make validation error: {exc}")
                
                result = make_handler(db, validated_data.model_dump())
                
                object_id = result.get("id")
                if object_id:
                    make_context = None
                    if audit_context:
                        make_context = {
                            **audit_context,
                            "entity": ListingType.makes.value,
                            "row": row_number,
                        }
                    log_create(
                        db=db,
                        user=current_user,
                        entity_type="makes",
                        object_id=object_id,
                        entity_data=result,
                        context=make_context,
                    )
                
                make_result["status"] = "success"
                make_result["data"] = result
                success_counts["makes"] += 1
            else:
                make_result["status"] = "skipped"
                missing_fields = []
                if not make_data.get("name"):
                    missing_fields.append("make_name (or 'name' column)")
                if not make_data.get("description"):
                    missing_fields.append("description (or 'make_description' column)")
                make_result["error"] = f"Missing required fields for make: {', '.join(missing_fields)}"
        except IntegrityError as exc:
            db.rollback()
            error_counts["makes"] += 1
            make_result["status"] = "error"
            error_msg = str(exc.orig)
            # Check if it's a duplicate/unique constraint violation
            if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                make_result["error"] = f"Duplicate data insertion: Make already exists"
            else:
                make_result["error"] = f"Database integrity error: {error_msg}"
            if not skip_errors:
                aborted_early = True
                results.append(make_result)
                break
        except Exception as exc:
            db.rollback()
            error_counts["makes"] += 1
            make_result["status"] = "error"
            error_msg = str(exc)
            # Preserve duplicate error messages
            if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                make_result["error"] = error_msg
            else:
                make_result["error"] = error_msg
            if not skip_errors:
                aborted_early = True
                results.append(make_result)
                break
        
        results.append(make_result)
        if aborted_early:
            break
    
    if not aborted_early:
        # Process device types (depend on makes)
        for idx, row in df.iterrows():
            row_number = idx + 2
            # Get raw values from original row before mapping
            raw_row = {col: row[col] for col in row.index if pd.notna(row[col])}
            row_data = clean_dataframe_row(row)
            
            device_type_result: Dict[str, Any] = {
                "row": row_number,
                "entity_type": "device_type",
                "status": "pending",
                "data": None,
                "error": None,
            }
            
            try:
                # Extract devicetype_name and make_name directly from raw row (before mapping)
                device_type_name = None
                make_name = None
                
                for col in raw_row.keys():
                    col_lower = normalize_column_name(col)
                    if col_lower in ["devicetype name", "devicetype_name", "device type name", "device_type", "asset type"]:
                        if not device_type_name:
                            device_type_name = str(raw_row[col]).strip()
                    elif col_lower in ["make name", "make_name", "manufacturer"]:
                        if not make_name:
                            make_name = str(raw_row[col]).strip()
                
                # Fallback to mapped row_data
                if not device_type_name:
                    device_type_name = row_data.get("name") or row_data.get("devicetype_name") or row_data.get("device_type") or row_data.get("asset_type")
                if not make_name:
                    make_name = row_data.get("name") or row_data.get("make_name") or row_data.get("manufacturer")
                
                device_type_data = {
                    "name": device_type_name,
                    "make_name": make_name,
                    "description": row_data.get("devicetype_description") or row_data.get("description", ""),
                }
                
                # Schema requires: name, make_name, and description (all with min_length=1)
                if all([device_type_data.get("name"), device_type_data.get("make_name"), device_type_data.get("description")]):
                    try:
                        validated_data = device_type_schema(**device_type_data)
                    except Exception as exc:
                        raise ValueError(f"Device type validation error: {exc}")
                    
                    result = device_type_handler(db, validated_data.model_dump())
                    
                    object_id = result.get("id")
                    if object_id:
                        dt_context = None
                        if audit_context:
                            dt_context = {
                                **audit_context,
                                "entity": ListingType.device_types.value,
                                "row": row_number,
                            }
                        log_create(
                            db=db,
                            user=current_user,
                            entity_type="device_types",
                            object_id=object_id,
                            entity_data=result,
                            context=dt_context,
                        )
                    
                    device_type_result["status"] = "success"
                    device_type_result["data"] = result
                    success_counts["device_types"] += 1
                else:
                    device_type_result["status"] = "skipped"
                    missing_fields = []
                    if not device_type_data.get("name"):
                        missing_fields.append("devicetype_name (or 'name' column)")
                    if not device_type_data.get("make_name"):
                        missing_fields.append("make_name (or 'name' column)")
                    if not device_type_data.get("description"):
                        missing_fields.append("description (or 'devicetype_description' column)")
                    device_type_result["error"] = f"Missing required fields for device type: {', '.join(missing_fields)}"
            except IntegrityError as exc:
                db.rollback()
                error_counts["device_types"] += 1
                device_type_result["status"] = "error"
                error_msg = str(exc.orig)
                # Check if it's a duplicate/unique constraint violation
                if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                    device_type_result["error"] = f"Duplicate data insertion: Device type already exists"
                else:
                    device_type_result["error"] = f"Database integrity error: {error_msg}"
                if not skip_errors:
                    aborted_early = True
                    results.append(device_type_result)
                    break
            except Exception as exc:
                db.rollback()
                error_counts["device_types"] += 1
                device_type_result["status"] = "error"
                error_msg = str(exc)
                # Preserve duplicate error messages
                if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                    device_type_result["error"] = error_msg
                else:
                    device_type_result["error"] = error_msg
                if not skip_errors:
                    aborted_early = True
                    results.append(device_type_result)
                    break
            
            results.append(device_type_result)
            if aborted_early:
                break
    
    if not aborted_early:
        # Process models (depend on makes and device types)
        for idx, row in df.iterrows():
            row_number = idx + 2
            # Get raw values from original row before mapping
            raw_row = {col: row[col] for col in row.index if pd.notna(row[col])}
            row_data = clean_dataframe_row(row)
            
            model_result: Dict[str, Any] = {
                "row": row_number,
                "entity_type": "model",
                "status": "pending",
                "data": None,
                "error": None,
            }
            
            try:
                # Extract model_name, make_name, and devicetype_name directly from raw row (before mapping)
                model_name = None
                make_name = None
                devicetype_name = None
                
                for col in raw_row.keys():
                    col_lower = normalize_column_name(col)
                    if col_lower in ["model name", "model_name", "model"]:
                        if not model_name:
                            model_name = str(raw_row[col]).strip()
                    elif col_lower in ["make name", "make_name", "manufacturer"]:
                        if not make_name:
                            make_name = str(raw_row[col]).strip()
                    elif col_lower in ["devicetype name", "devicetype_name", "device type name", "device_type", "asset type"]:
                        if not devicetype_name:
                            devicetype_name = str(raw_row[col]).strip()
                
                # Fallback to mapped row_data
                if not model_name:
                    model_name = row_data.get("name") or row_data.get("model_name") or row_data.get("model")
                if not make_name:
                    make_name = row_data.get("name") or row_data.get("make_name") or row_data.get("manufacturer")
                if not devicetype_name:
                    devicetype_name = row_data.get("devicetype_name") or row_data.get("device_type") or row_data.get("asset_type")
                
                # Get height as integer
                height_value = row_data.get("height") or row_data.get("model_height")
                if height_value:
                    try:
                        height_value = int(height_value)
                    except (ValueError, TypeError):
                        height_value = None
                
                model_data = {
                    "name": model_name,
                    "make_name": make_name,
                    "devicetype_name": devicetype_name,
                    "height": height_value,
                    "description": row_data.get("model_description") or row_data.get("description", ""),
                }
                
                # Schema requires: name, make_name, devicetype_name, height, and description (all required)
                if all([model_data.get("name"), model_data.get("make_name"), 
                       model_data.get("devicetype_name"), model_data.get("height"), model_data.get("description")]):
                    try:
                        validated_data = model_schema(**model_data)
                    except Exception as exc:
                        raise ValueError(f"Model validation error: {exc}")
                    
                    result = model_handler(db, validated_data.model_dump())
                    
                    object_id = result.get("id")
                    if object_id:
                        model_context = None
                        if audit_context:
                            model_context = {
                                **audit_context,
                                "entity": ListingType.models.value,
                                "row": row_number,
                            }
                        log_create(
                            db=db,
                            user=current_user,
                            entity_type="models",
                            object_id=object_id,
                            entity_data=result,
                            context=model_context,
                        )
                    
                    model_result["status"] = "success"
                    model_result["data"] = result
                    success_counts["models"] += 1
                else:
                    model_result["status"] = "skipped"
                    missing_fields = []
                    if not model_data.get("name"):
                        missing_fields.append("model_name (or 'name' column)")
                    if not model_data.get("make_name"):
                        missing_fields.append("make_name (or 'name' column)")
                    if not model_data.get("devicetype_name"):
                        missing_fields.append("devicetype_name")
                    if not model_data.get("height"):
                        missing_fields.append("height")
                    if not model_data.get("description"):
                        missing_fields.append("description (or 'model_description' column)")
                    model_result["error"] = f"Missing required fields for model: {', '.join(missing_fields)}"
            except IntegrityError as exc:
                db.rollback()
                error_counts["models"] += 1
                model_result["status"] = "error"
                error_msg = str(exc.orig)
                # Check if it's a duplicate/unique constraint violation
                if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                    model_result["error"] = f"Duplicate data insertion: Model already exists"
                else:
                    model_result["error"] = f"Database integrity error: {error_msg}"
                if not skip_errors:
                    aborted_early = True
                    results.append(model_result)
                    break
            except Exception as exc:
                db.rollback()
                error_counts["models"] += 1
                model_result["status"] = "error"
                error_msg = str(exc)
                # Preserve duplicate error messages
                if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                    model_result["error"] = error_msg
                else:
                    model_result["error"] = error_msg
                if not skip_errors:
                    aborted_early = True
                    results.append(model_result)
                    break
            
            results.append(model_result)
            if aborted_early:
                break
    
    if aborted_early:
        db.rollback()
    elif sum(success_counts.values()) > 0:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise RuntimeError(f"Failed to commit changes: {exc}") from exc
    
    summary = {
        "entity": "entity_devicetypes (makes, device_types, models)",
        "total_rows": len(df),
        "processed": len(results),
        "success": {
            "makes": success_counts["makes"],
            "device_types": success_counts["device_types"],
            "models": success_counts["models"],
        },
        "errors": {
            "makes": error_counts["makes"],
            "device_types": error_counts["device_types"],
            "models": error_counts["models"],
        },
        "aborted": aborted_early,
        "skip_errors": skip_errors,
    }
    
    return summary, results


def _process_devicetypes_bulk_upload_job(
    job_id: str,
    file_bytes: bytes,
    skip_errors: bool,
    current_user_id: int,
    current_user_email: Optional[str],
) -> None:
    """Background task entry point for processing device type entities and emailing results."""
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
        audit_context = build_audit_context(
            router="dcim.bulk_upload.devicetypes",
            action="create",
            extra={"job_id": job_id},
        )
        summary, results = _process_devicetypes_rows(
            db=db,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user=user,
            audit_context=audit_context,
        )
        # Invalidate caches if any entities were created
        success_data = summary.get("success", {}) if summary else {}
        if isinstance(success_data, dict):
            if success_data.get("makes"):
                invalidate_listing_cache_for_entity(ListingType.makes)
            if success_data.get("device_types"):
                invalidate_listing_cache_for_entity(ListingType.device_types)
            if success_data.get("models"):
                invalidate_listing_cache_for_entity(ListingType.models)
        app_logger.info(
            "Bulk device types upload job completed",
            extra={
                "job_id": job_id,
                "success": summary["success"] if summary else {},
                "errors": summary["errors"] if summary else {},
            },
        )
    except Exception as exc:
        failure_reason = str(exc)
        app_logger.exception(
            "Bulk device types upload job failed",
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


# =============================================================================
# API Endpoints
# =============================================================================

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
       - Expected columns: HostName, Asset Status, Building, Location, Wing, Floor, Room/Area,
         Rack No, Manufacturer, Model ID, Asset Type, IP Address, Asset PO Number, Asset Owner,
         Asset User, Application Mapped, Warranty Start Date, Warranty End Date, AMC Start Date,
         AMC End Date, Position, Space Required, Face, Description
    
    2. **racks** - Single rack entities
       - Expected columns: Rack Name, Location Name, Building Name, Wing Name, Floor Name,
         Datacenter Name, Status, Height, Description
    
    3. **entity_wfd** - Wings, Floors, Datacenters (hierarchical)
       - Expected columns: Location Name, Building Name, Wing Name, Floor Name, Datacenter Name, Description
       - Processes in order: Wings → Floors → Datacenters
    
    4. **entity_asset_details** - Asset Owners, Applications Mapped
       - Expected columns: Asset Owner Name, Location Name, Application Name, Description
       - Processes in order: Asset Owners → Applications
    
    5. **entity_devicetypes** - Makes, Device Types, Models
       - Expected columns: Make Name, DeviceType Name, Model Name, Height, Description
       - Processes in order: Makes → Device Types → Models
    
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

    # Select appropriate background task based on entity type
    if entity_type == BulkUploadEntityType.devices:
        background_tasks.add_task(
            _process_device_bulk_upload_job,
            job_id=job_id,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user_id=current_user.id,
            current_user_email=current_user.email,
        )
        entity_description = "devices"
    elif entity_type == BulkUploadEntityType.racks:
        background_tasks.add_task(
            _process_rack_bulk_upload_job,
            job_id=job_id,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user_id=current_user.id,
            current_user_email=current_user.email,
        )
        entity_description = "racks"
    elif entity_type == BulkUploadEntityType.entity_wfd:
        background_tasks.add_task(
            _process_hierarchy_bulk_upload_job,
            job_id=job_id,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user_id=current_user.id,
            current_user_email=current_user.email,
        )
        entity_description = "entity_wfd (wings, floors, datacenters)"
    elif entity_type == BulkUploadEntityType.entity_asset_details:
        background_tasks.add_task(
            _process_asset_details_bulk_upload_job,
            job_id=job_id,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user_id=current_user.id,
            current_user_email=current_user.email,
        )
        entity_description = "entity_asset_details (asset_owner, applications)"
    elif entity_type == BulkUploadEntityType.entity_devicetypes:
        background_tasks.add_task(
            _process_devicetypes_bulk_upload_job,
            job_id=job_id,
            file_bytes=file_bytes,
            skip_errors=skip_errors,
            current_user_id=current_user.id,
            current_user_email=current_user.email,
        )
        entity_description = "entity_devicetypes (makes, device_types, models)"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {entity_type}",
        )

    return {
        "entity": entity_description,
        "job_id": job_id,
        "message": (
            "CSV received. Processing will continue in the background. "
            "An email report will be sent after completion."
        ),
        "report_recipient": current_user.email,
    }

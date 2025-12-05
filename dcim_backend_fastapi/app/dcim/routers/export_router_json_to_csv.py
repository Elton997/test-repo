"""
DCIM Export Router - Converts JSON data from UI to CSV downloads.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(prefix="/api/dcim", tags=["DCIM Export"])


class ExportRequest(BaseModel):
    """Request model for CSV export."""
    data: List[Dict[str, Any]] = Body(..., description="Array of JSON objects to export as CSV")
    filename: Optional[str] = Body(None, description="Optional custom filename for the CSV")


def _get_pandas():
    """Lazy import pandas only when needed."""
    import pandas as pd
    return pd


def _flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
    """
    Flatten nested dictionaries into a single level.
    Example: {"a": {"b": 1}} -> {"a_b": 1}
    """
    items: List[tuple] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Convert lists to string representation
            items.append((new_key, str(v) if v else ""))
        else:
            items.append((new_key, v))
    return dict(items)


def _json_to_csv(data: List[Dict[str, Any]]) -> str:
    """
    Convert JSON array to CSV string.
    Handles nested objects by flattening them.
    """
    if not data:
        return ""

    pd = _get_pandas()

    # Flatten all nested dictionaries
    flattened_data = []
    for record in data:
        flattened_record = _flatten_dict(record)
        flattened_data.append(flattened_record)

    # Create DataFrame
    df = pd.DataFrame(flattened_data)

    # Convert to CSV
    return df.to_csv(index=False)


@router.post(
    "/list/export",
    summary="Export JSON data to CSV",
)
def export_dcim_entities(
    request: ExportRequest,
):
    """
    Export JSON data received from UI as CSV file.
    Accepts an array of JSON objects and converts them to CSV format.
    Nested objects are automatically flattened with underscore separators.
    """
    if not request.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided for export",
        )

    try:
        csv_content = _json_to_csv(request.data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error converting data to CSV: {str(e)}",
        )

    # Generate filename
    if request.filename:
        filename = request.filename
        if not filename.endswith(".csv"):
            filename = f"{filename}.csv"
    else:
        filename = f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


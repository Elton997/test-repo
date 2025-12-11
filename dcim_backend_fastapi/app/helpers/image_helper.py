# app/helpers/image_helper.py
"""
Helper functions for handling model images.
Handles saving, updating, and deleting model images (front and rear).
Images are associated with models, not individual devices.
"""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status

from app.core.config import get_settings


def get_device_image_storage_path() -> Path:
    """Get the base path for storing model images."""
    settings = get_settings()
    storage_path = Path(settings.DEVICE_IMAGE_STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


def save_device_image(image_file: UploadFile, model_name: str) -> str:
    """
    Save a model image file and return the relative path.
    
    Args:
        image_file: The uploaded image file
        model_name: The model name (used for generating filename)
        
    Returns:
        The relative path to the saved image
        
    Raises:
        HTTPException: If the file is not a valid image or save fails
    """
    # Validate file type
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    file_extension = Path(image_file.filename or "").suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format. Allowed formats: {', '.join(allowed_extensions)}",
        )
    
    # Generate unique filename
    # Sanitize model name for filename
    safe_model_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in model_name)
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{safe_model_name}_{unique_id}{file_extension}"
    
    # Get storage path
    storage_path = get_device_image_storage_path()
    file_path = storage_path / filename
    
    # Save the file
    try:
        # Read file content
        file_content = image_file.file.read()
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image file size exceeds maximum allowed size of 10MB",
            )
        
        # Write file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Return relative path (relative to storage base path)
        return str(file_path)
    except Exception as e:
        # Clean up if file was partially written
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save image: {str(e)}",
        )


def delete_device_image(image_path: Optional[str]) -> None:
    """
    Delete a model image file.
    
    Args:
        image_path: The path to the image file to delete
    """
    if not image_path:
        return
    
    try:
        file_path = Path(image_path)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
    except Exception as e:
        # Log error but don't raise - deletion of image shouldn't fail the operation
        # In production, you might want to log this to a logging system
        pass


def update_device_image(
    image_file: Optional[UploadFile],
    model_name: str,
    existing_image_path: Optional[str] = None,
) -> Optional[str]:
    """
    Update a model image. If new image is provided, saves it and deletes old one.
    If image_file is None, returns existing path.
    
    Args:
        image_file: The new uploaded image file (optional)
        model_name: The model name
        existing_image_path: The current image path (will be deleted if new image is provided)
        
    Returns:
        The new image path if image_file is provided, otherwise existing_image_path
    """
    if image_file is None:
        return existing_image_path
    
    # Delete old image if it exists
    if existing_image_path:
        delete_device_image(existing_image_path)
    
    # Save new image
    return save_device_image(image_file, model_name)


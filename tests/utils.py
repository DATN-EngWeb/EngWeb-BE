import os
import base64
from django.conf import settings
from django.core.files.base import ContentFile
from pathlib import Path
import uuid


def get_receptive_part_media_path(user_uuid, test_id, part_order):
    """
    Get the media path for a specific receptive part
    Format: receptive_test/{user_uuid}/test_{test_id}/part_{part_order}/
    """
    return f"receptive_test/{user_uuid}/test_{test_id}/part_{part_order}"


def save_html_content(html_content, user_uuid, test_id, part_order):
    """
    Save HTML content to a text file
    
    Args:
        html_content: HTML string to save
        user_uuid: UUID của user (từ file_storage_uuid)
        test_id: ID of the test
        part_order: Order number of the part
    
    Returns:
        Relative path to the saved file (e.g., "receptive_test/{uuid}/test_1/part_1/content.html")
    """
    if not html_content:
        return None
    
    # Create directory structure
    base_path = get_receptive_part_media_path(user_uuid, test_id, part_order)
    full_path = os.path.join(settings.MEDIA_ROOT, base_path)
    Path(full_path).mkdir(parents=True, exist_ok=True)
    
    # Save HTML content
    file_name = "content.html"
    file_path = os.path.join(full_path, file_name)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Return relative path for storing in DB
    return f"{base_path}/{file_name}"


def save_uploaded_image(image_file, user_uuid, test_id, part_order):
    """
    Save uploaded image file from request.FILES
    
    Args:
        image_file: File object from request.FILES
        user_uuid: UUID của user (từ file_storage_uuid)
        test_id: ID of the test
        part_order: Order number of the part
    
    Returns:
        Relative path to the saved file
    """
    if not image_file:
        return None
    
    # Create directory
    base_path = get_receptive_part_media_path(user_uuid, test_id, part_order)
    full_path = os.path.join(settings.MEDIA_ROOT, base_path)
    Path(full_path).mkdir(parents=True, exist_ok=True)
    
    # Get file extension
    file_ext = os.path.splitext(image_file.name)[1]
    
    # Generate unique filename
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(full_path, file_name)
    
    # Save file
    with open(file_path, 'wb') as f:
        for chunk in image_file.chunks():
            f.write(chunk)
    
    # Return relative path
    return f"{base_path}/{file_name}"
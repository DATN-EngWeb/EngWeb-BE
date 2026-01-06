import os
import base64
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from pathlib import Path
import uuid


def get_receptive_part_media_path(user_uuid, test_id, part_order):
    """
    Get the media path for a specific receptive part
    Format: media/receptive_test/{user_uuid}/test_{test_id}/part_{part_order}/
    """
    return f"media/receptive_test/{user_uuid}/test_{test_id}/part_{part_order}"


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

    # Create file path
    base_path = get_receptive_part_media_path(user_uuid, test_id, part_order)
    file_name = "content.html"
    file_path = f"{base_path}/{file_name}"

    # Save file using Django storage backend
    content_file = ContentFile(html_content.encode("utf-8"))
    default_storage.save(file_path, content_file)

    # Return relative path for storing in DB
    return file_path


def save_uploaded_file(file_obj, user_uuid, test_id, part_order):
    """
    Save uploaded file (image or audio) from request.FILES

    Args:
        file_obj: File object from request.FILES (image, audio, etc.)
        user_uuid: UUID của user (từ file_storage_uuid)
        test_id: ID of the test
        part_order: Order number of the part

    Returns:
        Relative path to the saved file
    """
    if not file_obj:
        return None

    # Create file path
    base_path = get_receptive_part_media_path(user_uuid, test_id, part_order)

    # Get file extension
    file_ext = os.path.splitext(file_obj.name)[1]

    # Generate unique filename
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = f"{base_path}/{file_name}"

    # Save file using Django storage backend
    default_storage.save(file_path, file_obj)

    # Return relative path
    return file_path

"""
Utility functions for cleaning up GCS resources when updating test data
"""

from storage.utils.gcs_presigned import GCSPresignedURLManager
from django.conf import settings
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def extract_key_from_url(url: str) -> str:
    """
    Extract GCS object key from full URL

    Args:
        url: Full GCS URL (e.g., https://storage.googleapis.com/bucket-name/media/tests/1/part1/file.png)

    Returns:
        GCS key (e.g., media/tests/1/part1/file.png)
    """
    if not url:
        return ""

    try:
        # Parse the URL
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")

        # Remove bucket name if present in path
        bucket_name = getattr(settings, "GCS_BUCKET_NAME", "")
        if bucket_name and path.startswith(bucket_name + "/"):
            path = path[len(bucket_name) + 1 :]

        return path
    except Exception as e:
        logger.error(f"Error extracting key from URL {url}: {e}")
        return ""


def delete_gcs_resource(url: str) -> bool:
    """
    Delete a single GCS resource by URL

    Args:
        url: Full GCS URL to delete

    Returns:
        True if successful, False otherwise
    """
    if not url:
        return True  # Nothing to delete

    try:
        key = extract_key_from_url(url)
        if not key:
            logger.warning(f"Could not extract key from URL: {url}")
            return False

        gcs_manager = GCSPresignedURLManager()
        result = gcs_manager.delete_object(key)

        if result:
            logger.info(f"Successfully deleted GCS resource: {key}")
        else:
            logger.warning(f"Failed to delete GCS resource: {key}")

        return result
    except Exception as e:
        logger.error(f"Error deleting GCS resource {url}: {e}")
        return False


def cleanup_changed_resources(old_resources: dict, new_resources: dict) -> dict:
    """
    Clean up only the GCS resources that changed or were removed

    Compares old and new resources dictionaries and deletes only:
    1. Resources with changed URLs (old URL != new URL)
    2. Resources that exist in old but not in new (removed fields)

    Args:
        old_resources: Current resources dict
        new_resources: New resources dict being set

    Returns:
        Dictionary with cleanup results
    """
    if not old_resources or not isinstance(old_resources, dict):
        return {}

    if not new_resources:
        new_resources = {}

    results = {}

    for key, old_url in old_resources.items():
        if not isinstance(old_url, str) or not old_url:
            continue

        new_url = new_resources.get(key)

        # Delete if:
        # 1. Key removed from new_resources (new_url is None)
        # 2. URL changed (old_url != new_url)
        if new_url is None or old_url != new_url:
            success = delete_gcs_resource(old_url)
            results[key] = {
                "old_url": old_url,
                "new_url": new_url,
                "deleted": success,
                "reason": "removed" if new_url is None else "changed",
            }

    return results


def delete_resources_from_dict(resources: dict) -> dict:
    """
    Delete all GCS resources from a resources dictionary

    Args:
        resources: Dictionary containing resource URLs (e.g., {"image": "url1", "audio": "url2"})

    Returns:
        Dictionary with deletion results for each key
    """
    if not resources or not isinstance(resources, dict):
        return {}

    results = {}
    for key, url in resources.items():
        if isinstance(url, str) and url:
            success = delete_gcs_resource(url)
            results[key] = {"url": url, "deleted": success}
        else:
            results[key] = {"url": url, "deleted": False, "reason": "Invalid URL"}

    return results


def cleanup_receptive_part_on_delete(part):
    """
    Clean up all GCS resources when deleting a ReceptivePart

    Simply deletes the entire part folder on GCS: media/tests/{test_id}/part{order}/
    This removes all resources (content, images, audio, etc.) in one operation.

    Args:
        part: ReceptivePart instance to cleanup

    Returns:
        Dictionary with cleanup results
    """
    results = {
        "folder_deleted": False,
        "folder_stats": {"deleted": 0, "total": 0},
    }

    try:
        # Delete entire part folder from GCS
        # Folder structure: media/tests/test_{test_id}/part_{part_id}/
        test_id = part.receptive_test.test.id
        part_id = part.id
        folder_prefix = f"media/tests/test_{test_id}/part_{part_id}/"

        gcs_manager = GCSPresignedURLManager()
        success_count, total_count = gcs_manager.delete_folder(folder_prefix)

        results["folder_deleted"] = success_count > 0
        results["folder_stats"] = {"deleted": success_count, "total": total_count}

        logger.info(
            f"Cleaned up ReceptivePart {part.id}: Deleted {success_count}/{total_count} files from {folder_prefix}"
        )

    except Exception as e:
        logger.error(f"Error cleaning up ReceptivePart {part.id}: {e}")

    return results


def cleanup_receptive_question_on_delete(question):
    """
    Clean up GCS resources when deleting a ReceptiveQuestion
    
    Deletes individual resource URLs (not folder) since other questions may exist in the same part.
    
    Args:
        question: ReceptiveQuestion instance to cleanup
    
    Returns:
        Dictionary with cleanup results
    """
    results = {
        "question_resources": {},
        "answers_cleaned": 0,
    }
    
    try:
        # Clean up question's resources
        if question.resources:
            results["question_resources"] = delete_resources_from_dict(question.resources)
        
        # Clean up all answers in this question
        for answer in question.receptive_answers.all():
            if answer.resources:
                delete_resources_from_dict(answer.resources)
            results["answers_cleaned"] += 1
        
        logger.info(f"Cleaned up ReceptiveQuestion {question.id}: {results}")
        
    except Exception as e:
        logger.error(f"Error cleaning up ReceptiveQuestion {question.id}: {e}")
    
    return results


def cleanup_receptive_answer_on_delete(answer):
    """
    Clean up GCS resources when deleting a ReceptiveAnswer
    
    Deletes individual resource URLs (not folder) since other answers may exist in the same question.
    
    Args:
        answer: ReceptiveAnswer instance to cleanup
    
    Returns:
        Dictionary with cleanup results
    """
    results = {
        "answer_resources": {},
    }
    
    try:
        # Clean up answer's resources
        if answer.resources:
            results["answer_resources"] = delete_resources_from_dict(answer.resources)
        
        logger.info(f"Cleaned up ReceptiveAnswer {answer.id}: {results}")
        
    except Exception as e:
        logger.error(f"Error cleaning up ReceptiveAnswer {answer.id}: {e}")
    
    return results


def cleanup_productive_test_on_update(old_productive_test, new_data: dict) -> dict:
    """
    Clean up GCS resources when updating ProductiveTest
    
    Compares old and new data for:
    - description (string URL)
    - glue_resources (dict of URLs)
    
    Only deletes resources that have changed or been removed.
    
    Args:
        old_productive_test: Current ProductiveTest instance
        new_data: Dictionary with new data (from serializer validated_data)
    
    Returns:
        Dictionary with cleanup results
    """
    results = {
        "description_cleaned": False,
        "glue_resources_cleaned": {},
    }
    
    try:
        # 1. Cleanup description if changed
        if "description" in new_data:
            old_description = old_productive_test.description or ""
            new_description = new_data.get("description") or ""
            
            # Delete old description URL if it changed
            if old_description and old_description != new_description:
                success = delete_gcs_resource(old_description)
                results["description_cleaned"] = success
                if success:
                    logger.info(f"Deleted old description URL: {old_description}")
        
        # 2. Cleanup glue_resources if changed
        if "glue_resources" in new_data:
            old_glue_resources = old_productive_test.glue_resources or {}
            new_glue_resources = new_data.get("glue_resources") or {}
            
            # Use existing cleanup_changed_resources to handle dict comparison
            cleanup_result = cleanup_changed_resources(old_glue_resources, new_glue_resources)
            results["glue_resources_cleaned"] = cleanup_result
            
            if cleanup_result:
                logger.info(f"Cleaned up ProductiveTest {old_productive_test.test_id} glue_resources: {cleanup_result}")
        
    except Exception as e:
        logger.error(f"Error cleaning up ProductiveTest {old_productive_test.test_id}: {e}")
    
    return results

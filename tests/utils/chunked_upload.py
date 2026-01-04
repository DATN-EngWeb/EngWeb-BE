import os
import shutil
from django.conf import settings
from pathlib import Path


def get_chunk_temp_dir(upload_id):
    """Get temporary directory for chunks of this upload session"""
    temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads", upload_id)
    return temp_dir


def save_chunk(upload_id, chunk_number, chunk_data, max_chunk_size=50*1024*1024):
    """
    Save a single chunk to temp directory with validation
    
    **Binary Approach (No Base64 Encoding):**
    chunk_data should be RAW BYTES of the multipart form-data payload.
    
    Args:
        upload_id: Unique upload session ID (same for all chunks)
        chunk_number: Chunk number (1-based indexing)
        chunk_data: **Raw binary bytes** of chunk
        max_chunk_size: Maximum allowed chunk size (default 50MB)
    
    Returns:
        tuple: (success: bool, file_path: str or None, error_msg: str or None)
        - success: True if chunk saved successfully
        - file_path: Path to saved chunk file (e.g., "media/temp_uploads/sess_xxx/chunk_00001")
        - error_msg: Error message if failed
    """
    try:
        # Validate chunk size
        if hasattr(chunk_data, 'size'):
            chunk_size = chunk_data.size
        elif hasattr(chunk_data, '__len__'):
            chunk_size = len(chunk_data)
        else:
            # Read to get size
            if hasattr(chunk_data, 'read'):
                content = chunk_data.read()
                chunk_size = len(content)
                chunk_data.seek(0)  # Reset for later reading
            else:
                return False, None, "Cannot determine chunk size"
        
        if chunk_size == 0:
            return False, None, "Chunk data is empty"
        
        if chunk_size > max_chunk_size:
            return False, None, f"Chunk size {chunk_size} exceeds maximum {max_chunk_size}"
        
        temp_dir = get_chunk_temp_dir(upload_id)
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
        chunk_file = os.path.join(temp_dir, f"chunk_{chunk_number:05d}")
        
        # Save chunk (raw bytes from multipart body)
        with open(chunk_file, 'wb') as f:
            if hasattr(chunk_data, 'read'):
                # File-like object (UploadedFile)
                for chunk in chunk_data.chunks():
                    f.write(chunk)
            else:
                # Binary data
                f.write(chunk_data)
        
        # Verify file was saved
        if not os.path.exists(chunk_file) or os.path.getsize(chunk_file) == 0:
            return False, None, "Failed to save chunk data"
        
        return True, chunk_file, None
        
    except Exception as e:
        print(f"Error saving chunk: {e}")
        return False, None, f"Error saving chunk: {str(e)}"


def get_missing_chunks(upload_id, total_chunks):
    """
    Check which chunks are missing from the upload session
    
    Args:
        upload_id: Unique upload session ID
        total_chunks: Total number of chunks expected
    
    Returns:
        list: List of missing chunk numbers (empty if all present)
              Example: [1, 3, 5] means chunks 1, 3, 5 are missing
    """
    try:
        temp_dir = get_chunk_temp_dir(upload_id)
        missing = []
        
        for i in range(1, total_chunks + 1):
            chunk_file = os.path.join(temp_dir, f"chunk_{i:05d}")
            if not os.path.exists(chunk_file):
                missing.append(i)
        
        return missing
    except Exception as e:
        print(f"Error checking missing chunks: {e}")
        return list(range(1, total_chunks + 1))  # Assume all missing on error


def merge_chunks(upload_id, total_chunks, output_format='binary'):
    """
    Merge all chunks into a single multipart payload (BINARY APPROACH)
    
    Example:
    - Chunk 1: bytes[0:5MB]  ─┐
    - Chunk 2: bytes[5:10MB]  ├─> Concatenate = Original 20MB payload
    - Chunk 3: bytes[10:15MB] ├─> Now it's complete multipart form-data
    - Chunk 4: bytes[15:20MB] ┘
    
    Args:
        upload_id: Unique upload session ID
        total_chunks: Total number of chunks (all must be present)
        output_format: Unused (always binary). For backward compatibility.
    
    Returns:
        bytes: Complete merged binary data (original multipart payload), or None if failed
               Ready to be parsed as multipart form-data
    
    Raises:
        ValueError: If chunks are missing or merge fails
        
    Example:
        merged_bytes = merge_chunks("sess_abc123", 4)
        # merged_bytes is now complete 20MB multipart payload
        # Next step: parse as multipart to extract data + files
    """
    try:
        temp_dir = get_chunk_temp_dir(upload_id)
        merged_file = os.path.join(temp_dir, "merged_data")
        
        # Verify all chunks exist
        missing = get_missing_chunks(upload_id, total_chunks)
        if missing:
            raise ValueError(f"Missing chunks: {missing}")
        
        # Merge chunks sequentially
        with open(merged_file, 'wb') as outfile:
            for i in range(1, total_chunks + 1):
                chunk_file = os.path.join(temp_dir, f"chunk_{i:05d}")
                with open(chunk_file, 'rb') as infile:
                    outfile.write(infile.read())
        
        # Return merged binary data (raw multipart payload)
        with open(merged_file, 'rb') as f:
            merged_data = f.read()
        
        return merged_data
    except Exception as e:
        print(f"Error merging chunks: {e}")
        return None


def cleanup_upload_session(upload_id):
    """
    Clean up temporary files for this upload session
    
    Removes all chunk files and merged_data file from temp directory.
    Called after successful merge + parse, or on error.
    
    Args:
        upload_id: Unique upload session ID
        
    Example:
        cleanup_upload_session("sess_abc123")
        # Removes: media/temp_uploads/sess_abc123/ and all its contents
    """
    try:
        temp_dir = get_chunk_temp_dir(upload_id)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Error cleaning up upload session: {e}")


def cleanup_old_uploads(max_age_hours=24):
    """
    Clean up old incomplete uploads (older than max_age_hours)
    
    Args:
        max_age_hours: Remove uploads older than this (default 24 hours)
    """
    try:
        import time
        temp_uploads_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
        if not os.path.exists(temp_uploads_dir):
            return
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for upload_id in os.listdir(temp_uploads_dir):
            upload_dir = os.path.join(temp_uploads_dir, upload_id)
            if os.path.isdir(upload_dir):
                dir_age = current_time - os.path.getmtime(upload_dir)
                if dir_age > max_age_seconds:
                    shutil.rmtree(upload_dir)
    except Exception as e:
        print(f"Error cleaning up old uploads: {e}")


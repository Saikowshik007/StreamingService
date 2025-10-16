import os
import subprocess
import logging
import base64
import tempfile
from pathlib import Path
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("ffmpeg not found. Thumbnail generation will be disabled.")
        return False

def generate_thumbnail_base64(video_path, timestamp='00:00:03', width=320):
    """
    Generate a base64 encoded thumbnail from a video file

    Args:
        video_path: Path to the video file
        timestamp: Time in video to capture (format: HH:MM:SS)
        width: Width of thumbnail (height will be calculated to maintain aspect ratio)

    Returns:
        str or None: Base64 encoded thumbnail string if successful, None otherwise
    """
    if not check_ffmpeg():
        return None

    # Use a temporary file for the thumbnail
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        # Extract thumbnail using ffmpeg
        cmd = [
            'ffmpeg',
            '-ss', timestamp,  # Seek to timestamp
            '-i', video_path,  # Input file
            '-vframes', '1',   # Extract 1 frame
            '-vf', f'scale={width}:-1',  # Resize width, maintain aspect ratio
            '-q:v', '2',       # High quality
            '-y',              # Overwrite output file
            temp_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and os.path.exists(temp_path):
            # Read the image and convert to base64
            with Image.open(temp_path) as img:
                # Optimize the image
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=85, optimize=True)
                img_bytes = buffered.getvalue()

                # Convert to base64
                base64_string = base64.b64encode(img_bytes).decode('utf-8')
                logger.info(f"Generated base64 thumbnail for: {video_path}")

                # Clean up temp file
                os.unlink(temp_path)

                return f"data:image/jpeg;base64,{base64_string}"
        else:
            logger.error(f"Failed to generate thumbnail: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        logger.error(f"Thumbnail generation timed out for {video_path}")
        return None
    except Exception as e:
        logger.error(f"Error generating thumbnail: {str(e)}")
        return None
    finally:
        # Ensure temp file is deleted
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

def generate_thumbnail_for_file(video_path, filename):
    """
    Generate base64 thumbnail for a video file

    Args:
        video_path: Full path to the video file
        filename: Original filename (for logging)

    Returns:
        str or None: Base64 encoded thumbnail if successful, None otherwise
    """
    logger.info(f"Generating thumbnail for: {filename}")
    return generate_thumbnail_base64(video_path)

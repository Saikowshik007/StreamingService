import hashlib
import hmac
import time
from typing import Tuple, Optional
from config import Config
import logging

logger = logging.getLogger(__name__)


def generate_signed_url(file_id: str, expiration_seconds: int = None) -> Tuple[str, int]:
    """
    Generate a signed URL token for a file.

    Args:
        file_id: The ID of the file to sign
        expiration_seconds: Expiration time in seconds (defaults to Config.URL_EXPIRATION_SECONDS)

    Returns:
        Tuple of (signature, expiration_timestamp)
    """
    if expiration_seconds is None:
        expiration_seconds = Config.URL_EXPIRATION_SECONDS

    expiration = int(time.time()) + expiration_seconds

    # Create the message to sign: file_id:expiration
    message = f"{file_id}:{expiration}"

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        Config.URL_SIGNING_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    logger.info(f"Generated signed URL for file {file_id}, expires at {expiration}")
    return signature, expiration


def verify_signed_url(file_id: str, signature: str, expiration: int) -> bool:
    """
    Verify a signed URL token.

    Args:
        file_id: The ID of the file
        signature: The signature to verify
        expiration: The expiration timestamp

    Returns:
        True if signature is valid and not expired, False otherwise
    """
    # Check if expired
    current_time = int(time.time())
    if current_time > expiration:
        logger.warning(f"Signed URL expired for file {file_id}. Expired at {expiration}, current time {current_time}")
        return False

    # Recreate the expected signature
    message = f"{file_id}:{expiration}"
    expected_signature = hmac.new(
        Config.URL_SIGNING_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(signature, expected_signature)

    if not is_valid:
        logger.warning(f"Invalid signature for file {file_id}")

    return is_valid


def parse_signed_params(request_args) -> Optional[Tuple[str, int]]:
    """
    Parse signature and expiration from request arguments.

    Args:
        request_args: Flask request.args object

    Returns:
        Tuple of (signature, expiration) or None if missing
    """
    signature = request_args.get('signature')
    expiration_str = request_args.get('expires')

    if not signature or not expiration_str:
        return None

    try:
        expiration = int(expiration_str)
        return signature, expiration
    except ValueError:
        logger.warning(f"Invalid expiration value: {expiration_str}")
        return None
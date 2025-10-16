from firebase_admin import auth
from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def verify_firebase_token(id_token):
    """Verify Firebase ID token"""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        return None

def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No authorization token provided'}), 401

        id_token = auth_header.split('Bearer ')[1]
        decoded_token = verify_firebase_token(id_token)

        if not decoded_token:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Add user info to request object
        request.current_user = {
            'uid': decoded_token['uid'],
            'email': decoded_token.get('email'),
            'email_verified': decoded_token.get('email_verified', False)
        }

        return f(*args, **kwargs)

    return decorated_function

def optional_auth(f):
    """Decorator for optional authentication (doesn't fail if no token)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if auth_header and auth_header.startswith('Bearer '):
            id_token = auth_header.split('Bearer ')[1]
            decoded_token = verify_firebase_token(id_token)

            if decoded_token:
                request.current_user = {
                    'uid': decoded_token['uid'],
                    'email': decoded_token.get('email'),
                    'email_verified': decoded_token.get('email_verified', False)
                }
            else:
                request.current_user = None
        else:
            request.current_user = None

        return f(*args, **kwargs)

    return decorated_function

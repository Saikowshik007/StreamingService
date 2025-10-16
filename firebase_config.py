import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import logging

logger = logging.getLogger(__name__)

_db = None

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    global _db

    if _db is not None:
        return _db

    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
        _db = firestore.client()
        logger.info("Firebase already initialized")
        return _db
    except ValueError:
        pass

    # Try to get credentials from environment variable (JSON string or file path)
    cred_json = os.environ.get('FIREBASE_CREDENTIALS')
    cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')

    try:
        if cred_json:
            # Parse JSON string from environment
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            logger.info("Using Firebase credentials from environment variable")
        elif os.path.exists(cred_path):
            # Use credentials file
            cred = credentials.Certificate(cred_path)
            logger.info(f"Using Firebase credentials from file: {cred_path}")
        else:
            # Use application default credentials (for local development)
            logger.warning("No Firebase credentials found. Using application default credentials.")
            firebase_admin.initialize_app()
            _db = firestore.client()
            return _db

        firebase_admin.initialize_app(cred)
        _db = firestore.client()
        logger.info("Firebase initialized successfully")
        return _db

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        raise

def get_db():
    """Get Firestore database instance"""
    global _db
    if _db is None:
        _db = initialize_firebase()
    return _db

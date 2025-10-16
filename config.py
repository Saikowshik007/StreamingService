import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = int(os.getenv('PORT', 5000))
    MEDIA_PATH = os.getenv('MEDIA_PATH', 'D:/CourseMedia')
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    # Secret key for signing URLs (should be set in .env for production)
    URL_SIGNING_SECRET = os.getenv('URL_SIGNING_SECRET', os.urandom(32).hex())
    # URL expiration time in seconds (default: 1 hour)
    URL_EXPIRATION_SECONDS = int(os.getenv('URL_EXPIRATION_SECONDS', 3600))

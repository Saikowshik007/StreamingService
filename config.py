import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = int(os.getenv('PORT', 5000))
    MEDIA_PATH = os.getenv('MEDIA_PATH', 'D:')
    DEBUG = os.getenv('FLASK_ENV') == 'development'

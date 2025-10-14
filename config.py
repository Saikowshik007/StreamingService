import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = int(os.getenv('PORT', 5000))
    MEDIA_PATH = os.getenv('MEDIA_PATH', 'C:/Users/anant/Desktop/CourseMedia')
    DB_PATH = os.getenv('DB_PATH', 'database.db')
    DEBUG = os.getenv('FLASK_ENV') == 'development'

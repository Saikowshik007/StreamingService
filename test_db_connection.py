"""
Test script to verify PostgreSQL database connection and schema.
Run this after starting PostgreSQL with: docker-compose up -d postgres
"""

import os
from dotenv import load_dotenv
from database_enhanced import get_enhanced_db_service

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test the database connection and schema initialization."""
    print("Testing PostgreSQL database connection...")
    print(f"DB Host: {os.getenv('DB_HOST', 'localhost')}")
    print(f"DB Port: {os.getenv('DB_PORT', '5432')}")
    print(f"DB Name: {os.getenv('DB_NAME', 'streaming_service')}")
    print(f"DB User: {os.getenv('DB_USER', 'postgres')}")
    print()

    try:
        # Initialize database service
        db = get_enhanced_db_service()
        print("✓ Database connection pool created successfully")
        print("✓ Database schema initialized successfully")
        print()

        # Test inserting sample progress
        print("Testing database operations...")

        test_user_id = "test_user_123"
        test_file_id = "test_file_456"
        test_lesson_id = "test_lesson_789"
        test_course_id = "test_course_101"

        # Insert test progress
        success = db.update_file_progress(
            user_id=test_user_id,
            file_id=test_file_id,
            lesson_id=test_lesson_id,
            course_id=test_course_id,
            progress_seconds=120,
            progress_percentage=50.0,
            completed=False
        )

        if success:
            print(f"✓ Successfully inserted test progress for user {test_user_id}")
        else:
            print(f"✗ Failed to insert test progress")
            return False

        # Retrieve test progress
        progress = db.get_file_progress(test_user_id, test_file_id)

        if progress:
            print(f"✓ Successfully retrieved test progress")
            print(f"  - Progress: {progress['progress_percentage']}%")
            print(f"  - Progress seconds: {progress['progress_seconds']}")
            print(f"  - Completed: {progress['completed']}")
        else:
            print(f"✗ Failed to retrieve test progress")
            return False

        # Get course progress (should be auto-calculated)
        course_progress = db.get_course_progress(test_user_id, test_course_id)

        if course_progress:
            print(f"✓ Successfully retrieved course progress")
            print(f"  - Total files: {course_progress['total_files']}")
            print(f"  - Completed files: {course_progress['completed_files']}")
            print(f"  - Progress: {course_progress['progress_percentage']}%")
        else:
            print(f"✓ Course progress not found (this is normal for a new course)")

        print()
        print("=" * 60)
        print("Database setup and testing completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Start the Flask backend: python app.py")
        print("2. The backend will automatically use PostgreSQL for progress tracking")
        print("3. User progress will be stored with their Firebase user ID")
        print()
        return True

    except Exception as e:
        print(f"✗ Database connection test failed: {str(e)}")
        print()
        print("Make sure PostgreSQL is running:")
        print("  docker-compose up -d postgres")
        print()
        return False

if __name__ == "__main__":
    test_database_connection()

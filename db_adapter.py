"""
Database adapter that prioritizes PostgreSQL and falls back to Firebase.
This adapter provides a unified interface for database operations while
avoiding Firebase quota limits.
"""

import logging
from database_enhanced import get_enhanced_db_service
import firebase_service as firebase_db

logger = logging.getLogger(__name__)


class DatabaseAdapter:
    """
    Unified database adapter that uses PostgreSQL as primary storage
    and Firebase as optional backup/sync.
    """

    def __init__(self, use_postgres=True, use_firebase_fallback=False):
        """
        Initialize the database adapter.

        Args:
            use_postgres: Use PostgreSQL as primary database (default: True)
            use_firebase_fallback: Fall back to Firebase if PostgreSQL fails (default: False)
        """
        self.use_postgres = use_postgres
        self.use_firebase_fallback = use_firebase_fallback
        self.pg_db = None

        if self.use_postgres:
            try:
                self.pg_db = get_enhanced_db_service()
                logger.info("PostgreSQL database adapter initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL: {str(e)}")
                if not self.use_firebase_fallback:
                    raise

    # ==================== COURSE METHODS ====================

    def create_course(self, course_data):
        """Create a course in the database."""
        course_id = course_data.get('id')

        # Try PostgreSQL first
        if self.pg_db:
            try:
                result = self.pg_db.create_or_update_course(
                    course_id=course_id,
                    title=course_data.get('title', ''),
                    folder_path=course_data.get('folder_path', ''),
                    description=course_data.get('description', ''),
                    instructor=course_data.get('instructor', ''),
                    thumbnail=course_data.get('thumbnail', ''),
                    total_files=course_data.get('total_files', 0)
                )
                if result:
                    logger.debug(f"Course {course_id} created in PostgreSQL")
                    return result
            except Exception as e:
                logger.error(f"Error creating course in PostgreSQL: {str(e)}")

        # Fallback to Firebase
        if self.use_firebase_fallback:
            try:
                return firebase_db.create_course(course_data)
            except Exception as e:
                logger.error(f"Error creating course in Firebase: {str(e)}")

        return course_id

    def get_course_by_id(self, course_id):
        """Get a course by ID."""
        # Try PostgreSQL first
        if self.pg_db:
            try:
                result = self.pg_db.get_course_by_id(course_id)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Error getting course from PostgreSQL: {str(e)}")

        # Fallback to Firebase
        if self.use_firebase_fallback:
            try:
                return firebase_db.get_course_by_id(course_id)
            except Exception as e:
                logger.error(f"Error getting course from Firebase: {str(e)}")

        return None

    def get_course_by_folder_path(self, folder_path):
        """Get a course by folder path."""
        # Try PostgreSQL first
        if self.pg_db:
            try:
                result = self.pg_db.get_course_by_folder_path(folder_path)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Error getting course by path from PostgreSQL: {str(e)}")

        return None

    def get_all_courses(self):
        """Get all courses."""
        # Try PostgreSQL first
        if self.pg_db:
            try:
                results = self.pg_db.get_all_courses()
                if results:
                    return results
            except Exception as e:
                logger.error(f"Error getting all courses from PostgreSQL: {str(e)}")

        # Fallback to Firebase
        if self.use_firebase_fallback:
            try:
                return firebase_db.get_all_courses()
            except Exception as e:
                logger.error(f"Error getting all courses from Firebase: {str(e)}")

        return []

    def update_course(self, course_id, updates):
        """Update a course."""
        if self.pg_db:
            try:
                # Get existing course first
                course = self.pg_db.get_course_by_id(course_id)
                if course:
                    # Merge updates
                    course.update(updates)
                    return self.pg_db.create_or_update_course(
                        course_id=course_id,
                        title=course.get('title', ''),
                        folder_path=course.get('folder_path', ''),
                        description=course.get('description', ''),
                        instructor=course.get('instructor', ''),
                        thumbnail=course.get('thumbnail', ''),
                        total_files=course.get('total_files', 0)
                    )
            except Exception as e:
                logger.error(f"Error updating course in PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.update_course(course_id, updates)
            except Exception as e:
                logger.error(f"Error updating course in Firebase: {str(e)}")

        return None

    # ==================== LESSON METHODS ====================

    def create_lesson(self, lesson_data):
        """Create a lesson in the database."""
        lesson_id = lesson_data.get('id')

        if self.pg_db:
            try:
                result = self.pg_db.create_or_update_lesson(
                    lesson_id=lesson_id,
                    course_id=lesson_data.get('course_id', ''),
                    title=lesson_data.get('title', ''),
                    folder_path=lesson_data.get('folder_path', ''),
                    description=lesson_data.get('description', ''),
                    order_index=lesson_data.get('order_index', 0)
                )
                if result:
                    logger.debug(f"Lesson {lesson_id} created in PostgreSQL")
                    return result
            except Exception as e:
                logger.error(f"Error creating lesson in PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.create_lesson(lesson_data)
            except Exception as e:
                logger.error(f"Error creating lesson in Firebase: {str(e)}")

        return lesson_id

    def get_lesson_by_id(self, lesson_id):
        """Get a lesson by ID."""
        if self.pg_db:
            try:
                result = self.pg_db.get_lesson_by_id(lesson_id)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Error getting lesson from PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.get_lesson_by_id(lesson_id)
            except Exception as e:
                logger.error(f"Error getting lesson from Firebase: {str(e)}")

        return None

    def get_lessons_by_course_id(self, course_id):
        """Get all lessons for a course."""
        if self.pg_db:
            try:
                results = self.pg_db.get_lessons_by_course(course_id)
                if results is not None:
                    return results
            except Exception as e:
                logger.error(f"Error getting lessons from PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.get_lessons_by_course_id(course_id)
            except Exception as e:
                logger.error(f"Error getting lessons from Firebase: {str(e)}")

        return []

    # ==================== FILE METHODS ====================

    def create_file(self, file_data):
        """Create a file in the database."""
        file_id = file_data.get('id')

        if self.pg_db:
            try:
                result = self.pg_db.create_or_update_file(
                    file_id=file_id,
                    lesson_id=file_data.get('lesson_id', ''),
                    course_id=file_data.get('course_id', ''),
                    filename=file_data.get('filename', ''),
                    file_path=file_data.get('file_path', ''),
                    file_type=file_data.get('file_type', ''),
                    file_size=file_data.get('file_size', 0),
                    duration=file_data.get('duration', 0),
                    order_index=file_data.get('order_index', 0),
                    is_video=file_data.get('is_video', False),
                    is_document=file_data.get('is_document', False),
                    thumbnail_base64=file_data.get('thumbnail_base64', '')
                )
                if result:
                    logger.debug(f"File {file_id} created in PostgreSQL")
                    return result
            except Exception as e:
                logger.error(f"Error creating file in PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.create_file(file_data)
            except Exception as e:
                logger.error(f"Error creating file in Firebase: {str(e)}")

        return file_id

    def get_file_by_id(self, file_id):
        """Get a file by ID."""
        if self.pg_db:
            try:
                result = self.pg_db.get_file_by_id(file_id)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Error getting file from PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.get_file_by_id(file_id)
            except Exception as e:
                logger.error(f"Error getting file from Firebase: {str(e)}")

        return None

    def get_files_by_lesson_id(self, lesson_id):
        """Get all files for a lesson."""
        if self.pg_db:
            try:
                results = self.pg_db.get_files_by_lesson(lesson_id)
                if results is not None:
                    return results
            except Exception as e:
                logger.error(f"Error getting files from PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.get_files_by_lesson_id(lesson_id)
            except Exception as e:
                logger.error(f"Error getting files from Firebase: {str(e)}")

        return []

    def get_files_by_course_id(self, course_id):
        """Get all files for a course."""
        if self.pg_db:
            try:
                results = self.pg_db.get_files_by_course(course_id)
                if results is not None:
                    return results
            except Exception as e:
                logger.error(f"Error getting files from PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.get_files_by_course_id(course_id)
            except Exception as e:
                logger.error(f"Error getting files from Firebase: {str(e)}")

        return []

    # ==================== PROGRESS METHODS ====================

    def update_user_progress(self, user_id, file_id, lesson_id, course_id,
                            progress_seconds, progress_percentage, completed=False):
        """Update user progress."""
        if self.pg_db:
            try:
                return self.pg_db.update_file_progress(
                    user_id, file_id, lesson_id, course_id,
                    progress_seconds, progress_percentage, completed
                )
            except Exception as e:
                logger.error(f"Error updating progress in PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.update_user_progress(
                    user_id, file_id, lesson_id, course_id,
                    progress_seconds, progress_percentage, completed
                )
            except Exception as e:
                logger.error(f"Error updating progress in Firebase: {str(e)}")

        return False

    def get_user_progress(self, user_id, file_id):
        """Get user progress for a file."""
        if self.pg_db:
            try:
                result = self.pg_db.get_file_progress(user_id, file_id)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Error getting progress from PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.get_user_progress(user_id, file_id)
            except Exception as e:
                logger.error(f"Error getting progress from Firebase: {str(e)}")

        return None

    def get_course_progress(self, course_id, user_id):
        """Get course progress for a user."""
        if self.pg_db:
            try:
                result = self.pg_db.get_course_progress(user_id, course_id)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Error getting course progress from PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.get_course_progress(course_id, user_id)
            except Exception as e:
                logger.error(f"Error getting course progress from Firebase: {str(e)}")

        return None

    def update_course_progress(self, course_id, user_id='default_user'):
        """Update/recalculate course progress for a user."""
        if self.pg_db:
            try:
                # Use the internal _update_course_progress method
                self.pg_db._update_course_progress(user_id, course_id)
                return True
            except Exception as e:
                logger.error(f"Error updating course progress in PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.update_course_progress(course_id, user_id)
            except Exception as e:
                logger.error(f"Error updating course progress in Firebase: {str(e)}")

        return False

    # ==================== SCAN HISTORY ====================

    def record_scan_history(self, scan_data):
        """Record scan history."""
        if self.pg_db:
            try:
                return self.pg_db.record_scan(
                    scan_path=scan_data.get('scan_path', ''),
                    files_found=scan_data.get('files_found', 0),
                    courses_added=scan_data.get('courses_added', 0),
                    lessons_added=scan_data.get('lessons_added', 0),
                    scan_duration=scan_data.get('scan_duration', 0),
                    status=scan_data.get('status', 'completed')
                )
            except Exception as e:
                logger.error(f"Error recording scan in PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.record_scan_history(scan_data)
            except Exception as e:
                logger.error(f"Error recording scan in Firebase: {str(e)}")

        return None

    def get_scan_history(self, limit=10):
        """Get scan history."""
        if self.pg_db:
            try:
                results = self.pg_db.get_scan_history(limit)
                if results:
                    return results
            except Exception as e:
                logger.error(f"Error getting scan history from PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.get_scan_history()
            except Exception as e:
                logger.error(f"Error getting scan history from Firebase: {str(e)}")

        return []

    def get_stats(self):
        """Get overall statistics."""
        if self.pg_db:
            try:
                # Get counts from PostgreSQL
                conn = self.pg_db.get_connection()
                cursor = conn.cursor()

                # Count courses
                cursor.execute("SELECT COUNT(*) FROM courses")
                courses_count = cursor.fetchone()[0]

                # Count lessons
                cursor.execute("SELECT COUNT(*) FROM lessons")
                lessons_count = cursor.fetchone()[0]

                # Count all files
                cursor.execute("SELECT COUNT(*) FROM files")
                files_count = cursor.fetchone()[0]

                # Count videos
                cursor.execute("SELECT COUNT(*) FROM files WHERE is_video = TRUE")
                videos_count = cursor.fetchone()[0]

                # Count documents
                cursor.execute("SELECT COUNT(*) FROM files WHERE is_document = TRUE")
                documents_count = cursor.fetchone()[0]

                cursor.close()
                self.pg_db.return_connection(conn)

                return {
                    'courses': courses_count,
                    'lessons': lessons_count,
                    'files': files_count,
                    'videos': videos_count,
                    'documents': documents_count
                }
            except Exception as e:
                logger.error(f"Error getting stats from PostgreSQL: {str(e)}")

        if self.use_firebase_fallback:
            try:
                return firebase_db.get_stats()
            except Exception as e:
                logger.error(f"Error getting stats from Firebase: {str(e)}")

        return {
            'courses': 0,
            'lessons': 0,
            'files': 0,
            'videos': 0,
            'documents': 0
        }

    # ==================== OPTIMIZED BATCH METHODS ====================

    def get_all_courses_with_progress(self, user_id):
        """Get all courses with progress in a single query (eliminates N+1)."""
        if self.pg_db:
            try:
                results = self.pg_db.get_all_courses_with_progress(user_id)
                if results is not None:
                    return results
            except Exception as e:
                logger.error(f"Error getting courses with progress from PostgreSQL: {str(e)}")

        # Fallback to non-optimized method
        return self._get_all_courses_with_progress_fallback(user_id)

    def _get_all_courses_with_progress_fallback(self, user_id):
        """Fallback: Get courses with progress using multiple queries."""
        courses = self.get_all_courses()
        for course in courses:
            progress = self.get_course_progress(course['id'], user_id)
            if progress:
                course['progress_percentage'] = progress.get('progress_percentage', 0)
                course['completed_files'] = progress.get('completed_files', 0)
                course['progress_total_files'] = progress.get('total_files', 0)
            else:
                course['progress_percentage'] = 0
                course['completed_files'] = 0
                course['progress_total_files'] = 0
        return courses

    def get_course_with_details(self, course_id, user_id):
        """Get course with lessons, files, and progress in minimal queries."""
        if self.pg_db:
            try:
                result = self.pg_db.get_course_with_details(course_id, user_id)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Error getting course with details from PostgreSQL: {str(e)}")

        # Fallback to non-optimized method
        return self._get_course_with_details_fallback(course_id, user_id)

    def _get_course_with_details_fallback(self, course_id, user_id):
        """Fallback: Get course with details using multiple queries."""
        course = self.get_course_by_id(course_id)
        if not course:
            return None

        progress = self.get_course_progress(course_id, user_id)
        if progress:
            course['progress_percentage'] = progress.get('progress_percentage', 0)
            course['completed_files'] = progress.get('completed_files', 0)
            course['progress_total_files'] = progress.get('total_files', 0)
        else:
            course['progress_percentage'] = 0
            course['completed_files'] = 0
            course['progress_total_files'] = 0

        lessons = self.get_lessons_by_course_id(course_id)
        for lesson in lessons:
            lesson['files'] = self.get_files_by_lesson_id(lesson['id'])
            for file in lesson['files']:
                file_progress = self.get_user_progress(user_id, file['id'])
                if file_progress:
                    file['progress_seconds'] = file_progress.get('progress_seconds', 0)
                    file['progress_percentage'] = file_progress.get('progress_percentage', 0)
                    file['completed'] = file_progress.get('completed', False)
                else:
                    file['progress_seconds'] = 0
                    file['progress_percentage'] = 0
                    file['completed'] = False

        course['lessons'] = lessons
        return course

    def get_lesson_with_files_and_progress(self, lesson_id, user_id):
        """Get lesson with files and progress in minimal queries."""
        if self.pg_db:
            try:
                result = self.pg_db.get_lesson_with_files_and_progress(lesson_id, user_id)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Error getting lesson with files from PostgreSQL: {str(e)}")

        # Fallback to non-optimized method
        return self._get_lesson_with_files_fallback(lesson_id, user_id)

    def _get_lesson_with_files_fallback(self, lesson_id, user_id):
        """Fallback: Get lesson with files using multiple queries."""
        lesson = self.get_lesson_by_id(lesson_id)
        if not lesson:
            return None

        files = self.get_files_by_lesson_id(lesson_id)
        for file in files:
            file_progress = self.get_user_progress(user_id, file['id'])
            if file_progress:
                file['progress_seconds'] = file_progress.get('progress_seconds', 0)
                file['progress_percentage'] = file_progress.get('progress_percentage', 0)
                file['completed'] = file_progress.get('completed', False)
            else:
                file['progress_seconds'] = 0
                file['progress_percentage'] = 0
                file['completed'] = False

        lesson['files'] = files
        return lesson


# Singleton instance
db_adapter = None

def get_db_adapter(use_postgres=True, use_firebase_fallback=False):
    """
    Get or create the database adapter singleton.

    Args:
        use_postgres: Use PostgreSQL as primary (default: True)
        use_firebase_fallback: Fall back to Firebase if PostgreSQL fails (default: False)
    """
    global db_adapter
    if db_adapter is None:
        db_adapter = DatabaseAdapter(use_postgres, use_firebase_fallback)
    return db_adapter

"""
Enhanced PostgreSQL database service with full metadata storage.
This service manages courses, lessons, files, AND user progress.
Reduces dependency on Firebase to avoid quota limits.
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, Json
import os
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class EnhancedDatabaseService:
    """
    PostgreSQL database service for managing all streaming service data.
    Stores courses, lessons, files, and user progress locally.
    """

    def __init__(self):
        """Initialize database connection pool."""
        self.connection_pool = None
        self.initialize_pool()

    def initialize_pool(self):
        """Create connection pool to PostgreSQL database."""
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'streaming_service')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'postgres')

        logger.info(f"Connecting to PostgreSQL at {db_host}:{db_port}/{db_name}")

        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # minimum connections
                20,  # maximum connections (increased for scanning)
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=5
            )
            logger.info("✓ Enhanced database connection pool created successfully")

            # Try to create database if it doesn't exist
            self.initialize_schema()

        except psycopg2.OperationalError as e:
            error_msg = str(e)

            # Check if database doesn't exist
            if "does not exist" in error_msg and db_name in error_msg:
                logger.warning(f"Database '{db_name}' does not exist. Attempting to create it...")
                try:
                    # Connect to default 'postgres' database to create our database
                    temp_conn = psycopg2.connect(
                        host=db_host,
                        port=db_port,
                        database='postgres',  # Connect to default database
                        user=db_user,
                        password=db_password
                    )
                    temp_conn.autocommit = True
                    cursor = temp_conn.cursor()
                    cursor.execute(f"CREATE DATABASE {db_name}")
                    cursor.close()
                    temp_conn.close()
                    logger.info(f"✓ Database '{db_name}' created successfully")

                    # Now create the connection pool to the new database
                    self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                        1, 20,
                        host=db_host,
                        port=db_port,
                        database=db_name,
                        user=db_user,
                        password=db_password
                    )
                    logger.info("✓ Connected to newly created database")
                    self.initialize_schema()

                except Exception as create_error:
                    logger.error(f"Failed to create database: {str(create_error)}")
                    raise
            else:
                logger.error(f"Failed to connect to PostgreSQL: {error_msg}")
                logger.error("Please check:")
                logger.error(f"  1. PostgreSQL is running on {db_host}:{db_port}")
                logger.error(f"  2. Credentials are correct (user: {db_user})")
                logger.error(f"  3. Run: python check_postgres.py")
                raise

        except Exception as e:
            logger.error(f"Error creating connection pool: {str(e)}")
            raise

    def get_connection(self):
        """Get a connection from the pool."""
        return self.connection_pool.getconn()

    def return_connection(self, conn):
        """Return a connection to the pool."""
        self.connection_pool.putconn(conn)

    def initialize_schema(self):
        """Create database tables if they don't exist."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Courses table - metadata for courses
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id VARCHAR(128) PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    description TEXT,
                    instructor VARCHAR(255),
                    thumbnail TEXT,
                    folder_path TEXT NOT NULL UNIQUE,
                    total_files INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Lessons table - metadata for lessons
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id VARCHAR(128) PRIMARY KEY,
                    course_id VARCHAR(128) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    description TEXT,
                    folder_path TEXT NOT NULL UNIQUE,
                    order_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
                )
            """)

            # Files table - metadata for media files
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id VARCHAR(128) PRIMARY KEY,
                    lesson_id VARCHAR(128) NOT NULL,
                    course_id VARCHAR(128) NOT NULL,
                    filename VARCHAR(500) NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    file_type VARCHAR(50),
                    file_size BIGINT,
                    duration INTEGER,
                    order_index INTEGER DEFAULT 0,
                    is_video BOOLEAN DEFAULT FALSE,
                    is_document BOOLEAN DEFAULT FALSE,
                    thumbnail_base64 TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
                )
            """)

            # User progress table - tracks individual file/lesson progress
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(128) NOT NULL,
                    file_id VARCHAR(128) NOT NULL,
                    lesson_id VARCHAR(128),
                    course_id VARCHAR(128),
                    progress_seconds INTEGER DEFAULT 0,
                    progress_percentage DECIMAL(5,2) DEFAULT 0.0,
                    completed BOOLEAN DEFAULT FALSE,
                    last_watched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, file_id)
                )
            """)

            # Course progress table - aggregated course-level progress
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS course_progress (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(128) NOT NULL,
                    course_id VARCHAR(128) NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    completed_files INTEGER DEFAULT 0,
                    total_duration INTEGER DEFAULT 0,
                    watched_duration INTEGER DEFAULT 0,
                    progress_percentage DECIMAL(5,2) DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course_id)
                )
            """)

            # Lesson progress table - lesson-level progress tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lesson_progress (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(128) NOT NULL,
                    lesson_id VARCHAR(128) NOT NULL,
                    course_id VARCHAR(128),
                    total_files INTEGER DEFAULT 0,
                    completed_files INTEGER DEFAULT 0,
                    progress_percentage DECIMAL(5,2) DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, lesson_id)
                )
            """)

            # Scan history table - track folder scans
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id SERIAL PRIMARY KEY,
                    scan_path TEXT NOT NULL,
                    files_found INTEGER DEFAULT 0,
                    courses_added INTEGER DEFAULT 0,
                    lessons_added INTEGER DEFAULT 0,
                    scan_duration DECIMAL(10,2),
                    scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'completed'
                )
            """)

            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lessons_course_id ON lessons(course_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_lesson_id ON files(lesson_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_course_id ON files(course_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_progress_user_id ON user_progress(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_progress_course_id ON user_progress(course_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_course_progress_user_id ON course_progress(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lesson_progress_user_id ON lesson_progress(user_id)")

            conn.commit()
            cursor.close()
            logger.info("Enhanced database schema initialized successfully")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error initializing schema: {str(e)}")
            raise
        finally:
            if conn:
                self.return_connection(conn)

    # ==================== COURSE METHODS ====================

    def create_or_update_course(self, course_id, title, folder_path, description='',
                                instructor='', thumbnail='', total_files=0):
        """Create or update a course."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO courses (id, title, description, instructor, thumbnail,
                                   folder_path, total_files, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    instructor = EXCLUDED.instructor,
                    thumbnail = EXCLUDED.thumbnail,
                    folder_path = EXCLUDED.folder_path,
                    total_files = EXCLUDED.total_files,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """, (course_id, title, description, instructor, thumbnail,
                  folder_path, total_files, datetime.now()))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            return result[0] if result else course_id
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error creating/updating course: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_course_by_id(self, course_id):
        """Get course by ID."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT * FROM courses WHERE id = %s", (course_id,))
            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting course: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_course_by_folder_path(self, folder_path):
        """Get course by folder path."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT * FROM courses WHERE folder_path = %s", (folder_path,))
            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting course by path: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_all_courses(self):
        """Get all courses."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT * FROM courses ORDER BY title")
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error getting all courses: {str(e)}")
            return []
        finally:
            if conn:
                self.return_connection(conn)

    # ==================== LESSON METHODS ====================

    def create_or_update_lesson(self, lesson_id, course_id, title, folder_path,
                               description='', order_index=0):
        """Create or update a lesson."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO lessons (id, course_id, title, description, folder_path, order_index)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    course_id = EXCLUDED.course_id,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    folder_path = EXCLUDED.folder_path,
                    order_index = EXCLUDED.order_index
                RETURNING id
            """, (lesson_id, course_id, title, description, folder_path, order_index))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            return result[0] if result else lesson_id
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error creating/updating lesson: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_lesson_by_id(self, lesson_id):
        """Get lesson by ID."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT * FROM lessons WHERE id = %s", (lesson_id,))
            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting lesson: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_lessons_by_course(self, course_id):
        """Get all lessons for a course."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM lessons
                WHERE course_id = %s
                ORDER BY order_index, title
            """, (course_id,))

            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error getting lessons for course: {str(e)}")
            return []
        finally:
            if conn:
                self.return_connection(conn)

    # ==================== FILE METHODS ====================

    def create_or_update_file(self, file_id, lesson_id, course_id, filename, file_path,
                             file_type='', file_size=0, duration=0, order_index=0,
                             is_video=False, is_document=False, thumbnail_base64=''):
        """Create or update a file."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO files (id, lesson_id, course_id, filename, file_path, file_type,
                                 file_size, duration, order_index, is_video, is_document,
                                 thumbnail_base64)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    lesson_id = EXCLUDED.lesson_id,
                    course_id = EXCLUDED.course_id,
                    filename = EXCLUDED.filename,
                    file_path = EXCLUDED.file_path,
                    file_type = EXCLUDED.file_type,
                    file_size = EXCLUDED.file_size,
                    duration = EXCLUDED.duration,
                    order_index = EXCLUDED.order_index,
                    is_video = EXCLUDED.is_video,
                    is_document = EXCLUDED.is_document,
                    thumbnail_base64 = EXCLUDED.thumbnail_base64
                RETURNING id
            """, (file_id, lesson_id, course_id, filename, file_path, file_type,
                  file_size, duration, order_index, is_video, is_document, thumbnail_base64))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            return result[0] if result else file_id
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error creating/updating file: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_file_by_id(self, file_id):
        """Get file by ID."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT * FROM files WHERE id = %s", (file_id,))
            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting file: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_files_by_lesson(self, lesson_id):
        """Get all files for a lesson."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM files
                WHERE lesson_id = %s
                ORDER BY order_index, filename
            """, (lesson_id,))

            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error getting files for lesson: {str(e)}")
            return []
        finally:
            if conn:
                self.return_connection(conn)

    def get_files_by_course(self, course_id):
        """Get all files for a course."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM files
                WHERE course_id = %s
                ORDER BY order_index, filename
            """, (course_id,))

            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error getting files for course: {str(e)}")
            return []
        finally:
            if conn:
                self.return_connection(conn)

    # ==================== PROGRESS METHODS ====================

    def update_file_progress(self, user_id, file_id, lesson_id, course_id,
                            progress_seconds, progress_percentage, completed=False):
        """Update or insert user progress for a specific file."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO user_progress
                    (user_id, file_id, lesson_id, course_id, progress_seconds,
                     progress_percentage, completed, last_watched, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, file_id)
                DO UPDATE SET
                    progress_seconds = EXCLUDED.progress_seconds,
                    progress_percentage = EXCLUDED.progress_percentage,
                    completed = EXCLUDED.completed,
                    last_watched = EXCLUDED.last_watched,
                    updated_at = EXCLUDED.updated_at
            """, (user_id, file_id, lesson_id, course_id, progress_seconds,
                  progress_percentage, completed, datetime.now(), datetime.now()))

            conn.commit()
            cursor.close()

            # Update aggregated course and lesson progress
            self._update_lesson_progress(user_id, lesson_id, course_id)
            self._update_course_progress(user_id, course_id)

            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating file progress: {str(e)}")
            return False
        finally:
            if conn:
                self.return_connection(conn)

    def get_file_progress(self, user_id, file_id):
        """Get progress for a specific file."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM user_progress
                WHERE user_id = %s AND file_id = %s
            """, (user_id, file_id))

            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting file progress: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_course_progress(self, user_id, course_id):
        """Get aggregated progress for a course."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM course_progress
                WHERE user_id = %s AND course_id = %s
            """, (user_id, course_id))

            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting course progress: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def _update_lesson_progress(self, user_id, lesson_id, course_id):
        """Update aggregated lesson progress based on file progress."""
        if not lesson_id:
            return

        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total_files,
                    SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) as completed_files
                FROM user_progress
                WHERE user_id = %s AND lesson_id = %s
            """, (user_id, lesson_id))

            result = cursor.fetchone()
            total_files = result[0] if result[0] else 0
            completed_files = result[1] if result[1] else 0
            progress_pct = (completed_files / total_files * 100) if total_files > 0 else 0

            cursor.execute("""
                INSERT INTO lesson_progress
                    (user_id, lesson_id, course_id, total_files, completed_files,
                     progress_percentage, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, lesson_id)
                DO UPDATE SET
                    total_files = EXCLUDED.total_files,
                    completed_files = EXCLUDED.completed_files,
                    progress_percentage = EXCLUDED.progress_percentage,
                    last_updated = EXCLUDED.last_updated
            """, (user_id, lesson_id, course_id, total_files, completed_files,
                  progress_pct, datetime.now()))

            conn.commit()
            cursor.close()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating lesson progress: {str(e)}")
        finally:
            if conn:
                self.return_connection(conn)

    def _update_course_progress(self, user_id, course_id):
        """Update aggregated course progress based on file progress."""
        if not course_id:
            return

        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total_files,
                    SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) as completed_files,
                    SUM(progress_seconds) as watched_duration
                FROM user_progress
                WHERE user_id = %s AND course_id = %s
            """, (user_id, course_id))

            result = cursor.fetchone()
            total_files = result[0] if result[0] else 0
            completed_files = result[1] if result[1] else 0
            watched_duration = result[2] if result[2] else 0
            progress_pct = (completed_files / total_files * 100) if total_files > 0 else 0

            cursor.execute("""
                INSERT INTO course_progress
                    (user_id, course_id, total_files, completed_files,
                     watched_duration, progress_percentage, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, course_id)
                DO UPDATE SET
                    total_files = EXCLUDED.total_files,
                    completed_files = EXCLUDED.completed_files,
                    watched_duration = EXCLUDED.watched_duration,
                    progress_percentage = EXCLUDED.progress_percentage,
                    last_updated = EXCLUDED.last_updated
            """, (user_id, course_id, total_files, completed_files,
                  watched_duration, progress_pct, datetime.now()))

            conn.commit()
            cursor.close()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating course progress: {str(e)}")
        finally:
            if conn:
                self.return_connection(conn)

    # ==================== SCAN HISTORY ====================

    def record_scan(self, scan_path, files_found, courses_added, lessons_added,
                   scan_duration, status='completed'):
        """Record a folder scan in history."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO scan_history
                    (scan_path, files_found, courses_added, lessons_added,
                     scan_duration, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (scan_path, files_found, courses_added, lessons_added,
                  scan_duration, status))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            return result[0] if result else None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error recording scan: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_scan_history(self, limit=10):
        """Get recent scan history."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM scan_history
                ORDER BY scan_timestamp DESC
                LIMIT %s
            """, (limit,))

            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error getting scan history: {str(e)}")
            return []
        finally:
            if conn:
                self.return_connection(conn)

    def close_all_connections(self):
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("All database connections closed")


# Singleton instance
enhanced_db_service = None

def get_enhanced_db_service():
    """Get or create the enhanced database service singleton."""
    global enhanced_db_service
    if enhanced_db_service is None:
        enhanced_db_service = EnhancedDatabaseService()
    return enhanced_db_service

"""
Local PostgreSQL database service for user progress tracking.
This service manages user progress data using a relational database.
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    PostgreSQL database service for managing user progress.
    Uses connection pooling for efficient database connections.
    """

    def __init__(self):
        """Initialize database connection pool."""
        self.connection_pool = None
        self.initialize_pool()

    def initialize_pool(self):
        """Create connection pool to PostgreSQL database."""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # minimum connections
                10,  # maximum connections
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'streaming_service'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
            logger.info("Database connection pool created successfully")
            self.initialize_schema()
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

            # User activity log - optional: track user learning activity
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_activity_log (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(128) NOT NULL,
                    file_id VARCHAR(128),
                    lesson_id VARCHAR(128),
                    course_id VARCHAR(128),
                    activity_type VARCHAR(50),
                    duration_seconds INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_progress_user_id
                ON user_progress(user_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_progress_course_id
                ON user_progress(course_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_course_progress_user_id
                ON course_progress(user_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lesson_progress_user_id
                ON lesson_progress(user_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_log_user_id
                ON user_activity_log(user_id)
            """)

            conn.commit()
            cursor.close()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error initializing schema: {str(e)}")
            raise
        finally:
            if conn:
                self.return_connection(conn)

    def update_file_progress(self, user_id, file_id, lesson_id, course_id,
                            progress_seconds, progress_percentage, completed=False):
        """
        Update or insert user progress for a specific file.

        Args:
            user_id: Firebase user ID
            file_id: File identifier
            lesson_id: Lesson identifier
            course_id: Course identifier
            progress_seconds: Current playback position in seconds
            progress_percentage: Percentage of file completed
            completed: Whether the file is marked as completed
        """
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

    def get_lesson_progress(self, user_id, lesson_id):
        """Get progress for a specific lesson."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM lesson_progress
                WHERE user_id = %s AND lesson_id = %s
            """, (user_id, lesson_id))

            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting lesson progress: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def get_all_user_progress(self, user_id):
        """Get all progress data for a user."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM user_progress
                WHERE user_id = %s
                ORDER BY last_watched DESC
            """, (user_id,))

            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error getting user progress: {str(e)}")
            return []
        finally:
            if conn:
                self.return_connection(conn)

    def get_user_courses_progress(self, user_id):
        """Get all course progress for a user."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM course_progress
                WHERE user_id = %s
                ORDER BY last_updated DESC
            """, (user_id,))

            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error getting user courses progress: {str(e)}")
            return []
        finally:
            if conn:
                self.return_connection(conn)

    def log_activity(self, user_id, file_id=None, lesson_id=None, course_id=None,
                     activity_type='view', duration_seconds=0):
        """Log user activity for analytics."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO user_activity_log
                    (user_id, file_id, lesson_id, course_id, activity_type, duration_seconds)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, file_id, lesson_id, course_id, activity_type, duration_seconds))

            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error logging activity: {str(e)}")
            return False
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

            # Calculate lesson progress from file progress
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

            # Calculate course progress from file progress
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

    def close_all_connections(self):
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("All database connections closed")


# Singleton instance
db_service = None

def get_db_service():
    """Get or create the database service singleton."""
    global db_service
    if db_service is None:
        db_service = DatabaseService()
    return db_service

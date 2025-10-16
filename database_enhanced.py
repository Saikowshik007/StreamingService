import sqlite3
from config import Config
from datetime import datetime

def init_enhanced_db():
    """Initialize enhanced database with file tracking"""
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()

    # Courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            instructor TEXT,
            thumbnail TEXT,
            folder_path TEXT UNIQUE,
            total_files INTEGER DEFAULT 0,
            total_duration INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Lessons table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            folder_path TEXT,
            order_index INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    ''')

    # Files table - tracks all video and document files
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT UNIQUE NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER,
            duration INTEGER,
            order_index INTEGER,
            is_video BOOLEAN DEFAULT 0,
            is_document BOOLEAN DEFAULT 0,
            thumbnail_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    ''')

    # Add thumbnail_path column if it doesn't exist (for existing databases)
    try:
        cursor.execute("SELECT thumbnail_path FROM files LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE files ADD COLUMN thumbnail_path TEXT")

    # User progress table - tracks progress for each file
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default_user',
            file_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            progress_seconds INTEGER DEFAULT 0,
            progress_percentage REAL DEFAULT 0,
            completed BOOLEAN DEFAULT 0,
            last_watched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            UNIQUE(user_id, file_id)
        )
    ''')

    # Course progress summary
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS course_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default_user',
            course_id INTEGER NOT NULL,
            total_files INTEGER DEFAULT 0,
            completed_files INTEGER DEFAULT 0,
            total_duration INTEGER DEFAULT 0,
            watched_duration INTEGER DEFAULT 0,
            progress_percentage REAL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            UNIQUE(user_id, course_id)
        )
    ''')

    # Folder scan history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_path TEXT NOT NULL,
            files_found INTEGER DEFAULT 0,
            courses_added INTEGER DEFAULT 0,
            lessons_added INTEGER DEFAULT 0,
            scan_duration REAL,
            scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT
        )
    ''')

    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_lesson ON files(lesson_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_course ON files(course_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_user ON user_progress(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_file ON user_progress(file_id)')

    conn.commit()
    conn.close()
    print("Enhanced database initialized successfully!")

def get_db():
    """Get database connection with row factory"""
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_course_stats(course_id, user_id='default_user'):
    """Get statistics for a course"""
    conn = get_db()
    cursor = conn.cursor()

    # Get total files and duration
    cursor.execute('''
        SELECT COUNT(*) as total_files,
               SUM(duration) as total_duration,
               SUM(CASE WHEN is_video = 1 THEN 1 ELSE 0 END) as video_count,
               SUM(CASE WHEN is_document = 1 THEN 1 ELSE 0 END) as document_count
        FROM files WHERE course_id = ?
    ''', (course_id,))
    stats = dict(cursor.fetchone())

    # Get completed files
    cursor.execute('''
        SELECT COUNT(*) as completed_files,
               SUM(progress_seconds) as watched_duration
        FROM user_progress
        WHERE course_id = ? AND user_id = ? AND completed = 1
    ''', (course_id, user_id))
    progress = dict(cursor.fetchone())

    conn.close()

    return {**stats, **progress}

def update_course_progress(course_id, user_id='default_user'):
    """Recalculate and update course progress"""
    conn = get_db()
    cursor = conn.cursor()

    stats = get_course_stats(course_id, user_id)

    progress_percentage = 0
    if stats['total_files'] > 0:
        progress_percentage = (stats.get('completed_files', 0) / stats['total_files']) * 100

    # Update or insert course progress
    cursor.execute('''
        INSERT INTO course_progress
        (user_id, course_id, total_files, completed_files, total_duration, watched_duration, progress_percentage, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, course_id) DO UPDATE SET
            total_files = excluded.total_files,
            completed_files = excluded.completed_files,
            total_duration = excluded.total_duration,
            watched_duration = excluded.watched_duration,
            progress_percentage = excluded.progress_percentage,
            last_updated = CURRENT_TIMESTAMP
    ''', (user_id, course_id, stats['total_files'], stats.get('completed_files', 0),
          stats.get('total_duration', 0), stats.get('watched_duration', 0), progress_percentage))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_enhanced_db()

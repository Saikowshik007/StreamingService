import sqlite3
from config import Config

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()

    # Create courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            instructor TEXT,
            thumbnail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create lessons table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            video_path TEXT,
            duration INTEGER,
            order_index INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')

    # Create resources table (for documents)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id)
        )
    ''')

    # Create user_progress table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            lesson_id INTEGER NOT NULL,
            progress INTEGER DEFAULT 0,
            completed BOOLEAN DEFAULT 0,
            last_watched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id)
        )
    ''')

    conn.commit()
    conn.close()

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_sample_data():
    """Add sample data for testing"""
    conn = get_db()
    cursor = conn.cursor()

    # Check if sample data already exists
    cursor.execute('SELECT COUNT(*) FROM courses')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Add sample course
    cursor.execute('''
        INSERT INTO courses (title, description, instructor, thumbnail)
        VALUES (?, ?, ?, ?)
    ''', ('Sample Course', 'This is a sample course to get you started', 'Instructor Name', ''))

    course_id = cursor.lastrowid

    # Add sample lesson
    cursor.execute('''
        INSERT INTO lessons (course_id, title, description, video_path, order_index)
        VALUES (?, ?, ?, ?, ?)
    ''', (course_id, 'Introduction', 'Welcome to the course', 'sample.mp4', 1))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    add_sample_data()
    print("Database initialized successfully!")

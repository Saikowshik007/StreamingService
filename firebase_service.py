"""
Firebase service module to replace SQLite database operations
Collections structure:
- courses: {id, title, description, instructor, thumbnail, folder_path, total_files, created_at, updated_at}
- lessons: {id, course_id, title, description, folder_path, order_index, created_at}
- files: {id, lesson_id, course_id, filename, file_path, file_type, file_size, duration, order_index, is_video, is_document, thumbnail_base64, created_at}
- user_progress: {id, user_id, file_id, lesson_id, course_id, progress_seconds, progress_percentage, completed, last_watched}
- course_progress: {id, user_id, course_id, total_files, completed_files, total_duration, watched_duration, progress_percentage, last_updated}
- scan_history: {id, scan_path, files_found, courses_added, lessons_added, scan_duration, scan_timestamp, status}
"""

from firebase_config import get_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def init_firebase():
    """Initialize Firebase (no need to create tables like SQL)"""
    try:
        db = get_db()
        logger.info("Firebase connection established")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        return False

# Course Operations
def create_course(title, description=None, instructor=None, folder_path=None, total_files=0):
    """Create a new course"""
    db = get_db()
    course_data = {
        'title': title,
        'description': description or f'Auto-imported from {folder_path}',
        'instructor': instructor or 'Unknown',
        'thumbnail': None,
        'folder_path': folder_path,
        'total_files': total_files,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    doc_ref = db.collection('courses').add(course_data)
    return doc_ref[1].id

def get_course_by_folder_path(folder_path):
    """Get course by folder path"""
    db = get_db()
    docs = db.collection('courses').where('folder_path', '==', folder_path).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None

def get_course_by_id(course_id):
    """Get course by ID"""
    db = get_db()
    doc = db.collection('courses').document(course_id).get()
    if doc.exists:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None

def update_course(course_id, **kwargs):
    """Update course fields"""
    db = get_db()
    kwargs['updated_at'] = datetime.utcnow()
    db.collection('courses').document(course_id).update(kwargs)

def get_all_courses(user_id='default_user'):
    """Get all courses with progress"""
    db = get_db()
    courses = []

    try:
        # Try to order by created_at (requires index in Firestore)
        query = db.collection('courses').order_by('created_at', direction='DESCENDING')
    except Exception as e:
        logger.warning(f"Failed to order by created_at, using default order: {str(e)}")
        # Fall back to no ordering if index doesn't exist
        query = db.collection('courses')

    for doc in query.stream():
        course = doc.to_dict()
        course['id'] = doc.id

        # Get progress
        try:
            progress = get_course_progress(course['id'], user_id)
            course['progress_percentage'] = progress.get('progress_percentage', 0)
            course['completed_files'] = progress.get('completed_files', 0)
            course['progress_total_files'] = progress.get('total_files', 0)
        except Exception as e:
            logger.error(f"Error getting progress for course {course['id']}: {str(e)}")
            course['progress_percentage'] = 0
            course['completed_files'] = 0
            course['progress_total_files'] = 0

        courses.append(course)

    return courses

# Lesson Operations
def create_lesson(course_id, title, folder_path=None, order_index=0, description=None):
    """Create a new lesson"""
    db = get_db()
    lesson_data = {
        'course_id': course_id,
        'title': title,
        'description': description,
        'folder_path': folder_path,
        'order_index': order_index,
        'created_at': datetime.utcnow()
    }
    doc_ref = db.collection('lessons').add(lesson_data)
    return doc_ref[1].id

def get_lesson_by_folder_path(course_id, folder_path):
    """Get lesson by course_id and folder path"""
    db = get_db()
    docs = db.collection('lessons').where('course_id', '==', course_id).where('folder_path', '==', folder_path).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None

def get_lesson_by_id(lesson_id, user_id='default_user'):
    """Get lesson by ID with files"""
    db = get_db()
    doc = db.collection('lessons').document(lesson_id).get()
    if not doc.exists:
        return None

    lesson = doc.to_dict()
    lesson['id'] = doc.id

    # Get files with progress
    lesson['files'] = get_files_by_lesson(lesson_id, user_id)

    return lesson

def get_lessons_by_course(course_id, user_id='default_user'):
    """Get all lessons for a course"""
    db = get_db()
    lessons = []

    try:
        query = db.collection('lessons').where('course_id', '==', course_id).order_by('order_index')
    except Exception as e:
        logger.warning(f"Failed to order lessons, using default order: {str(e)}")
        query = db.collection('lessons').where('course_id', '==', course_id)

    for doc in query.stream():
        lesson = doc.to_dict()
        lesson['id'] = doc.id

        # Get file counts
        files = get_files_by_lesson(lesson['id'], user_id)
        lesson['file_count'] = len(files)
        lesson['video_count'] = sum(1 for f in files if f.get('is_video'))
        lesson['document_count'] = sum(1 for f in files if f.get('is_document'))
        lesson['files'] = files

        lessons.append(lesson)

    return lessons

# File Operations
def create_file(lesson_id, course_id, filename, file_path, file_type, file_size, is_video, is_document, order_index=0, duration=None, thumbnail_base64=None):
    """Create a new file"""
    db = get_db()
    file_data = {
        'lesson_id': lesson_id,
        'course_id': course_id,
        'filename': filename,
        'file_path': file_path,
        'file_type': file_type,
        'file_size': file_size,
        'duration': duration,
        'order_index': order_index,
        'is_video': is_video,
        'is_document': is_document,
        'thumbnail_base64': thumbnail_base64,
        'created_at': datetime.utcnow(),
        'last_scanned': datetime.utcnow()
    }
    doc_ref = db.collection('files').add(file_data)
    return doc_ref[1].id

def get_file_by_path(file_path):
    """Get file by file path"""
    db = get_db()
    docs = db.collection('files').where('file_path', '==', file_path).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None

def get_file_by_id(file_id, user_id='default_user'):
    """Get file by ID with progress"""
    db = get_db()
    doc = db.collection('files').document(file_id).get()
    if not doc.exists:
        return None

    file_data = doc.to_dict()
    file_data['id'] = doc.id

    # Get progress
    progress = get_user_progress(user_id, file_id)
    if progress:
        file_data['progress_seconds'] = progress.get('progress_seconds', 0)
        file_data['progress_percentage'] = progress.get('progress_percentage', 0)
        file_data['completed'] = progress.get('completed', False)

    return file_data

def update_file(file_id, **kwargs):
    """Update file fields"""
    db = get_db()
    kwargs['last_scanned'] = datetime.utcnow()
    db.collection('files').document(file_id).update(kwargs)

def get_files_by_lesson(lesson_id, user_id='default_user'):
    """Get all files for a lesson"""
    db = get_db()
    files = []

    try:
        query = db.collection('files').where('lesson_id', '==', lesson_id).order_by('order_index')
    except Exception as e:
        logger.warning(f"Failed to order files, using default order: {str(e)}")
        query = db.collection('files').where('lesson_id', '==', lesson_id)

    for doc in query.stream():
        file_data = doc.to_dict()
        file_data['id'] = doc.id

        # Get progress
        progress = get_user_progress(user_id, file_data['id'])
        if progress:
            file_data['progress_seconds'] = progress.get('progress_seconds', 0)
            file_data['progress_percentage'] = progress.get('progress_percentage', 0)
            file_data['completed'] = progress.get('completed', False)
        else:
            file_data['progress_seconds'] = 0
            file_data['progress_percentage'] = 0
            file_data['completed'] = False

        files.append(file_data)

    return files

def get_all_video_files_without_thumbnails():
    """Get all video files that don't have thumbnails"""
    db = get_db()
    files = []

    # Query for videos where thumbnail_base64 is None or doesn't exist
    for doc in db.collection('files').where('is_video', '==', True).stream():
        file_data = doc.to_dict()
        if not file_data.get('thumbnail_base64'):
            file_data['id'] = doc.id
            files.append(file_data)

    return files

# User Progress Operations
def update_user_progress(user_id, file_id, lesson_id, course_id, progress_seconds, progress_percentage, completed):
    """Update or create user progress"""
    db = get_db()

    # Check if progress exists
    docs = db.collection('user_progress').where('user_id', '==', user_id).where('file_id', '==', file_id).limit(1).stream()

    progress_data = {
        'user_id': user_id,
        'file_id': file_id,
        'lesson_id': lesson_id,
        'course_id': course_id,
        'progress_seconds': progress_seconds,
        'progress_percentage': progress_percentage,
        'completed': completed,
        'last_watched': datetime.utcnow()
    }

    existing_doc = None
    for doc in docs:
        existing_doc = doc
        break

    if existing_doc:
        db.collection('user_progress').document(existing_doc.id).update(progress_data)
    else:
        db.collection('user_progress').add(progress_data)

    # Update course progress
    update_course_progress(course_id, user_id)

def get_user_progress(user_id, file_id):
    """Get user progress for a file"""
    db = get_db()
    docs = db.collection('user_progress').where('user_id', '==', user_id).where('file_id', '==', file_id).limit(1).stream()

    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None

# Course Progress Operations
def get_course_progress(course_id, user_id='default_user'):
    """Get course progress for a user"""
    db = get_db()
    docs = db.collection('course_progress').where('user_id', '==', user_id).where('course_id', '==', course_id).limit(1).stream()

    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        return data

    return {'progress_percentage': 0, 'completed_files': 0, 'total_files': 0}

def update_course_progress(course_id, user_id='default_user'):
    """Recalculate and update course progress"""
    db = get_db()

    # Get all files in the course
    total_files = 0
    total_duration = 0
    for doc in db.collection('files').where('course_id', '==', course_id).stream():
        total_files += 1
        file_data = doc.to_dict()
        if file_data.get('duration'):
            total_duration += file_data['duration']

    # Get completed files
    completed_files = 0
    watched_duration = 0
    for doc in db.collection('user_progress').where('user_id', '==', user_id).where('course_id', '==', course_id).where('completed', '==', True).stream():
        completed_files += 1
        progress_data = doc.to_dict()
        if progress_data.get('progress_seconds'):
            watched_duration += progress_data['progress_seconds']

    progress_percentage = 0
    if total_files > 0:
        progress_percentage = (completed_files / total_files) * 100

    # Check if progress record exists
    docs = db.collection('course_progress').where('user_id', '==', user_id).where('course_id', '==', course_id).limit(1).stream()

    progress_data = {
        'user_id': user_id,
        'course_id': course_id,
        'total_files': total_files,
        'completed_files': completed_files,
        'total_duration': total_duration,
        'watched_duration': watched_duration,
        'progress_percentage': progress_percentage,
        'last_updated': datetime.utcnow()
    }

    existing_doc = None
    for doc in docs:
        existing_doc = doc
        break

    if existing_doc:
        db.collection('course_progress').document(existing_doc.id).update(progress_data)
    else:
        db.collection('course_progress').add(progress_data)

# Scan History Operations
def add_scan_history(scan_path, files_found, courses_added, lessons_added, scan_duration, status):
    """Add scan history record"""
    db = get_db()
    history_data = {
        'scan_path': scan_path,
        'files_found': files_found,
        'courses_added': courses_added,
        'lessons_added': lessons_added,
        'scan_duration': scan_duration,
        'scan_timestamp': datetime.utcnow(),
        'status': status
    }
    db.collection('scan_history').add(history_data)

def get_scan_history(limit=10):
    """Get recent scan history"""
    db = get_db()
    history = []

    try:
        query = db.collection('scan_history').order_by('scan_timestamp', direction='DESCENDING').limit(limit)
    except Exception as e:
        logger.warning(f"Failed to order scan history, using default order: {str(e)}")
        query = db.collection('scan_history').limit(limit)

    for doc in query.stream():
        data = doc.to_dict()
        data['id'] = doc.id
        history.append(data)

    return history

# Statistics
def get_stats():
    """Get overall statistics"""
    db = get_db()

    stats = {
        'courses': len(list(db.collection('courses').stream())),
        'lessons': len(list(db.collection('lessons').stream())),
        'files': len(list(db.collection('files').stream())),
        'videos': len(list(db.collection('files').where('is_video', '==', True).stream())),
        'documents': len(list(db.collection('files').where('is_document', '==', True).stream()))
    }

    return stats

if __name__ == '__main__':
    init_firebase()
    print("Firebase service initialized successfully!")

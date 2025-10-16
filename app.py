from flask import Flask, request, send_file, jsonify, Response, Blueprint
from flask_cors import CORS
import os
import mimetypes
import logging
import atexit
from pathlib import Path
from config import Config
from database_enhanced import (
    init_enhanced_db, get_db, get_course_stats,
    update_course_progress
)
from folder_scanner import scan_and_import
from folder_watcher import start_watcher, stop_watcher, get_watcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Create a blueprint with /learn prefix to match Traefik routing
# This handles both cases: with and without Traefik stripprefix
api_bp = Blueprint('api', __name__, url_prefix='/learn')

def get_allowed_origins():
    """Get the list of allowed CORS origins."""
    origins = [
        # Production origins - EXACT MATCHES
        "https://streaming-service.vercel.app",
        "https://jobtrackai.duckdns.org",
        "http://jobtrackai.duckdns.org",

        # Development origins
        "http://localhost",
        "https://localhost",
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",

        # NULL origin for direct requests
        "null",
    ]

    # Add debug origins if in debug mode
    if os.environ.get('FLASK_DEBUG') or os.environ.get('DEBUG'):
        debug_origins = [
            "http://localhost:3001",
            "http://localhost:3002",
        ]
        origins.extend(debug_origins)

    # Add any additional origins from environment variable
    env_origins = os.environ.get('ADDITIONAL_CORS_ORIGINS', '')
    if env_origins:
        additional_origins = [origin.strip() for origin in env_origins.split(',')]
        origins.extend(additional_origins)

    logger.info(f"CORS allowed origins: {origins}")
    return origins

# Configure CORS with comprehensive settings
CORS(app,
    resources={
        r"/*": {
            "origins": get_allowed_origins(),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
            "allow_headers": [
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "Cache-Control",
                "DNT",
                "If-Modified-Since",
                "Keep-Alive",
                "Origin",
                "User-Agent",
                "X-Requested-With",
                "Range",
                "Referer",
                "X-Api-Key",
                "x-api-key",
                "X-CSRF-Token",
                "X-Forwarded-For",
                "X-Forwarded-Proto",
                "X-Real-IP",
                "X-Vercel-Id",
                "X-Deployment-Id",
            ],
            "expose_headers": [
                "Content-Range",
                "Accept-Ranges",
                "Content-Length",
                "X-Content-Range",
                "X-Total-Count",
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Credentials"
            ],
            "supports_credentials": True,
            "max_age": 3600
        }
    }
)

# Initialize database
init_enhanced_db()

# Start automatic folder watcher
logger.info("Starting automatic folder watcher...")
start_watcher()

# Register cleanup on exit
atexit.register(stop_watcher)


@api_bp.route('/api/courses', methods=['GET'])
def get_courses():
    """Get all courses with progress"""
    user_id = request.args.get('user_id', 'default_user')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.*,
               cp.progress_percentage,
               cp.completed_files,
               cp.total_files as progress_total_files
        FROM courses c
        LEFT JOIN course_progress cp ON c.id = cp.course_id AND cp.user_id = ?
        ORDER BY c.created_at DESC
    ''', (user_id,))

    courses = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(courses)

@api_bp.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """Get a specific course with lessons and files"""
    user_id = request.args.get('user_id', 'default_user')

    conn = get_db()
    cursor = conn.cursor()

    # Get course
    cursor.execute('''
        SELECT c.*,
               cp.progress_percentage,
               cp.completed_files,
               cp.total_files as progress_total_files
        FROM courses c
        LEFT JOIN course_progress cp ON c.id = cp.course_id AND cp.user_id = ?
        WHERE c.id = ?
    ''', (user_id, course_id))

    course = cursor.fetchone()
    if not course:
        conn.close()
        return jsonify({'error': 'Course not found'}), 404

    course_dict = dict(course)

    # Get lessons with their files
    cursor.execute('''
        SELECT l.*,
               COUNT(f.id) as file_count,
               SUM(CASE WHEN f.is_video = 1 THEN 1 ELSE 0 END) as video_count,
               SUM(CASE WHEN f.is_document = 1 THEN 1 ELSE 0 END) as document_count
        FROM lessons l
        LEFT JOIN files f ON l.id = f.lesson_id
        WHERE l.course_id = ?
        GROUP BY l.id
        ORDER BY l.order_index
    ''', (course_id,))

    lessons = []
    for lesson_row in cursor.fetchall():
        lesson = dict(lesson_row)

        # Get files for this lesson
        cursor.execute('''
            SELECT f.*,
                   up.progress_seconds,
                   up.progress_percentage,
                   up.completed
            FROM files f
            LEFT JOIN user_progress up ON f.id = up.file_id AND up.user_id = ?
            WHERE f.lesson_id = ?
            ORDER BY f.order_index, f.filename
        ''', (user_id, lesson['id']))

        lesson['files'] = [dict(row) for row in cursor.fetchall()]
        lessons.append(lesson)

    course_dict['lessons'] = lessons
    conn.close()

    return jsonify(course_dict)

@api_bp.route('/api/lessons/<int:lesson_id>', methods=['GET'])
def get_lesson(lesson_id):
    """Get a specific lesson with files"""
    user_id = request.args.get('user_id', 'default_user')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,))
    lesson = cursor.fetchone()

    if not lesson:
        conn.close()
        return jsonify({'error': 'Lesson not found'}), 404

    lesson_dict = dict(lesson)

    # Get files with progress
    cursor.execute('''
        SELECT f.*,
               up.progress_seconds,
               up.progress_percentage,
               up.completed
        FROM files f
        LEFT JOIN user_progress up ON f.id = up.file_id AND up.user_id = ?
        WHERE f.lesson_id = ?
        ORDER BY f.order_index, f.filename
    ''', (user_id, lesson_id))

    lesson_dict['files'] = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(lesson_dict)

@api_bp.route('/api/file/<int:file_id>', methods=['GET'])
def get_file_info(file_id):
    """Get file information"""
    user_id = request.args.get('user_id', 'default_user')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT f.*,
               up.progress_seconds,
               up.progress_percentage,
               up.completed
        FROM files f
        LEFT JOIN user_progress up ON f.id = up.file_id AND up.user_id = ?
        WHERE f.id = ?
    ''', (user_id, file_id))

    file = cursor.fetchone()
    conn.close()

    if not file:
        return jsonify({'error': 'File not found'}), 404

    return jsonify(dict(file))

@api_bp.route('/api/stream/<int:file_id>', methods=['GET'])
def stream_file(file_id):
    """Stream video file with range request support"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT file_path FROM files WHERE id = ? AND is_video = 1', (file_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({'error': 'Video file not found'}), 404

    video_path = os.path.join(Config.MEDIA_PATH, result['file_path'])

    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file not found on disk'}), 404

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)

    # Define chunk size for streaming (1MB)
    CHUNK_SIZE = 1024 * 1024

    # Parse range header
    byte_start = 0
    byte_end = file_size - 1

    if range_header:
        range_match = range_header.replace('bytes=', '').split('-')
        byte_start = int(range_match[0]) if range_match[0] else 0
        byte_end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else byte_end

    length = byte_end - byte_start + 1

    def generate():
        """Generator to stream file in chunks"""
        with open(video_path, 'rb') as video_file:
            video_file.seek(byte_start)
            remaining = length
            while remaining > 0:
                chunk_size = min(CHUNK_SIZE, remaining)
                data = video_file.read(chunk_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = Response(generate(), 206 if range_header else 200, mimetype='video/mp4')
    response.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
    response.headers.add('Accept-Ranges', 'bytes')
    response.headers.add('Content-Length', str(length))
    response.headers.add('Cache-Control', 'public, max-age=3600')

    return response

@api_bp.route('/api/document/<int:file_id>', methods=['GET'])
def get_document(file_id):
    """Serve document files"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT file_path, filename FROM files WHERE id = ? AND is_document = 1', (file_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({'error': 'Document not found'}), 404

    file_path = os.path.join(Config.MEDIA_PATH, result['file_path'])

    if not os.path.exists(file_path):
        return jsonify({'error': 'Document file not found on disk'}), 404

    mimetype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    return send_file(file_path, mimetype=mimetype, as_attachment=False)

@api_bp.route('/api/progress', methods=['POST'])
def update_progress():
    """Update user progress for a file"""
    data = request.json
    user_id = data.get('user_id', 'default_user')
    file_id = data.get('file_id')
    progress_seconds = data.get('progress_seconds', 0)
    progress_percentage = data.get('progress_percentage', 0)
    completed = data.get('completed', False)

    conn = get_db()
    cursor = conn.cursor()

    # Get file info
    cursor.execute('SELECT lesson_id, course_id FROM files WHERE id = ?', (file_id,))
    file_info = cursor.fetchone()

    if not file_info:
        conn.close()
        return jsonify({'error': 'File not found'}), 404

    # Update or insert progress
    cursor.execute('''
        INSERT INTO user_progress
        (user_id, file_id, lesson_id, course_id, progress_seconds, progress_percentage, completed, last_watched)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, file_id) DO UPDATE SET
            progress_seconds = excluded.progress_seconds,
            progress_percentage = excluded.progress_percentage,
            completed = excluded.completed,
            last_watched = CURRENT_TIMESTAMP
    ''', (user_id, file_id, file_info['lesson_id'], file_info['course_id'],
          progress_seconds, progress_percentage, completed))

    conn.commit()
    conn.close()

    # Update course progress
    update_course_progress(file_info['course_id'], user_id)

    return jsonify({'success': True})

@api_bp.route('/api/progress/course/<int:course_id>', methods=['GET'])
def get_course_progress(course_id):
    """Get course progress for a user"""
    user_id = request.args.get('user_id', 'default_user')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM course_progress
        WHERE user_id = ? AND course_id = ?
    ''', (user_id, course_id))

    result = cursor.fetchone()
    conn.close()

    if result:
        return jsonify(dict(result))
    else:
        return jsonify({'progress_percentage': 0, 'completed_files': 0})

@api_bp.route('/api/scan', methods=['POST'])
def scan_folders():
    """Trigger a folder scan"""
    data = request.json or {}
    scan_path = data.get('path', Config.MEDIA_PATH)
    rescan = data.get('rescan', False)

    try:
        success = scan_and_import(scan_path, rescan)
        if success:
            return jsonify({'success': True, 'message': 'Scan completed successfully'})
        else:
            return jsonify({'success': False, 'message': 'Scan failed'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/api/scan/history', methods=['GET'])
def get_scan_history():
    """Get scan history"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM scan_history ORDER BY scan_timestamp DESC LIMIT 10')
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(history)

@api_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as total_courses FROM courses')
    courses_count = cursor.fetchone()['total_courses']

    cursor.execute('SELECT COUNT(*) as total_lessons FROM lessons')
    lessons_count = cursor.fetchone()['total_lessons']

    cursor.execute('SELECT COUNT(*) as total_files FROM files')
    files_count = cursor.fetchone()['total_files']

    cursor.execute('SELECT COUNT(*) as total_videos FROM files WHERE is_video = 1')
    videos_count = cursor.fetchone()['total_videos']

    cursor.execute('SELECT COUNT(*) as total_documents FROM files WHERE is_document = 1')
    documents_count = cursor.fetchone()['total_documents']

    conn.close()

    return jsonify({
        'courses': courses_count,
        'lessons': lessons_count,
        'files': files_count,
        'videos': videos_count,
        'documents': documents_count
    })

@api_bp.route('/api/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'media_path': Config.MEDIA_PATH,
        'db_path': Config.DB_PATH,
        'cors_enabled': True,
        'version': '1.0.0'
    })

@api_bp.route('/api/cors-test', methods=['GET'])
def cors_test():
    """Test endpoint specifically for CORS debugging"""
    return jsonify({
        'message': 'CORS test successful',
        'origin_allowed': True,
        'cors_origins': get_allowed_origins(),
        'status': 'ok'
    })

@api_bp.route('/api/watcher/status', methods=['GET'])
def watcher_status():
    """Check folder watcher status"""
    watcher = get_watcher()
    return jsonify({
        'active': watcher.is_active(),
        'watch_path': watcher.watch_path,
        'auto_scan_enabled': True
    })

# Register the blueprint
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)

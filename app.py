from flask import Flask, request, send_file, jsonify, Response, Blueprint
from flask_cors import CORS
import os
import time
import mimetypes
import logging
import atexit
from pathlib import Path
from config import Config
from db_adapter import get_db_adapter
from folder_scanner import scan_and_import
from folder_watcher import start_watcher, stop_watcher, get_watcher
from thumbnail_generator import generate_thumbnail_for_file, check_ffmpeg
from auth_service import require_auth, optional_auth
from url_signer import generate_signed_url, verify_signed_url, parse_signed_params
from cache_service import get_cache
from progress_sync_worker import start_progress_sync_worker, stop_progress_sync_worker
from database import get_db_service
import firebase_service  # Still needed for Firebase auth initialization

# Initialize database adapter (PostgreSQL primary, no Firebase fallback)
db = get_db_adapter(use_postgres=True, use_firebase_fallback=False)

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

# Initialize Firebase (still needed for authentication)
logger.info("Initializing Firebase for authentication...")
firebase_service.init_firebase()

# Start automatic folder watcher
logger.info("Starting automatic folder watcher...")
start_watcher()

# Start progress sync worker (Redis -> Firebase every 30 seconds)
logger.info("Starting progress sync worker...")
start_progress_sync_worker(sync_interval=30)

# Register cleanup on exit
atexit.register(stop_watcher)
atexit.register(stop_progress_sync_worker)


@api_bp.route('/api/courses', methods=['GET'])
@require_auth
def get_courses():
    """Get all courses with progress"""
    user_id = request.current_user['uid']
    courses = db.get_all_courses()

    # Add progress information to each course
    for course in courses:
        progress = db.get_course_progress(course['id'], user_id)
        if progress:
            course['progress_percentage'] = progress.get('progress_percentage', 0)
            course['completed_files'] = progress.get('completed_files', 0)
            course['progress_total_files'] = progress.get('total_files', 0)
        else:
            course['progress_percentage'] = 0
            course['completed_files'] = 0
            course['progress_total_files'] = 0

    return jsonify(courses)

@api_bp.route('/api/courses/<course_id>', methods=['GET'])
@require_auth
def get_course(course_id):
    """Get a specific course with lessons and files"""
    user_id = request.current_user['uid']

    course = db.get_course_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    # Get progress
    progress = db.get_course_progress(course_id, user_id)
    if progress:
        course['progress_percentage'] = progress.get('progress_percentage', 0)
        course['completed_files'] = progress.get('completed_files', 0)
        course['progress_total_files'] = progress.get('total_files', 0)
    else:
        course['progress_percentage'] = 0
        course['completed_files'] = 0
        course['progress_total_files'] = 0

    # Get lessons with files
    lessons = db.get_lessons_by_course_id(course_id)

    # Add files to each lesson
    for lesson in lessons:
        lesson['files'] = db.get_files_by_lesson_id(lesson['id'])

        # Add progress to each file
        for file in lesson['files']:
            file_progress = db.get_user_progress(user_id, file['id'])
            if file_progress:
                file['progress_seconds'] = file_progress.get('progress_seconds', 0)
                file['progress_percentage'] = file_progress.get('progress_percentage', 0)
                file['completed'] = file_progress.get('completed', False)
            else:
                file['progress_seconds'] = 0
                file['progress_percentage'] = 0
                file['completed'] = False

    course['lessons'] = lessons

    return jsonify(course)

@api_bp.route('/api/lessons/<lesson_id>', methods=['GET'])
@require_auth
def get_lesson(lesson_id):
    """Get a specific lesson with files"""
    user_id = request.current_user['uid']

    lesson = db.get_lesson_by_id(lesson_id)
    if not lesson:
        return jsonify({'error': 'Lesson not found'}), 404

    # Add files to lesson
    files = db.get_files_by_lesson_id(lesson_id)

    # Add progress to each file
    for file in files:
        file_progress = db.get_user_progress(user_id, file['id'])
        if file_progress:
            file['progress_seconds'] = file_progress.get('progress_seconds', 0)
            file['progress_percentage'] = file_progress.get('progress_percentage', 0)
            file['completed'] = file_progress.get('completed', False)
        else:
            file['progress_seconds'] = 0
            file['progress_percentage'] = 0
            file['completed'] = False

    lesson['files'] = files

    return jsonify(lesson)

@api_bp.route('/api/file/<file_id>', methods=['GET'])
@require_auth
def get_file_info(file_id):
    """Get file information"""
    user_id = request.current_user['uid']

    file = db.get_file_by_id(file_id)
    if not file:
        return jsonify({'error': 'File not found'}), 404

    # Add progress
    file_progress = db.get_user_progress(user_id, file_id)
    if file_progress:
        file['progress_seconds'] = file_progress.get('progress_seconds', 0)
        file['progress_percentage'] = file_progress.get('progress_percentage', 0)
        file['completed'] = file_progress.get('completed', False)
    else:
        file['progress_seconds'] = 0
        file['progress_percentage'] = 0
        file['completed'] = False

    return jsonify(file)

@api_bp.route('/api/stream/signed-url/<file_id>', methods=['GET'])
@require_auth
def get_signed_stream_url(file_id):
    """
    Generate a signed URL for streaming a video file.
    This allows the video player to access the stream without custom headers.
    """
    user_id = request.current_user['uid']

    # Verify the file exists and user has access
    file = db.get_file_by_id(file_id)
    if not file or not file.get('is_video'):
        return jsonify({'error': 'Video file not found'}), 404

    # Generate signed URL parameters
    signature, expiration = generate_signed_url(file_id)

    # Return the signed URL components (without /learn prefix, frontend will add API_URL)
    return jsonify({
        'file_id': file_id,
        'signature': signature,
        'expires': expiration,
        'url': f"/api/stream/{file_id}?signature={signature}&expires={expiration}"
    })

@api_bp.route('/api/stream/<file_id>', methods=['GET'])
@optional_auth
def stream_file(file_id):
    """
    Stream video file with range request support.
    Accepts either:
    1. Bearer token authentication (Authorization header)
    2. Signed URL parameters (signature and expires query params)
    """
    # Check for signed URL parameters first
    signed_params = parse_signed_params(request.args)
    if signed_params:
        signature, expiration = signed_params
        if not verify_signed_url(file_id, signature, expiration):
            return jsonify({'error': 'Invalid or expired signature'}), 401
        # Signed URL is valid, get file without user_id check
        file = db.get_file_by_id(file_id)
    elif hasattr(request, 'current_user') and request.current_user:
        # Bearer token authentication
        user_id = request.current_user['uid']
        file = db.get_file_by_id(file_id)
    else:
        # No authentication provided
        return jsonify({'error': 'Authentication required'}), 401

    if not file or not file.get('is_video'):
        return jsonify({'error': 'Video file not found'}), 404

    video_path = os.path.join(Config.MEDIA_PATH, file['file_path'])

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

@api_bp.route('/api/document/<file_id>', methods=['GET'])
@require_auth
def get_document(file_id):
    """Serve document files"""
    user_id = request.current_user['uid']
    file = db.get_file_by_id(file_id, user_id)

    if not file or not file.get('is_document'):
        return jsonify({'error': 'Document not found'}), 404

    file_path = os.path.join(Config.MEDIA_PATH, file['file_path'])

    if not os.path.exists(file_path):
        return jsonify({'error': 'Document file not found on disk'}), 404

    mimetype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    return send_file(file_path, mimetype=mimetype, as_attachment=False)

@api_bp.route('/api/thumbnail/<file_id>', methods=['GET'])
def get_thumbnail(file_id):
    """Return thumbnail base64 data for a video file"""
    file = db.get_file_by_id(file_id)

    if not file:
        return jsonify({'error': 'File not found'}), 404

    thumbnail_base64 = file.get('thumbnail_base64')
    if not thumbnail_base64:
        return jsonify({'error': 'Thumbnail not available'}), 404

    # Return the base64 data (already includes data:image/jpeg;base64, prefix)
    return jsonify({'thumbnail': thumbnail_base64})

@api_bp.route('/api/progress', methods=['POST'])
@require_auth
def update_progress_endpoint():
    """Update user progress for a file - writes to PostgreSQL and Redis"""
    data = request.json
    user_id = request.current_user['uid']
    file_id = data.get('file_id')
    progress_seconds = data.get('progress_seconds', 0)
    progress_percentage = data.get('progress_percentage', 0)
    completed = data.get('completed', False)

    # Get file info
    file_info = db.get_file_by_id(file_id)

    if not file_info:
        return jsonify({'error': 'File not found'}), 404

    lesson_id = file_info.get('lesson_id')
    course_id = file_info.get('course_id')

    # Primary: Write to PostgreSQL database
    try:
        postgres_db = get_db_service()
        postgres_db.update_file_progress(
            user_id=user_id,
            file_id=file_id,
            lesson_id=lesson_id,
            course_id=course_id,
            progress_seconds=progress_seconds,
            progress_percentage=progress_percentage,
            completed=completed
        )
        logger.info(f"Progress saved to PostgreSQL for user {user_id}, file {file_id}")
    except Exception as e:
        logger.error(f"Failed to save progress to PostgreSQL: {str(e)}")
        # Continue to Redis/Firebase even if PostgreSQL fails

    # Get cache service
    cache = get_cache()

    # Cache key for this progress entry
    cache_key = f"progress:{user_id}:{file_id}"

    # Store progress in Redis immediately (fast read cache)
    progress_data = {
        'user_id': user_id,
        'file_id': file_id,
        'lesson_id': lesson_id,
        'course_id': course_id,
        'progress_seconds': progress_seconds,
        'progress_percentage': progress_percentage,
        'completed': completed,
        'last_updated': int(time.time())
    }

    if cache.enabled:
        # Store in Redis with 24 hour TTL
        cache.set(cache_key, progress_data, ttl=86400)

        # Mark this progress as dirty (needs Firebase sync)
        dirty_key = f"progress:dirty:{user_id}:{file_id}"
        cache.set(dirty_key, True, ttl=86400)
    else:
        # If Redis is unavailable, fall back to direct Firebase write
        db.update_user_progress(
            user_id=user_id,
            file_id=file_id,
            lesson_id=lesson_id,
            course_id=course_id,
            progress_seconds=progress_seconds,
            progress_percentage=progress_percentage,
            completed=completed
        )

    return jsonify({'success': True})

@api_bp.route('/api/progress/file/<file_id>', methods=['GET'])
@require_auth
def get_file_progress_endpoint(file_id):
    """Get progress for a specific file - tries Redis first, then PostgreSQL, then Firebase"""
    user_id = request.current_user['uid']

    cache = get_cache()
    cache_key = f"progress:{user_id}:{file_id}"

    # Try Redis first (fastest)
    if cache.enabled:
        progress_data = cache.get(cache_key)
        if progress_data:
            logger.debug(f"Progress cache HIT for file {file_id}")
            return jsonify(progress_data)

    # Try PostgreSQL (primary database)
    try:
        postgres_db = get_db_service()
        progress = postgres_db.get_file_progress(user_id, file_id)

        if progress:
            logger.debug(f"Progress found in PostgreSQL for file {file_id}")
            # Cache the result
            if cache.enabled:
                cache.set(cache_key, progress, ttl=86400)
            return jsonify(progress)
    except Exception as e:
        logger.error(f"Failed to get progress from PostgreSQL: {str(e)}")

    # Fall back to Firebase
    logger.debug(f"Progress cache MISS for file {file_id}, fetching from Firebase")
    progress = db.get_user_progress(user_id, file_id)

    # Cache the result from Firebase
    if progress and cache.enabled:
        cache.set(cache_key, progress, ttl=86400)

    return jsonify(progress or {})

@api_bp.route('/api/progress/course/<course_id>', methods=['GET'])
@require_auth
def get_course_progress_endpoint(course_id):
    """Get course progress for a user - tries PostgreSQL first, then Firebase"""
    user_id = request.current_user['uid']

    # Try PostgreSQL first
    try:
        postgres_db = get_db_service()
        progress = postgres_db.get_course_progress(user_id, course_id)

        if progress:
            logger.debug(f"Course progress found in PostgreSQL for course {course_id}")
            return jsonify(progress)
    except Exception as e:
        logger.error(f"Failed to get course progress from PostgreSQL: {str(e)}")

    # Fall back to Firebase
    progress = db.get_course_progress(course_id, user_id)
    return jsonify(progress)

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
def get_scan_history_endpoint():
    """Get scan history"""
    history = db.get_scan_history(limit=10)
    return jsonify(history)

@api_bp.route('/api/stats', methods=['GET'])
def get_stats_endpoint():
    """Get overall statistics"""
    stats = db.get_stats()
    return jsonify(stats)

@api_bp.route('/api/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'media_path': Config.MEDIA_PATH,
        'database': 'Firebase',
        'cors_enabled': True,
        'version': '2.0.0'
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

@api_bp.route('/api/thumbnails/generate', methods=['POST'])
def generate_thumbnails_endpoint():
    """Generate thumbnails for all videos that don't have them"""
    if not check_ffmpeg():
        return jsonify({'error': 'ffmpeg not found. Please install ffmpeg to generate thumbnails.'}), 400

    # Get all video files without thumbnails
    videos = db.get_all_video_files_without_thumbnails()
    total = len(videos)
    generated = 0
    failed = 0

    logger.info(f"Starting thumbnail generation for {total} videos")

    for video in videos:
        video_full_path = os.path.join(Config.MEDIA_PATH, video['file_path'])

        if not os.path.exists(video_full_path):
            logger.warning(f"Video file not found: {video_full_path}")
            failed += 1
            continue

        thumbnail_base64 = generate_thumbnail_for_file(video_full_path, video['filename'])

        if thumbnail_base64:
            db.update_file(video['id'], thumbnail_base64=thumbnail_base64)
            generated += 1
            logger.info(f"Generated thumbnail for: {video['filename']}")
        else:
            failed += 1
            logger.error(f"Failed to generate thumbnail for: {video['filename']}")

    return jsonify({
        'success': True,
        'total_videos': total,
        'generated': generated,
        'failed': failed
    })

@api_bp.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    cache = get_cache()
    stats = cache.get_stats()
    return jsonify(stats)

@api_bp.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all cache (admin only - consider adding auth)"""
    cache = get_cache()
    cache.clear_all()
    return jsonify({'success': True, 'message': 'Cache cleared'})

@api_bp.route('/api/cache/invalidate/course/<course_id>', methods=['POST'])
def invalidate_course_cache(course_id):
    """Invalidate all cache for a course"""
    cache = get_cache()
    cache.invalidate_course(course_id)
    return jsonify({'success': True, 'message': f'Cache invalidated for course {course_id}'})

@api_bp.route('/api/cache/invalidate/lesson/<lesson_id>', methods=['POST'])
def invalidate_lesson_cache(lesson_id):
    """Invalidate all cache for a lesson"""
    cache = get_cache()
    cache.invalidate_lesson(lesson_id)
    return jsonify({'success': True, 'message': f'Cache invalidated for lesson {lesson_id}'})

# Register the blueprint
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)

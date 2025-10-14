from flask import Flask, request, send_file, jsonify, Response
from flask_cors import CORS
import os
import mimetypes
from config import Config
from database import init_db, get_db

app = Flask(__name__)
CORS(app)

# Initialize database
init_db()

@app.route('/api/courses', methods=['GET'])
def get_courses():
    """Get all courses"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM courses ORDER BY created_at DESC')
    courses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(courses)

@app.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """Get a specific course with its lessons"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM courses WHERE id = ?', (course_id,))
    course = cursor.fetchone()

    if not course:
        conn.close()
        return jsonify({'error': 'Course not found'}), 404

    course_dict = dict(course)

    # Get lessons for this course
    cursor.execute('''
        SELECT * FROM lessons
        WHERE course_id = ?
        ORDER BY order_index
    ''', (course_id,))
    lessons = [dict(row) for row in cursor.fetchall()]

    course_dict['lessons'] = lessons
    conn.close()

    return jsonify(course_dict)

@app.route('/api/lessons/<int:lesson_id>', methods=['GET'])
def get_lesson(lesson_id):
    """Get a specific lesson with resources"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,))
    lesson = cursor.fetchone()

    if not lesson:
        conn.close()
        return jsonify({'error': 'Lesson not found'}), 404

    lesson_dict = dict(lesson)

    # Get resources for this lesson
    cursor.execute('SELECT * FROM resources WHERE lesson_id = ?', (lesson_id,))
    resources = [dict(row) for row in cursor.fetchall()]

    lesson_dict['resources'] = resources
    conn.close()

    return jsonify(lesson_dict)

@app.route('/api/video/<int:lesson_id>', methods=['GET'])
def stream_video(lesson_id):
    """Stream video with range request support"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT video_path FROM lessons WHERE id = ?', (lesson_id,))
    result = cursor.fetchone()
    conn.close()

    if not result or not result['video_path']:
        return jsonify({'error': 'Video not found'}), 404

    video_path = os.path.join(Config.MEDIA_PATH, result['video_path'])

    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file not found on disk'}), 404

    # Get file size
    file_size = os.path.getsize(video_path)

    # Check if range request
    range_header = request.headers.get('Range', None)

    if not range_header:
        # No range request, send entire file
        return send_file(video_path, mimetype='video/mp4')

    # Parse range header
    byte_start = 0
    byte_end = file_size - 1

    if range_header:
        range_match = range_header.replace('bytes=', '').split('-')
        byte_start = int(range_match[0]) if range_match[0] else 0
        byte_end = int(range_match[1]) if range_match[1] else byte_end

    # Read the requested chunk
    length = byte_end - byte_start + 1

    with open(video_path, 'rb') as video_file:
        video_file.seek(byte_start)
        data = video_file.read(length)

    # Create response with partial content
    response = Response(
        data,
        206,
        mimetype='video/mp4',
        direct_passthrough=True
    )

    response.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
    response.headers.add('Accept-Ranges', 'bytes')
    response.headers.add('Content-Length', str(length))

    return response

@app.route('/api/document/<int:resource_id>', methods=['GET'])
def get_document(resource_id):
    """Serve document files"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT file_path, file_type FROM resources WHERE id = ?', (resource_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({'error': 'Document not found'}), 404

    file_path = os.path.join(Config.MEDIA_PATH, result['file_path'])

    if not os.path.exists(file_path):
        return jsonify({'error': 'Document file not found on disk'}), 404

    # Determine mimetype
    mimetype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    return send_file(file_path, mimetype=mimetype)

@app.route('/api/progress', methods=['POST'])
def update_progress():
    """Update user progress for a lesson"""
    data = request.json
    user_id = data.get('user_id', 'default_user')
    lesson_id = data.get('lesson_id')
    progress = data.get('progress', 0)
    completed = data.get('completed', False)

    conn = get_db()
    cursor = conn.cursor()

    # Check if progress exists
    cursor.execute('''
        SELECT id FROM user_progress
        WHERE user_id = ? AND lesson_id = ?
    ''', (user_id, lesson_id))

    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
            UPDATE user_progress
            SET progress = ?, completed = ?, last_watched = CURRENT_TIMESTAMP
            WHERE user_id = ? AND lesson_id = ?
        ''', (progress, completed, user_id, lesson_id))
    else:
        cursor.execute('''
            INSERT INTO user_progress (user_id, lesson_id, progress, completed)
            VALUES (?, ?, ?, ?)
        ''', (user_id, lesson_id, progress, completed))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/progress/<int:lesson_id>', methods=['GET'])
def get_progress(lesson_id):
    """Get user progress for a lesson"""
    user_id = request.args.get('user_id', 'default_user')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM user_progress
        WHERE user_id = ? AND lesson_id = ?
    ''', (user_id, lesson_id))

    result = cursor.fetchone()
    conn.close()

    if result:
        return jsonify(dict(result))
    else:
        return jsonify({'progress': 0, 'completed': False})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'media_path': Config.MEDIA_PATH})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)

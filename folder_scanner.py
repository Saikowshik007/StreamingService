"""
Automatic folder scanner to detect and import courses from your file system.
Expected structure: MainFolder/CourseName/Subject/lesson.mp4
"""

import os
import time
from pathlib import Path
from config import Config
from database_enhanced import get_db, init_enhanced_db, update_course_progress

# Supported file extensions
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', '.xls', '.xlsx', '.zip', '.rar'}

def get_file_size(file_path):
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0

def get_video_duration(file_path):
    """Get video duration in seconds (placeholder - would need ffmpeg for real implementation)"""
    # For now, return None. You can integrate ffmpeg-python to get actual duration
    return None

def is_video_file(filename):
    """Check if file is a video"""
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS

def is_document_file(filename):
    """Check if file is a document"""
    return Path(filename).suffix.lower() in DOCUMENT_EXTENSIONS

def scan_folder_structure(base_path):
    """
    Scan folder structure and return organized data
    Expected: base_path/CourseName/LessonFolder/files
    """
    base_path = Path(base_path)
    if not base_path.exists():
        raise ValueError(f"Path does not exist: {base_path}")

    courses_data = {}
    files_found = 0

    # Iterate through course folders (first level)
    for course_folder in base_path.iterdir():
        if not course_folder.is_dir():
            continue

        course_name = course_folder.name
        course_path = str(course_folder.relative_to(base_path))

        courses_data[course_name] = {
            'path': course_path,
            'lessons': {},
            'total_files': 0
        }

        # Iterate through lesson folders (second level)
        for lesson_folder in course_folder.iterdir():
            if not lesson_folder.is_dir():
                # Handle files directly in course folder
                if is_video_file(lesson_folder.name) or is_document_file(lesson_folder.name):
                    lesson_name = 'Main Content'
                    if lesson_name not in courses_data[course_name]['lessons']:
                        courses_data[course_name]['lessons'][lesson_name] = {
                            'path': course_path,
                            'files': []
                        }

                    file_info = {
                        'filename': lesson_folder.name,
                        'path': str(lesson_folder.relative_to(base_path)),
                        'size': get_file_size(lesson_folder),
                        'is_video': is_video_file(lesson_folder.name),
                        'is_document': is_document_file(lesson_folder.name),
                        'extension': lesson_folder.suffix.lower()
                    }
                    courses_data[course_name]['lessons'][lesson_name]['files'].append(file_info)
                    courses_data[course_name]['total_files'] += 1
                    files_found += 1
                continue

            lesson_name = lesson_folder.name
            lesson_path = str(lesson_folder.relative_to(base_path))

            courses_data[course_name]['lessons'][lesson_name] = {
                'path': lesson_path,
                'files': []
            }

            # Get all files in lesson folder
            for file in lesson_folder.iterdir():
                if file.is_file() and (is_video_file(file.name) or is_document_file(file.name)):
                    file_info = {
                        'filename': file.name,
                        'path': str(file.relative_to(base_path)),
                        'size': get_file_size(file),
                        'is_video': is_video_file(file.name),
                        'is_document': is_document_file(file.name),
                        'extension': file.suffix.lower()
                    }
                    courses_data[course_name]['lessons'][lesson_name]['files'].append(file_info)
                    courses_data[course_name]['total_files'] += 1
                    files_found += 1

    return courses_data, files_found

def import_to_database(courses_data, rescan=False):
    """Import scanned data into database"""
    conn = get_db()
    cursor = conn.cursor()

    courses_added = 0
    lessons_added = 0
    files_added = 0

    for course_name, course_info in courses_data.items():
        # Check if course exists
        cursor.execute('SELECT id FROM courses WHERE folder_path = ?', (course_info['path'],))
        existing_course = cursor.fetchone()

        if existing_course and not rescan:
            course_id = existing_course['id']
            print(f"Course '{course_name}' already exists (ID: {course_id})")
        else:
            if existing_course:
                course_id = existing_course['id']
                # Update course
                cursor.execute('''
                    UPDATE courses SET
                        title = ?,
                        total_files = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (course_name, course_info['total_files'], course_id))
                print(f"Updated course: {course_name}")
            else:
                # Insert new course
                cursor.execute('''
                    INSERT INTO courses (title, description, instructor, folder_path, total_files)
                    VALUES (?, ?, ?, ?, ?)
                ''', (course_name, f'Auto-imported from {course_info["path"]}',
                      'Unknown', course_info['path'], course_info['total_files']))
                course_id = cursor.lastrowid
                courses_added += 1
                print(f"Added course: {course_name} (ID: {course_id})")

        # Process lessons
        lesson_order = 1
        for lesson_name, lesson_info in course_info['lessons'].items():
            # Check if lesson exists
            cursor.execute('''
                SELECT id FROM lessons WHERE course_id = ? AND folder_path = ?
            ''', (course_id, lesson_info['path']))
            existing_lesson = cursor.fetchone()

            if existing_lesson:
                lesson_id = existing_lesson['id']
            else:
                cursor.execute('''
                    INSERT INTO lessons (course_id, title, folder_path, order_index)
                    VALUES (?, ?, ?, ?)
                ''', (course_id, lesson_name, lesson_info['path'], lesson_order))
                lesson_id = cursor.lastrowid
                lessons_added += 1
                print(f"  Added lesson: {lesson_name} (ID: {lesson_id})")

            lesson_order += 1

            # Process files
            file_order = 1
            for file_info in lesson_info['files']:
                # Check if file exists
                cursor.execute('SELECT id FROM files WHERE file_path = ?', (file_info['path'],))
                existing_file = cursor.fetchone()

                if existing_file:
                    # Update file
                    cursor.execute('''
                        UPDATE files SET
                            file_size = ?,
                            last_scanned = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (file_info['size'], existing_file['id']))
                else:
                    # Insert new file
                    cursor.execute('''
                        INSERT INTO files
                        (lesson_id, course_id, filename, file_path, file_type, file_size,
                         is_video, is_document, order_index)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (lesson_id, course_id, file_info['filename'], file_info['path'],
                          file_info['extension'], file_info['size'],
                          file_info['is_video'], file_info['is_document'], file_order))
                    files_added += 1

                file_order += 1

    conn.commit()

    # Update course progress for all users
    cursor.execute('SELECT DISTINCT id FROM courses')
    for row in cursor.fetchall():
        update_course_progress(row['id'])

    conn.close()

    return courses_added, lessons_added, files_added

def scan_and_import(base_path=None, rescan=False):
    """Main function to scan folder and import to database"""
    if base_path is None:
        base_path = Config.MEDIA_PATH

    print(f"Scanning folder: {base_path}")
    print(f"Rescan mode: {rescan}")
    print("-" * 60)

    start_time = time.time()

    try:
        # Initialize database
        init_enhanced_db()

        # Scan folders
        courses_data, files_found = scan_folder_structure(base_path)

        print(f"\nFound {len(courses_data)} courses with {files_found} files")
        print("-" * 60)

        # Import to database
        courses_added, lessons_added, files_added = import_to_database(courses_data, rescan)

        scan_duration = time.time() - start_time

        # Record scan history
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scan_history
            (scan_path, files_found, courses_added, lessons_added, scan_duration, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (base_path, files_found, courses_added, lessons_added, scan_duration, 'success'))
        conn.commit()
        conn.close()

        print("\nScan Summary:")
        print(f"  Courses added: {courses_added}")
        print(f"  Lessons added: {lessons_added}")
        print(f"  Files added: {files_added}")
        print(f"  Scan duration: {scan_duration:.2f} seconds")
        print(f"  Status: Success")

        return True

    except Exception as e:
        print(f"\nError during scan: {str(e)}")
        scan_duration = time.time() - start_time

        # Record failed scan
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scan_history
                (scan_path, files_found, scan_duration, status)
                VALUES (?, ?, ?, ?)
            ''', (base_path, 0, scan_duration, f'failed: {str(e)}'))
            conn.commit()
            conn.close()
        except:
            pass

        return False

if __name__ == '__main__':
    import sys

    rescan = '--rescan' in sys.argv or '-r' in sys.argv

    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        scan_path = sys.argv[1]
    else:
        scan_path = Config.MEDIA_PATH

    print("=" * 60)
    print("LEARNING PLATFORM - FOLDER SCANNER")
    print("=" * 60)

    success = scan_and_import(scan_path, rescan)

    if success:
        print("\n✓ Scan completed successfully!")
        print("\nYou can now start the server and view your courses.")
    else:
        print("\n✗ Scan failed. Check the error messages above.")

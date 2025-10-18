"""
Automatic folder scanner to detect and import courses from your file system.
Expected structure: MainFolder/CourseName/Subject/lesson.mp4
"""

import os
import re
import time
from pathlib import Path
from config import Config
import firebase_service as db
from thumbnail_generator import generate_thumbnail_for_file, check_ffmpeg

# Supported file extensions
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', '.xls', '.xlsx', '.zip', '.rar'}

def natural_sort_key(text):
    """
    Natural sort key for sorting filenames with numbers correctly.
    Converts '1', '2', '10', '20' to be sorted as numbers, not strings.

    Example:
        ['1.mp4', '10.mp4', '2.mp4'] -> ['1.mp4', '2.mp4', '10.mp4']
    """
    def convert(part):
        return int(part) if part.isdigit() else part.lower()

    return [convert(c) for c in re.split('([0-9]+)', str(text))]

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
    Scan folder structure recursively using DFS and return organized data
    Uses Path.rglob() to find all files at any depth
    Expected: base_path/CourseName/any_nested_structure/files
    """
    base_path = Path(base_path)
    if not base_path.exists():
        raise ValueError(f"Path does not exist: {base_path}")

    courses_data = {}
    files_found = 0

    # Iterate through course folders (first level) - sorted naturally
    course_folders = sorted(
        [f for f in base_path.iterdir() if f.is_dir()],
        key=lambda f: natural_sort_key(f.name)
    )

    for course_folder in course_folders:

        course_name = course_folder.name
        course_path = str(course_folder.relative_to(base_path))

        courses_data[course_name] = {
            'path': course_path,
            'lessons': {},
            'total_files': 0
        }

        # Use rglob to recursively find all files in the course folder
        all_files = [
            f for f in course_folder.rglob('*')
            if f.is_file() and (is_video_file(f.name) or is_document_file(f.name))
        ]

        # Group files by their parent directory (lesson folder)
        lessons_map = {}
        for file in all_files:
            # Get the immediate parent directory relative to course folder
            parent_dir = file.parent

            # If file is directly in course folder, use 'Main Content'
            if parent_dir == course_folder:
                lesson_name = 'Main Content'
                lesson_path = course_path
            else:
                # Use parent directory name as lesson name
                lesson_name = parent_dir.name
                lesson_path = str(parent_dir.relative_to(base_path))

            # Initialize lesson if not exists
            if lesson_name not in lessons_map:
                lessons_map[lesson_name] = {
                    'path': lesson_path,
                    'files': []
                }

            # Add file info
            file_info = {
                'filename': file.name,
                'path': str(file.relative_to(base_path)),
                'size': get_file_size(file),
                'is_video': is_video_file(file.name),
                'is_document': is_document_file(file.name),
                'extension': file.suffix.lower()
            }
            lessons_map[lesson_name]['files'].append(file_info)
            courses_data[course_name]['total_files'] += 1
            files_found += 1

        # Sort lessons naturally and sort files within each lesson
        for lesson_name in sorted(lessons_map.keys(), key=natural_sort_key):
            lesson_data = lessons_map[lesson_name]
            # Sort files naturally
            lesson_data['files'] = sorted(
                lesson_data['files'],
                key=lambda f: natural_sort_key(f['filename'])
            )
            courses_data[course_name]['lessons'][lesson_name] = lesson_data

    return courses_data, files_found

def import_to_database(courses_data, rescan=False):
    """Import scanned data into Firebase"""
    courses_added = 0
    lessons_added = 0
    files_added = 0
    processed_course_ids = []

    for course_name, course_info in courses_data.items():
        # Check if course exists
        existing_course = db.get_course_by_folder_path(course_info['path'])

        if existing_course and not rescan:
            course_id = existing_course['id']
            print(f"Course '{course_name}' already exists (ID: {course_id})")
        else:
            if existing_course:
                course_id = existing_course['id']
                # Update course
                db.update_course(
                    course_id,
                    title=course_name,
                    total_files=course_info['total_files']
                )
                print(f"Updated course: {course_name}")
            else:
                # Create new course
                course_id = db.create_course(
                    title=course_name,
                    description=f'Auto-imported from {course_info["path"]}',
                    instructor='Unknown',
                    folder_path=course_info['path'],
                    total_files=course_info['total_files']
                )
                courses_added += 1
                print(f"Added course: {course_name} (ID: {course_id})")

        # Track this course ID for progress update later
        processed_course_ids.append(course_id)

        # Process lessons
        lesson_order = 1
        for lesson_name, lesson_info in course_info['lessons'].items():
            # Check if lesson exists
            existing_lesson = db.get_lesson_by_folder_path(course_id, lesson_info['path'])

            if existing_lesson:
                lesson_id = existing_lesson['id']
            else:
                lesson_id = db.create_lesson(
                    course_id=course_id,
                    title=lesson_name,
                    folder_path=lesson_info['path'],
                    order_index=lesson_order
                )
                lessons_added += 1
                print(f"  Added lesson: {lesson_name} (ID: {lesson_id})")

            lesson_order += 1

            # Process files
            file_order = 1
            for file_info in lesson_info['files']:
                # Check if file exists
                existing_file = db.get_file_by_path(file_info['path'])

                if existing_file:
                    file_id = existing_file['id']
                    # Update file
                    db.update_file(file_id, file_size=file_info['size'])

                    # Generate thumbnail if it's a video and doesn't have one
                    if file_info['is_video'] and not existing_file.get('thumbnail_base64'):
                        video_full_path = os.path.join(Config.MEDIA_PATH, file_info['path'])
                        thumbnail_base64 = generate_thumbnail_for_file(video_full_path, file_info['filename'])
                        if thumbnail_base64:
                            db.update_file(file_id, thumbnail_base64=thumbnail_base64)
                            print(f"    Generated thumbnail for: {file_info['filename']}")
                else:
                    # Generate thumbnail for new video files
                    thumbnail_base64 = None
                    if file_info['is_video']:
                        video_full_path = os.path.join(Config.MEDIA_PATH, file_info['path'])
                        thumbnail_base64 = generate_thumbnail_for_file(video_full_path, file_info['filename'])
                        if thumbnail_base64:
                            print(f"    Generated thumbnail for: {file_info['filename']}")

                    # Create new file
                    file_id = db.create_file(
                        lesson_id=lesson_id,
                        course_id=course_id,
                        filename=file_info['filename'],
                        file_path=file_info['path'],
                        file_type=file_info['extension'],
                        file_size=file_info['size'],
                        is_video=file_info['is_video'],
                        is_document=file_info['is_document'],
                        order_index=file_order,
                        thumbnail_base64=thumbnail_base64
                    )
                    files_added += 1

                file_order += 1

    # Update course progress for all processed courses
    for cid in processed_course_ids:
        try:
            db.update_course_progress(cid, 'default_user')
        except Exception as e:
            print(f"  Warning: Failed to update progress for course {cid}: {str(e)}")

    return courses_added, lessons_added, files_added

def scan_and_import(base_path=None, rescan=False):
    """Main function to scan folder and import to Firebase"""
    if base_path is None:
        base_path = Config.MEDIA_PATH

    print(f"Scanning folder: {base_path}")
    print(f"Rescan mode: {rescan}")
    print("-" * 60)

    start_time = time.time()

    try:
        # Initialize Firebase
        db.init_firebase()

        # Scan folders
        courses_data, files_found = scan_folder_structure(base_path)

        print(f"\nFound {len(courses_data)} courses with {files_found} files")
        print("-" * 60)

        # Import to Firebase
        courses_added, lessons_added, files_added = import_to_database(courses_data, rescan)

        scan_duration = time.time() - start_time

        # Record scan history
        db.add_scan_history(
            scan_path=base_path,
            files_found=files_found,
            courses_added=courses_added,
            lessons_added=lessons_added,
            scan_duration=scan_duration,
            status='success'
        )

        print("\nScan Summary:")
        print(f"  Courses added: {courses_added}")
        print(f"  Lessons added: {lessons_added}")
        print(f"  Files added: {files_added}")
        print(f"  Scan duration: {scan_duration:.2f} seconds")
        print(f"  Status: Success")

        return True

    except Exception as e:
        print(f"\nError during scan: {str(e)}")
        import traceback
        traceback.print_exc()
        scan_duration = time.time() - start_time

        # Record failed scan
        try:
            db.add_scan_history(
                scan_path=base_path,
                files_found=0,
                courses_added=0,
                lessons_added=0,
                scan_duration=scan_duration,
                status=f'failed: {str(e)}'
            )
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

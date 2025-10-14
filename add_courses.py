"""
Helper script to add courses, lessons, and resources to the database.
Modify this script to add your own courses.
"""

from database import get_db, init_db

def add_course(title, description, instructor, thumbnail=''):
    """Add a course to the database"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO courses (title, description, instructor, thumbnail)
        VALUES (?, ?, ?, ?)
    ''', (title, description, instructor, thumbnail))
    course_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"Added course: {title} (ID: {course_id})")
    return course_id

def add_lesson(course_id, title, description, video_path, duration=None, order_index=1):
    """Add a lesson to a course"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO lessons (course_id, title, description, video_path, duration, order_index)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (course_id, title, description, video_path, duration, order_index))
    lesson_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"  Added lesson: {title} (ID: {lesson_id})")
    return lesson_id

def add_resource(lesson_id, title, file_path, file_type):
    """Add a resource (document) to a lesson"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO resources (lesson_id, title, file_path, file_type)
        VALUES (?, ?, ?, ?)
    ''', (lesson_id, title, file_path, file_type))
    resource_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"    Added resource: {title} (ID: {resource_id})")
    return resource_id

if __name__ == '__main__':
    # Initialize database
    init_db()

    # Example: Add a Python Programming course
    course_id = add_course(
        title='Python Programming Fundamentals',
        description='Learn Python programming from scratch with practical examples',
        instructor='John Doe'
    )

    # Add lessons to the course
    lesson1_id = add_lesson(
        course_id=course_id,
        title='Introduction to Python',
        description='Learn the basics of Python programming',
        video_path='python/intro.mp4',  # Path relative to MEDIA_PATH
        duration=600,  # Duration in seconds
        order_index=1
    )

    # Add resources to the lesson
    add_resource(
        lesson_id=lesson1_id,
        title='Python Basics Cheatsheet',
        file_path='python/cheatsheet.pdf',  # Path relative to MEDIA_PATH
        file_type='pdf'
    )

    lesson2_id = add_lesson(
        course_id=course_id,
        title='Variables and Data Types',
        description='Understanding Python variables and data types',
        video_path='python/variables.mp4',
        duration=720,
        order_index=2
    )

    add_resource(
        lesson_id=lesson2_id,
        title='Data Types Reference',
        file_path='python/datatypes.pdf',
        file_type='pdf'
    )

    # Example: Add another course
    course_id2 = add_course(
        title='Web Development Basics',
        description='Learn HTML, CSS, and JavaScript fundamentals',
        instructor='Jane Smith'
    )

    lesson3_id = add_lesson(
        course_id=course_id2,
        title='HTML Introduction',
        description='Getting started with HTML',
        video_path='web/html-intro.mp4',
        duration=540,
        order_index=1
    )

    print("\nCourses added successfully!")
    print("\nIMPORTANT: Make sure your video and document files exist in the MEDIA_PATH directory")
    print("with the exact paths specified above.")

import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import API_URL, { authenticatedFetch } from '../config';
import './CoursePage.css';

// Build a hierarchical tree from flat lesson list
function buildLessonTree(lessons) {
  const tree = {};

  lessons.forEach(lesson => {
    const parts = lesson.title.split('/');

    // If no slash, it's a top-level lesson
    if (parts.length === 1) {
      if (!tree[lesson.title]) {
        tree[lesson.title] = {
          type: 'lesson',
          lesson: lesson,
          children: {}
        };
      }
    } else {
      // Build nested structure
      let current = tree;

      for (let i = 0; i < parts.length - 1; i++) {
        const folderName = parts[i];
        if (!current[folderName]) {
          current[folderName] = {
            type: 'folder',
            name: folderName,
            children: {}
          };
        }
        current = current[folderName].children;
      }

      // Last part is the actual lesson
      const lessonName = parts[parts.length - 1];
      current[lessonName] = {
        type: 'lesson',
        lesson: lesson,
        children: {}
      };
    }
  });

  return tree;
}

// TreeNode component for rendering folders and lessons
function TreeNode({ name, node, depth = 0 }) {
  const [isOpen, setIsOpen] = useState(true);

  if (node.type === 'lesson') {
    return (
      <Link
        to={`/lesson/${node.lesson.id}`}
        className="lesson-item"
        style={{ paddingLeft: `${depth * 20 + 10}px` }}
      >
        <div className="lesson-icon">🎥</div>
        <div className="lesson-details">
          <h3>{name}</h3>
          {node.lesson.description && <p>{node.lesson.description}</p>}
        </div>
        <div className="lesson-arrow">→</div>
      </Link>
    );
  }

  // Folder node
  const hasChildren = Object.keys(node.children).length > 0;

  return (
    <div className="folder-node">
      <div
        className="folder-header"
        style={{ paddingLeft: `${depth * 20 + 10}px` }}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="folder-icon">{isOpen ? '📂' : '📁'}</span>
        <span className="folder-name">{name}</span>
        <span className="folder-toggle">{isOpen ? '▼' : '▶'}</span>
      </div>
      {isOpen && hasChildren && (
        <div className="folder-children">
          {Object.entries(node.children).map(([childName, childNode]) => (
            <TreeNode
              key={childName}
              name={childName}
              node={childNode}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CoursePage() {
  const { courseId } = useParams();
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCourse = async () => {
      try {
        const response = await authenticatedFetch(`${API_URL}/api/courses/${courseId}`);
        const data = await response.json();
        setCourse(data);
        setLoading(false);
      } catch (err) {
        setError('Failed to load course details.');
        setLoading(false);
      }
    };

    fetchCourse();
  }, [courseId]);

  if (loading) {
    return <div className="loading">Loading course...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!course) {
    return <div className="error">Course not found</div>;
  }

  // Build tree structure from lessons
  const lessonTree = course?.lessons && course.lessons.length > 0
    ? buildLessonTree(course.lessons)
    : {};

  return (
    <div className="course-page">
      <div className="course-header">
        <div className="container">
          <h1>{course.title}</h1>
          <p className="course-meta">Instructor: {course.instructor}</p>
          <p className="course-desc">{course.description}</p>
        </div>
      </div>
      <div className="container">
        <h2 className="section-title">Course Content</h2>
        {Object.keys(lessonTree).length > 0 ? (
          <div className="lessons-tree">
            {Object.entries(lessonTree).map(([name, node]) => (
              <TreeNode key={name} name={name} node={node} depth={0} />
            ))}
          </div>
        ) : (
          <div className="no-lessons">
            <p>No lessons available for this course yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default CoursePage;

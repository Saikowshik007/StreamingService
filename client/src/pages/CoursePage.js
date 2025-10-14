import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import './CoursePage.css';

function CoursePage() {
  const { courseId } = useParams();
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCourse();
  }, [courseId]);

  const fetchCourse = async () => {
    try {
      const response = await axios.get(`/api/courses/${courseId}`);
      setCourse(response.data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load course details.');
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading course...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!course) {
    return <div className="error">Course not found</div>;
  }

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
        {course.lessons && course.lessons.length > 0 ? (
          <div className="lessons-list">
            {course.lessons.map((lesson, index) => (
              <Link
                to={`/lesson/${lesson.id}`}
                key={lesson.id}
                className="lesson-item"
              >
                <div className="lesson-number">{index + 1}</div>
                <div className="lesson-details">
                  <h3>{lesson.title}</h3>
                  <p>{lesson.description}</p>
                  {lesson.duration && (
                    <span className="lesson-duration">
                      {Math.floor(lesson.duration / 60)}:{(lesson.duration % 60).toString().padStart(2, '0')} min
                    </span>
                  )}
                </div>
                <div className="lesson-arrow">→</div>
              </Link>
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

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import API_URL, { authenticatedFetch } from '../config';
import './Home.css';

function Home() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    try {
      const response = await authenticatedFetch(`${API_URL}/api/courses`);
      const data = await response.json();
      setCourses(data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load courses. Make sure the backend server is running.');
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading courses...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="home">
      <div className="hero">
        <h1>Learn at Your Own Pace</h1>
        <p>Access high-quality courses from your local library</p>
      </div>
      <div className="container">
        <h2 className="section-title">Available Courses</h2>
        {courses.length === 0 ? (
          <div className="no-courses">
            <p>No courses available yet.</p>
            <p>Add courses to your database to get started!</p>
          </div>
        ) : (
          <div className="courses-grid">
            {courses.map(course => (
              <Link to={`/course/${course.id}`} key={course.id} className="course-card">
                <div className="course-thumbnail">
                  {course.thumbnail ? (
                    <img src={course.thumbnail} alt={course.title} />
                  ) : (
                    <div className="thumbnail-placeholder">
                      <span>{course.title.charAt(0)}</span>
                    </div>
                  )}
                </div>
                <div className="course-info">
                  <h3 className="course-title">{course.title}</h3>
                  <p className="course-instructor">{course.instructor}</p>
                  <p className="course-description">{course.description}</p>
                  {course.progress_percentage !== null && course.progress_percentage !== undefined && (
                    <div className="course-progress">
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{width: `${course.progress_percentage}%`}}
                        ></div>
                      </div>
                      <span className="progress-text">
                        {Math.round(course.progress_percentage)}% Complete
                        {course.completed_files && course.progress_total_files &&
                          ` (${course.completed_files}/${course.progress_total_files} files)`
                        }
                      </span>
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Home;

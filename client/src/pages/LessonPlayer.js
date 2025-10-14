import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import './LessonPlayer.css';

function LessonPlayer() {
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const videoRef = useRef(null);

  useEffect(() => {
    fetchLesson();
  }, [lessonId]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      const progress = (video.currentTime / video.duration) * 100;
      updateProgress(progress, video.currentTime >= video.duration - 1);
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => video.removeEventListener('timeupdate', handleTimeUpdate);
  }, [lesson]);

  const fetchLesson = async () => {
    try {
      const response = await axios.get(`/api/lessons/${lessonId}`);
      setLesson(response.data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load lesson.');
      setLoading(false);
    }
  };

  const updateProgress = async (progress, completed) => {
    try {
      await axios.post('/api/progress', {
        lesson_id: lessonId,
        progress: Math.floor(progress),
        completed: completed
      });
    } catch (err) {
      console.error('Failed to update progress:', err);
    }
  };

  if (loading) {
    return <div className="loading">Loading lesson...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!lesson) {
    return <div className="error">Lesson not found</div>;
  }

  return (
    <div className="lesson-player">
      <div className="video-container">
        {lesson.video_path ? (
          <video
            ref={videoRef}
            controls
            className="video-player"
            src={`/api/video/${lessonId}`}
          >
            Your browser does not support the video tag.
          </video>
        ) : (
          <div className="no-video">
            <p>No video available for this lesson</p>
          </div>
        )}
      </div>

      <div className="lesson-content">
        <div className="container">
          <h1 className="lesson-title">{lesson.title}</h1>
          {lesson.description && (
            <p className="lesson-description">{lesson.description}</p>
          )}

          {lesson.resources && lesson.resources.length > 0 && (
            <div className="resources-section">
              <h2>Course Resources</h2>
              <div className="resources-list">
                {lesson.resources.map(resource => (
                  <a
                    key={resource.id}
                    href={`/api/document/${resource.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="resource-item"
                  >
                    <div className="resource-icon">
                      {getFileIcon(resource.file_type)}
                    </div>
                    <div className="resource-info">
                      <h3>{resource.title}</h3>
                      <span className="resource-type">{resource.file_type || 'Document'}</span>
                    </div>
                    <div className="download-icon">⬇</div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function getFileIcon(fileType) {
  if (!fileType) return '📄';

  const type = fileType.toLowerCase();
  if (type.includes('pdf')) return '📕';
  if (type.includes('doc')) return '📘';
  if (type.includes('xls') || type.includes('csv')) return '📊';
  if (type.includes('ppt')) return '📙';
  if (type.includes('zip') || type.includes('rar')) return '📦';
  if (type.includes('txt')) return '📝';

  return '📄';
}

export default LessonPlayer;

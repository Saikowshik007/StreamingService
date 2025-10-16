import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import API_URL, { authenticatedFetch } from '../config';
import './LessonPlayerEnhanced.css';

function LessonPlayerEnhanced() {
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [currentFile, setCurrentFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const videoRef = useRef(null);
  const progressInterval = useRef(null);
  const shouldSeek = useRef(true);

  const updateProgress = useCallback(async () => {
    if (!currentFile || !currentFile.is_video || !videoRef.current) return;

    const video = videoRef.current;
    const progress_seconds = Math.floor(video.currentTime);
    const progress_percentage = (video.currentTime / video.duration) * 100;
    const completed = video.currentTime >= video.duration - 2;

    try {
      await authenticatedFetch(`${API_URL}/api/progress`, {
        method: 'POST',
        body: JSON.stringify({
          file_id: currentFile.id,
          progress_seconds,
          progress_percentage,
          completed
        })
      });

      // Update local state without triggering seek
      shouldSeek.current = false;
      setCurrentFile(prev => ({
        ...prev,
        progress_seconds,
        progress_percentage,
        completed
      }));
    } catch (err) {
      console.error('Failed to update progress:', err);
    }
  }, [currentFile]);

  useEffect(() => {
    const fetchLesson = async () => {
      try {
        const response = await authenticatedFetch(`${API_URL}/api/lessons/${lessonId}`);
        const data = await response.json();
        setLesson(data);
        setLoading(false);
      } catch (err) {
        setError('Failed to load lesson.');
        setLoading(false);
      }
    };

    fetchLesson();
    return () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
    };
  }, [lessonId]);

  useEffect(() => {
    if (lesson && lesson.files && lesson.files.length > 0 && !currentFile) {
      // Find first incomplete video or just the first video
      const firstIncomplete = lesson.files.find(f => f.is_video && !f.completed);
      const firstVideo = lesson.files.find(f => f.is_video);
      setCurrentFile(firstIncomplete || firstVideo || lesson.files[0]);
    }
  }, [lesson, currentFile]);

  useEffect(() => {
    if (currentFile && currentFile.is_video && videoRef.current) {
      const video = videoRef.current;

      // Seek to saved position only if this is a real file change
      if (shouldSeek.current && currentFile.progress_seconds && currentFile.progress_seconds > 0) {
        video.currentTime = currentFile.progress_seconds;
      }
      shouldSeek.current = true; // Reset for next time

      // Update progress every 5 seconds
      progressInterval.current = setInterval(() => {
        if (!video.paused) {
          updateProgress();
        }
      }, 5000);

      return () => {
        if (progressInterval.current) {
          clearInterval(progressInterval.current);
        }
      };
    }
  }, [currentFile, updateProgress]);

  const handleFileSelect = (file) => {
    // Save progress of current video before switching
    if (currentFile && currentFile.is_video && videoRef.current) {
      updateProgress();
    }
    setCurrentFile(file);
  };

  const handleVideoEnd = () => {
    updateProgress();
    // Auto-play next video if available
    const currentIndex = lesson.files.findIndex(f => f.id === currentFile.id);
    if (currentIndex < lesson.files.length - 1) {
      const nextFile = lesson.files[currentIndex + 1];
      if (nextFile.is_video) {
        setTimeout(() => setCurrentFile(nextFile), 1000);
      }
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

  const videos = lesson.files?.filter(f => f.is_video) || [];
  const documents = lesson.files?.filter(f => f.is_document) || [];

  return (
    <div className="lesson-player-enhanced">
      <div className="player-layout">
        <div className="main-content">
          <div className="video-container">
            {currentFile && currentFile.is_video ? (
            <video
              key={currentFile?.id}
              ref={videoRef}
              controls
              className="video-player"
              crossOrigin="use-credentials"
              src={`${API_URL}/api/stream/${currentFile.id}`}
              onEnded={handleVideoEnd}
              onPause={updateProgress}
              preload="metadata"
            />
            ) : (
              <div className="no-video">
                <p>Select a video to start watching</p>
              </div>
            )}
          </div>

          <div className="lesson-info">
            <h1>{lesson.title}</h1>
            {lesson.description && <p className="description">{lesson.description}</p>}
            {currentFile && (
              <div className="current-file-info">
                <h3>Now Playing: {currentFile.filename}</h3>
                {currentFile.progress_percentage > 0 && (
                  <div className="file-progress">
                    <div className="progress-bar-small">
                      <div
                        className="progress-fill-small"
                        style={{width: `${currentFile.progress_percentage}%`}}
                      ></div>
                    </div>
                    <span>{Math.round(currentFile.progress_percentage)}% watched</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="sidebar">
          {videos.length > 0 && (
            <div className="sidebar-section">
              <h2>Videos ({videos.length})</h2>
              <div className="files-list">
                {videos.map((file, index) => (
                  <div
                    key={file.id}
                    className={`file-item ${currentFile?.id === file.id ? 'active' : ''} ${file.completed ? 'completed' : ''}`}
                    onClick={() => handleFileSelect(file)}
                  >
                    {file.thumbnail_base64 ? (
                      <div className="file-thumbnail">
                        <img
                          src={file.thumbnail_base64}
                          alt={file.filename}
                          onError={(e) => e.target.style.display = 'none'}
                        />
                      </div>
                    ) : (
                      <div className="file-number">{index + 1}</div>
                    )}
                    <div className="file-details">
                      <div className="file-name">{file.filename}</div>
                      {file.progress_percentage > 0 && (
                        <div className="mini-progress">
                          <div
                            className="mini-progress-fill"
                            style={{width: `${file.progress_percentage}%`}}
                          ></div>
                        </div>
                      )}
                    </div>
                    {file.completed && <span className="check-mark">✓</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {documents.length > 0 && (
            <div className="sidebar-section">
              <h2>Resources ({documents.length})</h2>
              <div className="files-list">
                {documents.map(file => (
                  <a
                    key={file.id}
                    href={`${API_URL}/api/document/${file.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="file-item document"
                  >
                    <div className="file-icon">📄</div>
                    <div className="file-details">
                      <div className="file-name">{file.filename}</div>
                      <div className="file-type">{file.file_type}</div>
                    </div>
                    <span className="download-icon">⬇</span>
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

export default LessonPlayerEnhanced;

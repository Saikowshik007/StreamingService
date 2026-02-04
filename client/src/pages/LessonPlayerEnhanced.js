import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import API_URL, { authenticatedFetch } from '../config';
import './LessonPlayerEnhanced.css';

function LessonPlayerEnhanced() {
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [currentFile, setCurrentFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState('');
  const videoRef = useRef(null);

  // Load lesson
  useEffect(() => {
    authenticatedFetch(`${API_URL}/api/lessons/${lessonId}`)
      .then(r => r.json())
      .then(data => {
        setLesson(data);
        if (data.files) {
          const firstVideo = data.files.find(f => f.is_video);
          if (firstVideo) setCurrentFile(firstVideo);
        }
      });
  }, [lessonId]);

  // Load video URL when file changes
  useEffect(() => {
    if (!currentFile?.is_video) return;

    console.log('Loading video:', currentFile.filename);

    authenticatedFetch(`${API_URL}/api/stream/signed-url/${currentFile.id}`)
      .then(r => r.json())
      .then(data => {
        const url = `${API_URL}${data.url}`;
        console.log('Video URL:', url);
        setVideoUrl(url);
      })
      .catch(err => {
        console.error('Error loading video:', err);
      });
  }, [currentFile]);

  // Reset video when URL changes
  useEffect(() => {
    if (videoUrl && videoRef.current) {
      console.log('Setting video source:', videoUrl);
      videoRef.current.load();
    }
  }, [videoUrl]);

  if (!lesson) return <div>Loading...</div>;

  const videos = lesson.files?.filter(f => f.is_video) || [];

  return (
    <div className="lesson-player-enhanced">
      <div className="player-layout">
        <div className="main-content">
          <div className="video-container">
            <video
              ref={videoRef}
              controls
              controlsList="nodownload"
              style={{ width: '100%', maxHeight: '80vh' }}
            >
              {videoUrl && <source src={videoUrl} type="video/mp4" />}
              Your browser does not support the video tag.
            </video>
          </div>
          <div className="lesson-info">
            <h1>{lesson.title}</h1>
            {currentFile && <h3>Playing: {currentFile.filename}</h3>}
          </div>
        </div>

        <div className="sidebar">
          <div className="sidebar-section">
            <h2>Videos ({videos.length})</h2>
            <div className="files-list">
              {videos.map((file, i) => (
                <div
                  key={file.id}
                  className={`file-item ${currentFile?.id === file.id ? 'active' : ''}`}
                  onClick={() => setCurrentFile(file)}
                >
                  <div className="file-number">{i + 1}</div>
                  <div className="file-details">
                    <div className="file-name">{file.filename}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LessonPlayerEnhanced;
import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import '@videojs/themes/dist/city/index.css';
import API_URL, { authenticatedFetch } from '../config';
import './LessonPlayerEnhanced.css';

function LessonPlayerEnhanced() {
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [currentFile, setCurrentFile] = useState(null);
  const videoRef = useRef(null);
  const playerRef = useRef(null);

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

  // Initialize player once
  useLayoutEffect(() => {
    if (!videoRef.current || playerRef.current) return;

    const player = videojs(videoRef.current, {
      controls: true,
      fluid: true,
      playbackRates: [0.5, 1, 1.5, 2]
    });

    playerRef.current = player;

    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, []);

  // Load video URL when file changes and update player
  useEffect(() => {
    if (!currentFile?.is_video) return;

    // Wait for player to be ready
    const loadVideo = () => {
      if (!playerRef.current) {
        // Player not ready yet, wait a bit
        setTimeout(loadVideo, 100);
        return;
      }

      authenticatedFetch(`${API_URL}/api/stream/signed-url/${currentFile.id}`)
        .then(r => r.json())
        .then(data => {
          const url = `${API_URL}${data.url}`;
          playerRef.current.src({ src: url, type: 'video/mp4' });
          playerRef.current.load();
        })
        .catch(err => {
          console.error('Error loading video:', err);
        });
    };

    loadVideo();
  }, [currentFile]);

  if (!lesson) return <div>Loading...</div>;

  const videos = lesson.files?.filter(f => f.is_video) || [];

  return (
    <div className="lesson-player-enhanced">
      <div className="player-layout">
        <div className="main-content">
          <div className="video-container">
            <video ref={videoRef} className="video-js vjs-theme-city" />
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
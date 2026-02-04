import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  
  const videoRef = useRef(null);
  const playerRef = useRef(null);
  const progressInterval = useRef(null);
  const currentFileIdRef = useRef(null);
  const savedProgressSeconds = useRef(0);
  const hasSeekedToProgress = useRef(false);
  const lastProgressUpdate = useRef(0);

  const updateProgress = useCallback(() => {
    const player = playerRef.current;
    if (!currentFile || !currentFile.is_video || !player || player.isDisposed()) return;

    const currentTime = player.currentTime();
    const duration = player.duration();
    if (!duration || isNaN(duration) || duration === 0) return;

    const progress_seconds = Math.floor(currentTime);
    if (Math.abs(progress_seconds - lastProgressUpdate.current) < 1) return;

    lastProgressUpdate.current = progress_seconds;
    const progress_percentage = (currentTime / duration) * 100;
    const completed = currentTime >= duration - 2;

    authenticatedFetch(`${API_URL}/api/progress`, {
      method: 'POST',
      body: JSON.stringify({
        file_id: currentFile.id,
        progress_seconds,
        progress_percentage,
        completed
      })
    }).catch(err => console.error('Progress update failed:', err));
  }, [currentFile]);

  // Fetch lesson
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
  }, [lessonId]);

  // Set initial file
  useEffect(() => {
    if (lesson && lesson.files && lesson.files.length > 0 && !currentFile) {
      const firstIncomplete = lesson.files.find(f => f.is_video && !f.completed);
      const firstVideo = lesson.files.find(f => f.is_video);
      setCurrentFile(firstIncomplete || firstVideo || lesson.files[0]);
    }
  }, [lesson, currentFile]);

  // Fetch video URL when file changes
  useEffect(() => {
    const fetchVideoData = async () => {
      if (!currentFile || !currentFile.is_video) {
        setVideoUrl(null);
        currentFileIdRef.current = null;
        return;
      }

      if (currentFileIdRef.current === currentFile.id) return;

      currentFileIdRef.current = currentFile.id;
      hasSeekedToProgress.current = false;
      savedProgressSeconds.current = 0;
      lastProgressUpdate.current = 0;

      try {
        const [urlResponse, progressResponse] = await Promise.all([
          authenticatedFetch(`${API_URL}/api/stream/signed-url/${currentFile.id}`),
          authenticatedFetch(`${API_URL}/api/progress/file/${currentFile.id}`)
        ]);

        const urlData = await urlResponse.json();
        const progressData = await progressResponse.json();
        savedProgressSeconds.current = progressData.progress_seconds || 0;

        const signedUrl = `${API_URL}${urlData.url}`;
        setVideoUrl(signedUrl);
      } catch (err) {
        console.error('Failed to fetch video data:', err);
      }
    };

    fetchVideoData();
  }, [currentFile]);

  // Initialize and manage Video.js player
  useEffect(() => {
    if (!videoUrl) return;

    // Wait for React to render the video element
    const timeout = setTimeout(() => {
      if (!videoRef.current) {
        console.error('Video ref still not available after timeout');
        return;
      }

      // Dispose old player if exists
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }

      // Create new player
      const player = videojs(videoRef.current, {
        controls: true,
        responsive: true,
        fluid: true,
        playbackRates: [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
      });

      playerRef.current = player;

      // Set source
      player.src({ src: videoUrl, type: 'video/mp4' });

      // Seek to saved progress
      player.one('loadedmetadata', () => {
        if (!hasSeekedToProgress.current && savedProgressSeconds.current > 5) {
          player.currentTime(savedProgressSeconds.current);
          hasSeekedToProgress.current = true;
        }
      });

      // Progress tracking
      player.on('playing', () => {
        if (progressInterval.current) clearInterval(progressInterval.current);
        progressInterval.current = setInterval(() => {
          if (!player.paused() && !player.seeking()) updateProgress();
        }, 10000);
      });

      player.on('pause', () => {
        if (!player.seeking()) updateProgress();
      });

      player.on('ended', () => {
        updateProgress();
      });
    }, 0);

    return () => {
      clearTimeout(timeout);
      if (progressInterval.current) clearInterval(progressInterval.current);
      if (playerRef.current && !playerRef.current.isDisposed()) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [videoUrl, updateProgress]);

  const handleFileSelect = (file) => {
    if (currentFile && currentFile.is_video && playerRef.current) {
      updateProgress();
    }
    setCurrentFile(file);
  };

  if (loading) return <div className="loading">Loading lesson...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!lesson) return <div className="error">Lesson not found</div>;

  const videos = lesson.files?.filter(f => f.is_video) || [];
  const documents = lesson.files?.filter(f => f.is_document) || [];

  return (
    <div className="lesson-player-enhanced">
      <div className="player-layout">
        <div className="main-content">
          <div className="video-container">
            {currentFile && currentFile.is_video ? (
              <div className="video-wrapper">
                <div data-vjs-player>
                  <video ref={videoRef} className="video-js vjs-theme-city vjs-big-play-centered" />
                </div>
              </div>
            ) : (
              <div className="no-video"><p>Select a video to start watching</p></div>
            )}
          </div>

          <div className="lesson-info">
            <h1>{lesson.title}</h1>
            {lesson.description && <p className="description">{lesson.description}</p>}
            {currentFile && (
              <div className="current-file-info">
                <h3>Now Playing: {currentFile.filename}</h3>
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
                    <div className="file-number">{index + 1}</div>
                    <div className="file-details">
                      <div className="file-name">{file.filename}</div>
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
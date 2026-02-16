import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import API_URL, { authenticatedFetch } from '../config';
import './LessonPlayerEnhanced.css';

function LessonPlayerEnhanced() {
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [currentFile, setCurrentFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [buffering, setBuffering] = useState(false);
  const [connectionSpeed, setConnectionSpeed] = useState('unknown');
  const [bufferHealth, setBufferHealth] = useState(100);
  const videoRef = useRef(null);

  // Detect network connection speed
  const detectConnectionSpeed = useCallback(() => {
    if ('connection' in navigator) {
      const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      const effectiveType = connection?.effectiveType;

      if (effectiveType) {
        setConnectionSpeed(effectiveType);
        console.log(`Connection type detected: ${effectiveType}`);
      }

      // Listen for connection changes
      connection?.addEventListener('change', () => {
        setConnectionSpeed(connection.effectiveType);
        console.log(`Connection changed to: ${connection.effectiveType}`);
      });
    }
  }, []);

  // Get optimal preload strategy based on connection
  const getPreloadStrategy = useCallback(() => {
    switch (connectionSpeed) {
      case 'slow-2g':
      case '2g':
        return 'none'; // Don't preload anything
      case '3g':
        return 'metadata'; // Only load metadata
      case '4g':
      default:
        return 'metadata'; // Load metadata for better UX
    }
  }, [connectionSpeed]);

  // Monitor buffer health
  const updateBufferHealth = useCallback(() => {
    const video = videoRef.current;
    if (!video || !video.duration) return;

    try {
      const buffered = video.buffered;
      if (buffered.length > 0) {
        const currentTime = video.currentTime;
        // Find the buffered range that contains current playback position
        for (let i = 0; i < buffered.length; i++) {
          if (buffered.start(i) <= currentTime && buffered.end(i) >= currentTime) {
            const bufferedAhead = buffered.end(i) - currentTime;
            const bufferPercentage = Math.min((bufferedAhead / 30) * 100, 100); // 30 seconds buffer is 100%
            setBufferHealth(bufferPercentage);
            return;
          }
        }
      }
      setBufferHealth(0);
    } catch (e) {
      console.error('Error calculating buffer health:', e);
    }
  }, []);

  // Detect connection speed on mount
  useEffect(() => {
    detectConnectionSpeed();
  }, [detectConnectionSpeed]);

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

      // Seek to last watched position if available
      if (currentFile?.progress_seconds > 0) {
        const seekTime = currentFile.progress_seconds;
        videoRef.current.addEventListener('loadedmetadata', () => {
          videoRef.current.currentTime = seekTime;
        }, { once: true });
      }
    }
  }, [videoUrl, currentFile]);

  // Track and save progress
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !currentFile) return;

    let progressInterval;

    const saveProgress = () => {
      if (!video.duration || isNaN(video.duration)) return;

      const progressSeconds = Math.floor(video.currentTime);
      const progressPercentage = (video.currentTime / video.duration) * 100;
      const completed = progressPercentage >= 90;

      // Update local state optimistically
      setLesson(prev => ({
        ...prev,
        files: prev.files.map(f =>
          f.id === currentFile.id
            ? { ...f, progress_seconds: progressSeconds, progress_percentage: progressPercentage, completed }
            : f
        )
      }));

      // Save to backend
      authenticatedFetch(`${API_URL}/api/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_id: currentFile.id,
          progress_seconds: progressSeconds,
          progress_percentage: progressPercentage,
          completed
        })
      }).catch(err => console.error('Failed to save progress:', err));
    };

    const handlePlay = () => {
      setBuffering(false);
      // Save progress every 5 seconds while playing
      progressInterval = setInterval(saveProgress, 5000);
    };

    const handlePause = () => {
      clearInterval(progressInterval);
      saveProgress(); // Save immediately on pause
    };

    const handleEnded = () => {
      clearInterval(progressInterval);
      saveProgress(); // Save when video ends
    };

    const handleWaiting = () => {
      console.log('Video is buffering...');
      setBuffering(true);
    };

    const handlePlaying = () => {
      console.log('Video playing');
      setBuffering(false);
    };

    const handleStalled = () => {
      console.log('Video stalled');
      setBuffering(true);
    };

    const handleCanPlay = () => {
      setBuffering(false);
    };

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('ended', handleEnded);
    video.addEventListener('waiting', handleWaiting);
    video.addEventListener('playing', handlePlaying);
    video.addEventListener('stalled', handleStalled);
    video.addEventListener('canplay', handleCanPlay);
    video.addEventListener('progress', updateBufferHealth);

    return () => {
      clearInterval(progressInterval);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('ended', handleEnded);
      video.removeEventListener('waiting', handleWaiting);
      video.removeEventListener('playing', handlePlaying);
      video.removeEventListener('stalled', handleStalled);
      video.removeEventListener('canplay', handleCanPlay);
      video.removeEventListener('progress', updateBufferHealth);
    };
  }, [currentFile, videoUrl, updateBufferHealth]);

  // Monitor buffer health periodically
  useEffect(() => {
    const bufferInterval = setInterval(() => {
      updateBufferHealth();
    }, 1000);

    return () => clearInterval(bufferInterval);
  }, [updateBufferHealth]);

  if (!lesson) return <div>Loading...</div>;

  const videos = lesson.files?.filter(f => f.is_video) || [];

  return (
    <div className="lesson-player-enhanced">
      <div className="player-layout">
        <div className="main-content">
          <div className="video-container">
            <div className="video-wrapper">
              <video
                ref={videoRef}
                controls
                controlsList="nodownload"
                className="video-player"
                style={{ width: '100%', maxHeight: '80vh' }}
                preload={getPreloadStrategy()}
                playsInline
              >
                {videoUrl && <source src={videoUrl} type="video/mp4" />}
                Your browser does not support the video tag.
              </video>

              {/* Buffering Indicator */}
              {buffering && (
                <div className="buffering-overlay">
                  <div className="buffering-spinner"></div>
                  <p>Buffering...</p>
                  {connectionSpeed !== 'unknown' && (
                    <small>Connection: {connectionSpeed}</small>
                  )}
                </div>
              )}

              {/* Buffer Health Indicator */}
              {bufferHealth < 30 && !buffering && (
                <div className="buffer-warning">
                  <span>⚠️ Low buffer</span>
                </div>
              )}
            </div>
          </div>
          <div className="lesson-info">
            <h1>{lesson.title}</h1>

            {/* Connection Quality Info */}
            {connectionSpeed !== 'unknown' && (
              <div className={`connection-info connection-${connectionSpeed}`}>
                <span className="connection-icon">
                  {connectionSpeed === '4g' ? '📶' :
                   connectionSpeed === '3g' ? '📡' : '⚠️'}
                </span>
                <span className="connection-text">
                  Connection: <strong>{connectionSpeed.toUpperCase()}</strong>
                  {(connectionSpeed === 'slow-2g' || connectionSpeed === '2g') && (
                    <span className="connection-tip"> - Video optimized for your connection</span>
                  )}
                </span>
              </div>
            )}

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
                  className={`file-item ${currentFile?.id === file.id ? 'active' : ''} ${file.completed ? 'completed' : ''}`}
                  onClick={() => setCurrentFile(file)}
                >
                  <div className="file-number">{i + 1}</div>
                  {file.thumbnail_base64 && (
                    <div className="file-thumbnail">
                      <img src={file.thumbnail_base64} alt={file.filename} />
                    </div>
                  )}
                  <div className="file-details">
                    <div className="file-name">{file.filename}</div>
                    {(file.progress_percentage > 0 || file.completed) && (
                      <div className="mini-progress">
                        <div
                          className="mini-progress-fill"
                          style={{ width: `${file.progress_percentage || 0}%` }}
                        />
                      </div>
                    )}
                  </div>
                  {file.completed && <span className="check-mark">✓</span>}
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
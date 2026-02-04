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
  const [videoUrl, setVideoUrl] = useState(null);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const videoRef = useRef(null);
  const progressInterval = useRef(null);
  const shouldSeek = useRef(true);
  const currentFileIdRef = useRef(null);
  const hasSetInitialTime = useRef(false);
  const savedProgressSeconds = useRef(0);

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

  // Fetch signed URL and latest progress when the file ID changes
  useEffect(() => {
    const fetchVideoData = async () => {
      if (!currentFile || !currentFile.is_video) {
        setVideoUrl(null);
        currentFileIdRef.current = null;
        return;
      }

      // Only fetch new URL if the file ID has actually changed
      if (currentFileIdRef.current === currentFile.id) {
        return;
      }

      currentFileIdRef.current = currentFile.id;
      hasSetInitialTime.current = false;
      shouldSeek.current = true;
      savedProgressSeconds.current = 0;

      try {
        // Fetch both signed URL and latest progress in parallel
        const [urlResponse, progressResponse] = await Promise.all([
          authenticatedFetch(`${API_URL}/api/stream/signed-url/${currentFile.id}`),
          authenticatedFetch(`${API_URL}/api/progress/file/${currentFile.id}`)
        ]);

        const urlData = await urlResponse.json();
        const progressData = await progressResponse.json();

        // Store progress in ref for immediate access in onCanPlay
        savedProgressSeconds.current = progressData.progress_seconds || 0;

        // Update current file with latest progress from Redis/Firebase
        setCurrentFile(prev => ({
          ...prev,
          progress_seconds: progressData.progress_seconds || 0,
          progress_percentage: progressData.progress_percentage || 0,
          completed: progressData.completed || false
        }));

        // Construct full URL with signature and expiration
        const signedUrl = `${API_URL}${urlData.url}`;
        setVideoUrl(signedUrl);
      } catch (err) {
        console.error('Failed to fetch video data:', err);
        setError('Failed to load video');
      }
    };

    fetchVideoData();
  }, [currentFile]);

  // Handle video ready to play - seek to saved position
  const handleVideoCanPlay = useCallback(() => {
    const video = videoRef.current;
    if (!video || hasSetInitialTime.current) return;

    // Seek to saved position only once when video is ready
    // Use ref for progress_seconds to avoid race condition with state updates
    const progressToSeek = savedProgressSeconds.current;
    if (shouldSeek.current && progressToSeek > 5) {
      console.log(`Seeking to saved position: ${progressToSeek}s`);
      video.currentTime = progressToSeek;
    }
    hasSetInitialTime.current = true;
  }, []);

  useEffect(() => {
    if (currentFile && currentFile.is_video) {
      // Reset flag when switching videos
      hasSetInitialTime.current = false;

      // Update progress every 5 seconds
      progressInterval.current = setInterval(() => {
        const video = videoRef.current;
        if (video && !video.paused) {
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

  // Handle speed change
  const handleSpeedChange = (rate) => {
    setPlaybackRate(rate);
    if (videoRef.current) {
      videoRef.current.playbackRate = rate;
    }
    setShowSpeedMenu(false);
  };

  // Toggle CC (subtitles)
  const handleToggleCC = () => {
    const video = videoRef.current;
    if (!video || !video.textTracks || video.textTracks.length === 0) {
      alert('No subtitles available for this video');
      return;
    }

    // Toggle first text track
    const track = video.textTracks[0];
    if (track.mode === 'showing') {
      track.mode = 'hidden';
    } else {
      track.mode = 'showing';
    }
  };

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
            {currentFile && currentFile.is_video && videoUrl ? (
            <div className="video-wrapper">
              <video
                key={currentFile?.id}
                ref={videoRef}
                controls
                className="video-player"
                src={videoUrl}
                onEnded={handleVideoEnd}
                onPause={updateProgress}
                onCanPlay={handleVideoCanPlay}
                preload="metadata"
              />

              {/* Custom Controls Overlay */}
              <div className="custom-controls">
                {/* Speed Control */}
                <div className="control-group">
                  <button
                    className="control-btn"
                    onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                    title="Playback Speed"
                  >
                    <span className="speed-label">{playbackRate}x</span>
                  </button>

                  {showSpeedMenu && (
                    <div className="speed-menu">
                      {[0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2].map(rate => (
                        <button
                          key={rate}
                          className={`speed-option ${playbackRate === rate ? 'active' : ''}`}
                          onClick={() => handleSpeedChange(rate)}
                        >
                          {rate}x
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* CC Toggle */}
                <button
                  className="control-btn cc-btn"
                  onClick={handleToggleCC}
                  title="Closed Captions"
                >
                  CC
                </button>
              </div>
            </div>
            ) : currentFile && currentFile.is_video ? (
              <div className="no-video">
                <p>Loading video...</p>
              </div>
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

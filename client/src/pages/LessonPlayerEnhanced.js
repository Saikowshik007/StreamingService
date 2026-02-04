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
  const currentFileRef = useRef(null);
  const lessonRef = useRef(null);
  const hasSeekedToProgress = useRef(false);
  const lastProgressUpdate = useRef(0);
  const lessonRefreshInterval = useRef(null);
  const playerInitialized = useRef(false); // Track if player has EVER been initialized

  // Keep refs in sync with state
  useEffect(() => {
    currentFileRef.current = currentFile;
  }, [currentFile]);

  useEffect(() => {
    lessonRef.current = lesson;
  }, [lesson]);

  // Function to refresh lesson data to get updated progress
  const refreshLessonProgress = useCallback(async () => {
    try {
      const response = await authenticatedFetch(`${API_URL}/api/lessons/${lessonId}`);
      const data = await response.json();

      setLesson(prevLesson => {
        if (!prevLesson) return data;

        const hasChanges = data.files?.some((newFile, idx) => {
          const oldFile = prevLesson.files?.[idx];
          return !oldFile ||
                 newFile.progress_percentage !== oldFile.progress_percentage ||
                 newFile.progress_seconds !== oldFile.progress_seconds ||
                 newFile.completed !== oldFile.completed;
        });

        return hasChanges ? data : prevLesson;
      });
    } catch (err) {
      console.error('Failed to refresh lesson progress:', err);
    }
  }, [lessonId]);

  const updateProgress = useCallback(() => {
    const file = currentFileRef.current;
    const player = playerRef.current;

    if (!file || !file.is_video || !player || player.isDisposed()) return;

    const currentTime = player.currentTime();
    const duration = player.duration();

    if (!duration || isNaN(duration) || duration === 0) return;

    const progress_seconds = Math.floor(currentTime);

    if (Math.abs(progress_seconds - lastProgressUpdate.current) < 1) {
      return;
    }

    lastProgressUpdate.current = progress_seconds;
    const progress_percentage = (currentTime / duration) * 100;
    const completed = currentTime >= duration - 2;

    authenticatedFetch(`${API_URL}/api/progress`, {
      method: 'POST',
      body: JSON.stringify({
        file_id: file.id,
        progress_seconds,
        progress_percentage,
        completed
      })
    }).catch(err => {
      console.error('Failed to update progress:', err);
    });
  }, []);

  const saveProgressOnUnmount = useCallback(async () => {
    const file = currentFileRef.current;
    const player = playerRef.current;
    if (!file || !file.is_video || !player) return;

    const currentTime = player.currentTime();
    const duration = player.duration();

    if (!duration || isNaN(duration)) return;

    const progress_seconds = Math.floor(currentTime);
    const progress_percentage = (currentTime / duration) * 100;
    const completed = currentTime >= duration - 2;

    try {
      await authenticatedFetch(`${API_URL}/api/progress`, {
        method: 'POST',
        body: JSON.stringify({
          file_id: file.id,
          progress_seconds,
          progress_percentage,
          completed
        })
      });
      console.log(`Progress saved on unmount: ${progress_seconds}s`);
    } catch (err) {
      console.error('Failed to save progress on unmount:', err);
    }
  }, []);

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

    lessonRefreshInterval.current = setInterval(() => {
      refreshLessonProgress();
    }, 30000);

    return () => {
      saveProgressOnUnmount();

      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }

      if (lessonRefreshInterval.current) {
        clearInterval(lessonRefreshInterval.current);
      }
    };
  }, [lessonId, saveProgressOnUnmount, refreshLessonProgress]);

  useEffect(() => {
    if (lesson && lesson.files && lesson.files.length > 0 && !currentFile) {
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

      if (currentFileIdRef.current === currentFile.id) {
        return;
      }

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
        console.log(`Loaded progress for file ${currentFile.id}: ${savedProgressSeconds.current}s`);

        const signedUrl = `${API_URL}${urlData.url}`;
        setVideoUrl(signedUrl);
      } catch (err) {
        console.error('Failed to fetch video data:', err);
        setError('Failed to load video');
      }
    };

    fetchVideoData();
  }, [currentFile]);

  // Initialize player when video element is available
  useEffect(() => {
    console.log('Player init effect running', {
      hasVideoRef: !!videoRef.current,
      hasCurrentFile: !!currentFile,
      isVideo: currentFile?.is_video,
      playerInitialized: playerInitialized.current
    });

    // Need both video element AND we need currentFile to be a video
    if (!videoRef.current) {
      console.log('No video ref yet');
      return;
    }

    if (!currentFile?.is_video) {
      console.log('No current video file yet');
      return;
    }

    // If player is already initialized, do nothing
    if (playerInitialized.current) {
      console.log('Player already initialized, skipping');
      return;
    }

    console.log('🎬 INITIALIZING Video.js player for the first time');
    playerInitialized.current = true;

    const player = videojs(videoRef.current, {
      controls: true,
      responsive: true,
      fluid: true,
      playbackRates: [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
      controlBar: {
        children: [
          'playToggle',
          'volumePanel',
          'currentTimeDisplay',
          'timeDivider',
          'durationDisplay',
          'progressControl',
          'remainingTimeDisplay',
          'playbackRateMenuButton',
          'chaptersButton',
          'subtitlesButton',
          'captionsButton',
          'fullscreenToggle'
        ]
      },
      userActions: {
        doubleClick: false
      }
    });

    playerRef.current = player;
    console.log('✅ Player reference set:', !!playerRef.current);

    player.ready(() => {
      console.log('✅ Video.js player is ready');
    });

    // Double-tap to seek
    let lastTapTime = 0;
    const doubleTapThreshold = 300;

    const handleDoubleTap = (e) => {
      const currentTime = new Date().getTime();
      const tapTimeDiff = currentTime - lastTapTime;

      const rect = player.el().getBoundingClientRect();
      const tapX = (e.clientX || e.changedTouches?.[0]?.clientX) - rect.left;

      if (tapTimeDiff < doubleTapThreshold && tapTimeDiff > 0) {
        e.preventDefault();

        const videoWidth = rect.width;
        const leftThird = videoWidth / 3;
        const rightThird = videoWidth * 2 / 3;

        if (tapX < leftThird) {
          const newTime = Math.max(0, player.currentTime() - 10);
          player.currentTime(newTime);
          showSeekFeedback('backward');
        } else if (tapX > rightThird) {
          const newTime = Math.min(player.duration(), player.currentTime() + 10);
          player.currentTime(newTime);
          showSeekFeedback('forward');
        }

        lastTapTime = 0;
      } else {
        lastTapTime = currentTime;
      }
    };

    const showSeekFeedback = (direction) => {
      const videoContainer = document.querySelector('.video-container');
      if (!videoContainer) return;

      const feedback = document.createElement('div');
      feedback.className = `seek-feedback seek-${direction}`;
      feedback.innerHTML = direction === 'backward' ? '⏪ 10s' : '10s ⏩';
      videoContainer.appendChild(feedback);

      setTimeout(() => {
        feedback.remove();
      }, 800);
    };

    const videoElement = player.el();
    videoElement.addEventListener('touchend', handleDoubleTap);
    videoElement.addEventListener('click', handleDoubleTap);

    player.on('ended', () => {
      updateProgress();
      setTimeout(() => refreshLessonProgress(), 500);

      const file = currentFileRef.current;
      const currentLesson = lessonRef.current;
      if (currentLesson && currentLesson.files && file) {
        const currentIndex = currentLesson.files.findIndex(f => f.id === file.id);
        if (currentIndex < currentLesson.files.length - 1) {
          const nextFile = currentLesson.files[currentIndex + 1];
          if (nextFile.is_video) {
            setTimeout(() => setCurrentFile(nextFile), 1000);
          }
        }
      }
    });

    player.on('pause', () => {
      if (!player.seeking()) {
        updateProgress();
      }
    });

    const startProgressTracking = () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }

      progressInterval.current = setInterval(() => {
        if (player && !player.paused() && !player.seeking() && !player.isDisposed()) {
          updateProgress();
        }
      }, 10000);
    };

    player.on('playing', () => {
      startProgressTracking();
    });

    return () => {
      console.log('🧹 Disposing player on unmount');
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
        progressInterval.current = null;
      }
      if (playerRef.current && !playerRef.current.isDisposed()) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
      playerInitialized.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentFile?.is_video]); // Run when we have a video file (triggers rendering of video element)

  // Load video source when videoUrl changes
  useEffect(() => {
    const player = playerRef.current;
    if (!player || !videoUrl || player.isDisposed()) {
      console.log('Waiting for player and video URL...', {
        hasPlayer: !!player,
        hasUrl: !!videoUrl
      });
      return;
    }

    console.log('Loading video source:', videoUrl);

    if (progressInterval.current) {
      clearInterval(progressInterval.current);
      progressInterval.current = null;
    }

    player.src({
      src: videoUrl,
      type: 'video/mp4'
    });

    player.load();

    const onLoadedMetadata = () => {
      const progressToSeek = savedProgressSeconds.current;
      console.log('Video metadata loaded, duration:', player.duration());

      if (!hasSeekedToProgress.current && progressToSeek > 5) {
        console.log(`Seeking to saved position: ${progressToSeek}s`);
        player.currentTime(progressToSeek);
        hasSeekedToProgress.current = true;
      }
    };

    player.one('loadedmetadata', onLoadedMetadata);

    return () => {
      player.off('loadedmetadata', onLoadedMetadata);
    };
  }, [videoUrl]);

  const handleFileSelect = (file) => {
    if (currentFile && currentFile.is_video && playerRef.current) {
      updateProgress();
    }
    setCurrentFile(file);
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
                <div data-vjs-player>
                  <video
                    ref={videoRef}
                    className="video-js vjs-theme-city vjs-big-play-centered"
                  />
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
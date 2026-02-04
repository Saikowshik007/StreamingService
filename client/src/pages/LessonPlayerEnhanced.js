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
  const [playerReady, setPlayerReady] = useState(false);
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

    console.log('Initializing video.js player...');

    const player = videojs(videoRef.current, {
      controls: true,
      fluid: true,
      playbackRates: [0.5, 1, 1.5, 2],
      preload: 'auto',
      html5: {
        vhs: {
          overrideNative: true
        }
      }
    });

    // Wait for player to be ready
    player.ready(() => {
      console.log('Video.js player is ready');
      playerRef.current = player;
      setPlayerReady(true);
    });

    return () => {
      if (playerRef.current) {
        console.log('Disposing video.js player');
        playerRef.current.dispose();
        playerRef.current = null;
        setPlayerReady(false);
      }
    };
  }, []);

  // Load video URL when file changes and update player
  useEffect(() => {
    if (!currentFile?.is_video) {
      console.log('No video file to load');
      return;
    }

    if (!playerReady || !playerRef.current) {
      console.log('Player not ready yet, waiting...');
      return;
    }

    console.log('Loading video for file:', currentFile.id, currentFile.filename);

    const player = playerRef.current;

    // Pause current playback
    player.pause();

    const signedUrlEndpoint = `${API_URL}/api/stream/signed-url/${currentFile.id}`;
    console.log('Fetching signed URL from:', signedUrlEndpoint);

    authenticatedFetch(signedUrlEndpoint)
      .then(r => {
        console.log('Response status:', r.status, r.statusText);
        if (!r.ok) {
          throw new Error(`HTTP error! status: ${r.status}`);
        }
        return r.json();
      })
      .then(data => {
        console.log('Signed URL response:', data);

        // Construct the full stream URL
        const streamUrl = `${API_URL}${data.url}`;
        console.log('Final stream URL:', streamUrl);

        // Set the new source
        player.src({
          src: streamUrl,
          type: 'video/mp4'
        });

        // Reset and load the new video
        player.load();

        console.log('Video source set and loaded');
      })
      .catch(err => {
        console.error('Error loading video:', err);
        console.error('Error details:', err.message);

        // Show error in player
        player.error({
          code: 4,
          message: 'Failed to load video: ' + err.message
        });
      });
  }, [currentFile, playerReady]);

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
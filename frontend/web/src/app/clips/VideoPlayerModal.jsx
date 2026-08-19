'use client';

import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { apiFetch } from '@/lib/apiClient';
import styles from './video-player-modal.module.css';

export default function VideoPlayerModal({ clip, isOpen, onClose }) {
  const videoRef = useRef(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen || !clip) return;

    const loadVideo = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch clip as blob via authenticated route
        const response = await apiFetch(`/api/clips/stream/${clip.id}`);

        if (!response.ok) {
          throw new Error(`Failed to load video: ${response.status} ${response.statusText}`);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setVideoUrl(url);

        // Autoplay when modal opens
        setTimeout(() => {
          if (videoRef.current) {
            videoRef.current.play().catch(err => {
              console.warn('Autoplay failed (might be blocked by browser):', err);
            });
          }
        }, 100);
      } catch (err) {
        console.error('Video load error:', err);
        setError(err.message || 'Failed to load video');
      } finally {
        setLoading(false);
      }
    };

    loadVideo();

    return () => {
      // Cleanup: stop playback and revoke blob URL
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.src = '';
      }
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl);
      }
    };
  }, [isOpen, clip]);

  const handleClose = () => {
    // Stop video playback
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
    // Revoke blob URL
    if (videoUrl) {
      URL.revokeObjectURL(videoUrl);
      setVideoUrl(null);
    }
    onClose();
  };

  if (!isOpen || !clip) return null;

  return (
    <div className={styles.modalOverlay} onClick={handleClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={handleClose} title="Close (ESC)">
          <X size={24} />
        </button>

        <div className={styles.playerContainer}>
          <h2 className={styles.title}>{clip.title}</h2>

          {loading && (
            <div className={styles.loading}>
              <div className={styles.spinner}></div>
              <p>Loading video...</p>
            </div>
          )}

          {error && (
            <div className={styles.error}>
              <p className={styles.errorIcon}>⚠️</p>
              <p className={styles.errorMessage}>{error}</p>
              <button className={styles.retryBtn} onClick={() => window.location.reload()}>
                Try Again
              </button>
            </div>
          )}

          {videoUrl && !error && (
            <video
              ref={videoRef}
              className={styles.video}
              controls
              controlsList="nodownload"
              poster={clip.thumbnail_path || undefined}
              onError={(e) => {
                console.error('Video playback error:', e);
                setError('Video playback failed');
              }}
            >
              <source src={videoUrl} type="video/mp4" />
              Your browser does not support HTML5 video.
            </video>
          )}

          {clip.description && (
            <p className={styles.description}>{clip.description}</p>
          )}
        </div>
      </div>
    </div>
  );
}

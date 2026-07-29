'use client';

import styles from './vertical-preview.module.css';
import { X } from 'lucide-react';

export default function VerticalPreviewModal({ clip, isOpen, onClose }) {
  if (!isOpen || !clip) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose}>
          <X size={24} />
        </button>

        <div className={styles.previewContainer}>
          <h2>Vertical Preview (9:16)</h2>
          <p className={styles.subtitle}>How your clip looks on mobile platforms</p>

          <div className={styles.verticalFrame}>
            <div className={styles.videoPlaceholder}>
              {clip.thumbnail_path ? (
                <img src={clip.thumbnail_path} alt={clip.title} />
              ) : (
                <div className={styles.placeholder}>No thumbnail</div>
              )}
              <div className={styles.playOverlay}>▶</div>
            </div>
          </div>

          <div className={styles.info}>
            <div className={styles.infoRow}>
              <span className={styles.label}>Duration:</span>
              <span>{clip.duration_seconds}s</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.label}>Aspect Ratio:</span>
              <span>9:16 (Vertical)</span>
            </div>
            <div className={styles.platforms}>
              <span className={styles.label}>Perfect for:</span>
              <div className={styles.platformList}>
                <span>TikTok</span>
                <span>Instagram Reels</span>
                <span>YouTube Shorts</span>
              </div>
            </div>
          </div>

          <p className={styles.message}>
            This is how your clip will appear on vertical video platforms.
            When you export, the video will be automatically cropped to 9:16 format.
          </p>
        </div>
      </div>
    </div>
  );
}

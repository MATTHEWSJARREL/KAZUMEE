import { useState } from 'react';
import styles from './ClipCard.module.css';

/**
 * ClipCard Component
 * 
 * Displays a single clip video with metadata and share button.
 * Shows dynamic tags/pills based on clip attributes.
 * Includes video preview and quick-share functionality.
 */
export default function ClipCard({ clip, onShare }) {
  const [isHovered, setIsHovered] = useState(false);

  // Extract tags from clip metadata
  const tags = clip.tags || [];
  const sentiment = clip.sentiment || 'neutral';

  const getSentimentColor = (sent) => {
    switch (sent) {
      case 'positive':
        return '#00E5A0';
      case 'negative':
        return '#FF4C6A';
      case 'neutral':
      default:
        return '#7A7095';
    }
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  };

  return (
    <div
      className={styles.card}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Video preview/thumbnail */}
      <div className={styles.videoContainer}>
        <video
          className={styles.video}
          poster={clip.thumbnail_url}
          controls={isHovered}
          muted
        >
          <source src={clip.url} type="video/mp4" />
          Your browser does not support the video tag.
        </video>

        {/* Duration badge */}
        {clip.duration && (
          <div className={styles.duration}>
            {Math.floor(clip.duration / 60)}:{String(Math.floor(clip.duration % 60)).padStart(2, '0')}
          </div>
        )}

        {/* Share button overlay */}
        {isHovered && (
          <button className={styles.shareButton} onClick={onShare} title="Share this clip">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="18" cy="5" r="3" />
              <circle cx="6" cy="12" r="3" />
              <circle cx="18" cy="19" r="3" />
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
            </svg>
          </button>
        )}
      </div>

      {/* Metadata */}
      <div className={styles.metadata}>
        {/* Title and timestamp */}
        <h3 className={styles.title}>{clip.title || 'Untitled Clip'}</h3>
        <p className={styles.timestamp}>{formatDate(clip.created_at)}</p>

        {/* Tags/Pills */}
        {tags.length > 0 && (
          <div className={styles.tags}>
            {tags.slice(0, 3).map((tag, idx) => (
              <span key={idx} className={styles.tag}>
                {tag}
              </span>
            ))}
            {tags.length > 3 && (
              <span className={styles.tag}>+{tags.length - 3}</span>
            )}
          </div>
        )}

        {/* Sentiment indicator */}
        <div className={styles.sentiment} style={{ borderLeftColor: getSentimentColor(sentiment) }}>
          <span className={styles.sentimentLabel}>{sentiment}</span>
        </div>
      </div>
    </div>
  );
}

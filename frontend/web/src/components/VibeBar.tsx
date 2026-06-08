import styles from './VibeBar.module.css';

/**
 * VibeBar Component
 * 
 * Shows a visual representation of the streamer's current mood/vibe.
 * Displays as a gradient bar from negative to positive sentiment.
 * Score ranges from 0 (negative) to 100 (positive).
 */
export default function VibeBar({ score = 50 }) {
  // Clamp score between 0-100
  const normalizedScore = Math.max(0, Math.min(100, score));
  
  // Map score to sentiment label
  const getSentimentLabel = (s) => {
    if (s < 25) return 'Frustrated';
    if (s < 50) return 'Calm';
    if (s < 75) return 'Happy';
    return 'Hyped!';
  };

  // Map score to color
  const getSentimentColor = (s) => {
    if (s < 25) return '#FF4C6A'; // Red: negative
    if (s < 50) return '#F5A623'; // Amber: neutral-negative
    if (s < 75) return '#00E5A0'; // Green: neutral-positive
    return '#00D4FF'; // Cyan: positive
  };

  const sentiment = getSentimentLabel(normalizedScore);
  const color = getSentimentColor(normalizedScore);

  return (
    <div className={styles.container}>
      <div className={styles.vibeWrapper}>
        {/* Bar background */}
        <div className={styles.barBackground}>
          {/* Gradient track */}
          <div className={styles.gradientTrack} />
          
          {/* Filled portion */}
          <div
            className={styles.barFill}
            style={{
              width: `${normalizedScore}%`,
              backgroundColor: color,              boxShadow: `0 0 8px ${color}`,            }}
          />

          {/* Indicator marker */}
          <div
            className={styles.marker}
            style={{
              left: `${normalizedScore}%`,
              boxShadow: `0 0 12px ${color}`,
              borderColor: color,
            }}
          />
        </div>

        {/* Labels */}
        <div className={styles.labels}>
          <span className={styles.minLabel}>Frustrated</span>
          <span className={styles.maxLabel}>Hyped</span>
        </div>
      </div>

      {/* Current sentiment */}
      <div className={styles.sentimentBadge} style={{ borderColor: color }}>
        <span className={styles.sentimentDot} style={{ backgroundColor: color }} />
        <span className={styles.sentimentText}>{sentiment}</span>
      </div>
    </div>
  );
}

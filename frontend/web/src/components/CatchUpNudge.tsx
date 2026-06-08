import { useEffect, useState } from 'react';
import styles from './CatchUpNudge.module.css';

/**
 * CatchUpNudge Component
 * 
 * Appears automatically after 45 seconds on viewer pages.
 * Suggests user to "Catch Me Up" on recent streamer activity.
 * Does not re-show in same session (uses sessionStorage flag).
 */
export default function CatchUpNudge({ onCatchUp, onDismiss }) {
  const [isVisible, setIsVisible] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(45);
  
  const NUDGE_KEY = 'catchup_nudge_dismissed';
  const NUDGE_DELAY = 45000; // 45 seconds

  useEffect(() => {
    // Check if user already dismissed in this session
    const wasDismissed = sessionStorage.getItem(NUDGE_KEY);
    if (wasDismissed) {
      return;
    }

    // Start countdown timer
    const countdownInterval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(countdownInterval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Show nudge after 45 seconds
    const showTimer = setTimeout(() => {
      setIsVisible(true);
      clearInterval(countdownInterval);
    }, NUDGE_DELAY);

    return () => {
      clearTimeout(showTimer);
      clearInterval(countdownInterval);
    };
  }, []);

  const handleDismiss = () => {
    sessionStorage.setItem(NUDGE_KEY, 'true');
    setIsVisible(false);
    if (onDismiss) {
      onDismiss();
    }
  };

  const handleCatchUp = () => {
    sessionStorage.setItem(NUDGE_KEY, 'true');
    setIsVisible(false);
    if (onCatchUp) {
      onCatchUp();
    }
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className={styles.nudgeContainer}>
      <div className={styles.nudgeCard}>
        {/* Icon */}
        <div className={styles.icon}>
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="1" />
            <path d="M12 1v6m0 6v6" />
            <path d="M4.22 4.22l4.24 4.24m3.08 3.08l4.24 4.24" />
            <path d="M1 12h6m6 0h6" />
            <path d="M4.22 19.78l4.24-4.24m3.08-3.08l4.24-4.24" />
          </svg>
        </div>

        {/* Content */}
        <div className={styles.content}>
          <h3 className={styles.title}>Catch Me Up!</h3>
          <p className={styles.description}>
            See what's been happening in the streamer's world.
          </p>
        </div>

        {/* Actions */}
        <div className={styles.actions}>
          <button
            className={styles.dismissButton}
            onClick={handleDismiss}
            title="Dismiss this suggestion"
          >
            Not now
          </button>
          <button
            className={styles.catchUpButton}
            onClick={handleCatchUp}
            title="Load recent activity"
          >
            Show me
          </button>
        </div>

        {/* Close button */}
        <button
          className={styles.closeButton}
          onClick={handleDismiss}
          aria-label="Close notification"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

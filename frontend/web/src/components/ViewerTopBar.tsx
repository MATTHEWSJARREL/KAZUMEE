import styles from './ViewerTopBar.module.css';

/**
 * ViewerTopBar Component
 * 
 * Simplified header for viewer page.
 * Shows streamer avatar, name, and status.
 * No heavy elements - just essential info.
 */
export default function ViewerTopBar({ streamer }) {
  const isLive = streamer.is_streaming || false;

  return (
    <header className={styles.topBar}>
      <div className={styles.container}>
        {/* Avatar and info section */}
        <div className={styles.streamerInfo}>
          {/* Avatar */}
          {streamer.avatar_url && (
            <img
              src={streamer.avatar_url}
              alt={streamer.name}
              className={styles.avatar}
            />
          )}

          {/* Name and status */}
          <div className={styles.textContent}>
            <h1 className={styles.name}>{streamer.name || 'Unknown Streamer'}</h1>
            {streamer.bio && (
              <p className={styles.bio}>{streamer.bio}</p>
            )}
          </div>

          {/* Live badge if streaming */}
          {isLive && (
            <div className={styles.liveBadge}>
              <span className={styles.liveDot} />
              <span className={styles.liveText}>LIVE</span>
            </div>
          )}
        </div>

        {/* Follow/Subscribe button */}
        <button className={styles.followButton}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm3.5-9H13V8.5c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5V11H8.5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5H11v2.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5V13h2.5c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5z" />
          </svg>
          Follow
        </button>
      </div>
    </header>
  );
}

'use client';

import styles from './ClipsGrid.module.css';

export default function ClipsGrid({ clips = [] }) {
  if (!clips || clips.length === 0) {
    return (
      <div className={styles.empty}>
        <p>No clips generated yet</p>
        <p className={styles.hint}>Clips will appear here as moments are detected during your stream</p>
      </div>
    );
  }

  return (
    <div className={styles.grid}>
      {clips.map((clip) => (
        <div key={clip.id} className={styles.card}>
          <div className={styles.thumbnail}>
            <div className={styles.placeholder}>🎬</div>
          </div>
          <div className={styles.info}>
            <h3>{clip.title}</h3>
            <div className={styles.stats}>
              <span className={styles.views}>{clip.views.toLocaleString()} views</span>
              <span className={styles.time}>{clip.timestamp}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

'use client';

import styles from './StreamStats.module.css';

export default function StreamStats() {
  return (
    <div className={styles.container}>
      <div className={styles.stat}>
        <div className={styles.indicator} style={{ background: '#10b981' }}>●</div>
        <div>
          <div className={styles.label}>Live Status</div>
          <div className={styles.value}>ONLINE</div>
        </div>
      </div>

      <div className={styles.stat}>
        <div className={styles.label}>Viewers</div>
        <div className={styles.bigValue}>45</div>
      </div>

      <div className={styles.stat}>
        <div className={styles.label}>Moments Detected</div>
        <div className={styles.bigValue}>3</div>
      </div>

      <div className={styles.stat}>
        <div className={styles.label}>Clips Generated</div>
        <div className={styles.bigValue}>3</div>
      </div>

      <div className={styles.stat}>
        <div className={styles.label}>Stream Duration</div>
        <div className={styles.bigValue}>2h 14m</div>
      </div>
    </div>
  );
}

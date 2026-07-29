'use client';

import styles from './MomentStats.module.css';

export default function MomentStats({ data }) {
  if (!data) return null;

  const chatPercent = Math.min(100, (data.chat_velocity || 0) / 10 * 100);
  const audioPercent = Math.min(100, (data.audio_peak || 0) * 100);
  const timeSinceMoment = Math.round(data.time_since_last_moment || 0);

  return (
    <div className={styles.container}>
      <h2>🎯 Moment Detection Status</h2>

      <div className={styles.grid}>
        {/* Chat Velocity */}
        <div className={styles.card}>
          <div className={styles.label}>Chat Velocity</div>
          <div className={styles.value}>
            {(data.chat_velocity || 0).toFixed(1)} msg/sec
          </div>
          <div className={styles.barContainer}>
            <div
              className={styles.bar}
              style={{ width: `${chatPercent}%` }}
            />
          </div>
          <div className={styles.threshold}>
            Threshold: 5.0 msg/sec
          </div>
        </div>

        {/* Audio Peak */}
        <div className={styles.card}>
          <div className={styles.label}>Audio Peak</div>
          <div className={styles.value}>
            {(data.audio_peak || 0).toFixed(2)}
          </div>
          <div className={styles.barContainer}>
            <div
              className={styles.bar}
              style={{ width: `${audioPercent}%` }}
            />
          </div>
          <div className={styles.threshold}>
            Threshold: 0.60
          </div>
        </div>

        {/* Status */}
        <div className={styles.card}>
          <div className={styles.label}>Detector Status</div>
          <div className={styles.status}>
            <span className={styles.indicator}>●</span>
            Active
          </div>
          <div className={styles.info}>
            {timeSinceMoment < 30 ? (
              <>Moment just detected!</>
            ) : (
              <>Last moment: {timeSinceMoment}s ago</>
            )}
          </div>
        </div>

        {/* Active Windows */}
        <div className={styles.card}>
          <div className={styles.label}>Signal Buffers</div>
          <div className={styles.value}>
            {data.active_chat_windows || 0} chat / {data.active_audio_peaks || 0} audio
          </div>
          <div className={styles.info}>
            Real-time event tracking
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { TrendingUp, Zap, Clock, BarChart3 } from 'lucide-react';
import { getApiUrl } from '@/utils/api';
import styles from './analytics.module.css';

export default function AnalyticsDashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchAnalytics = async () => {
    try {
      const res = await fetch('${getApiUrl()}/api/clips/analytics/stream-summary');
      if (!res.ok) throw new Error('Failed to fetch analytics');
      const data = await res.json();
      setAnalytics(data);
    } catch (err) {
      console.error('Analytics error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className={styles.loading}>Loading analytics...</div>;
  if (!analytics) return <div className={styles.empty}>No analytics data</div>;

  return (
    <div className={styles.container}>
      <h1>Stream Analytics</h1>

      {/* Key Metrics */}
      <div className={styles.metricsGrid}>
        <div className={styles.metric}>
          <div className={styles.icon}><Zap size={24} /></div>
          <div className={styles.content}>
            <div className={styles.label}>Moments Detected</div>
            <div className={styles.value}>{analytics.moments_detected}</div>
          </div>
        </div>

        <div className={styles.metric}>
          <div className={styles.icon}><TrendingUp size={24} /></div>
          <div className={styles.content}>
            <div className={styles.label}>Clips Generated</div>
            <div className={styles.value}>{analytics.clips_generated}</div>
          </div>
        </div>

        <div className={styles.metric}>
          <div className={styles.icon}><Clock size={24} /></div>
          <div className={styles.content}>
            <div className={styles.label}>Total Duration</div>
            <div className={styles.value}>{analytics.total_duration_minutes}m</div>
          </div>
        </div>

        <div className={styles.metric}>
          <div className={styles.icon}><BarChart3 size={24} /></div>
          <div className={styles.content}>
            <div className={styles.label}>Avg Quality Score</div>
            <div className={styles.value}>{(analytics.avg_quality_score * 10).toFixed(1)}/10</div>
          </div>
        </div>
      </div>

      {/* Quality Distribution */}
      <div className={styles.section}>
        <h2>Quality Distribution</h2>
        <div className={styles.distributionGrid}>
          <div className={styles.distributionItem}>
            <div className={styles.qualityHigh}></div>
            <span>High Quality ({analytics.quality_distribution.high})</span>
          </div>
          <div className={styles.distributionItem}>
            <div className={styles.qualityMedium}></div>
            <span>Medium Quality ({analytics.quality_distribution.medium})</span>
          </div>
          <div className={styles.distributionItem}>
            <div className={styles.qualityLow}></div>
            <span>Low Quality ({analytics.quality_distribution.low})</span>
          </div>
        </div>
      </div>

      {/* Clip Status Breakdown */}
      <div className={styles.section}>
        <h2>Clip Status</h2>
        <div className={styles.statusGrid}>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Pending Review</span>
            <span className={styles.statusValue}>{analytics.by_status.pending}</span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Approved</span>
            <span className={styles.statusValue}>{analytics.by_status.approved}</span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Rejected</span>
            <span className={styles.statusValue}>{analytics.by_status.rejected}</span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Deleted</span>
            <span className={styles.statusValue}>{analytics.by_status.deleted}</span>
          </div>
        </div>
      </div>

      {/* Clips List */}
      <div className={styles.section}>
        <h2>Generated Clips</h2>
        <div className={styles.clipsList}>
          {analytics.clips.map((clip) => (
            <div key={clip.id} className={styles.clipRow}>
              <span className={styles.clipTitle}>{clip.title}</span>
              <span className={styles.clipDuration}>{clip.duration}s</span>
              <span className={styles.clipQuality}>
                Score: {(clip.quality_score * 10).toFixed(1)}/10
              </span>
              <span className={`${styles.clipStatus} ${styles[`status_${clip.status}`]}`}>
                {clip.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

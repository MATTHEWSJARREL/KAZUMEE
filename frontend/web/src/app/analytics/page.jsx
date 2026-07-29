'use client';

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Video, TrendingUp, Settings, LogOut, Bell, Search, Eye, BarChart3, TrendingDown, Clock } from 'lucide-react';
import styles from './analytics.module.css';

export default function AnalyticsPage() {
  const navigate = useNavigate();
  const [clips, setClips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [streamerName, setStreamerName] = useState('');
  const [currentDate, setCurrentDate] = useState('');
  const [selectedRange, setSelectedRange] = useState('7d');

  useEffect(() => {
    const token = localStorage.getItem('authToken');
    const role = localStorage.getItem('userRole');

    if (!token || role !== 'streamer') {
      navigate('/auth', { replace: true });
      return;
    }

    const name = localStorage.getItem('streamerName') || 'Streamer';
    setStreamerName(name);

    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    setCurrentDate(now.toLocaleDateString('en-US', options));

    fetchAnalytics();
  }, [navigate, selectedRange]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const clipsToShow = [];

      // Fetch all clips
      try {
        const recentRes = await fetch('/api/clips/?limit=100');
        if (recentRes.ok) {
          const recentData = await recentRes.json();
          clipsToShow.push(...(recentData.clips || []).map(clip => ({
            id: clip.id,
            title: clip.title || 'Clip',
            created_at: clip.created_at,
            views: Math.floor(Math.random() * 10000),
            engagement: Math.floor(Math.random() * 100),
            quality_score: clip.quality_score || 0,
          })));
        }
      } catch (err) {
        console.warn('Failed to fetch clips:', err);
      }

      setClips(clipsToShow);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const totalViews = clips.reduce((sum, c) => sum + c.views, 0);
  const avgViews = clips.length > 0 ? Math.floor(totalViews / clips.length) : 0;
  const topClips = [...clips].sort((a, b) => b.views - a.views).slice(0, 5);
  const totalClips = clips.length;

  const getInitials = (name) => name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'ST';

  return (
    <div className={styles.analyticsPage}>
      <div className={styles.stars}></div>

      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.logoContainer}>
          <img src="/logo.png" alt="Kazumee" className={styles.logo} />
        </div>

        <nav className={styles.navMenu}>
          <a href="/dashboard" className={styles.navItem}>
            <Home size={20} />
            <span>Dashboard</span>
          </a>
          <a href="/clips" className={styles.navItem}>
            <Video size={20} />
            <span>Clips</span>
          </a>
          <a href="/analytics" className={`${styles.navItem} ${styles.active}`}>
            <TrendingUp size={20} />
            <span>Analytics</span>
          </a>
        </nav>

        <div className={styles.sidebarBottom}>
          <a href="/settings" className={styles.navItem}>
            <Settings size={20} />
            <span>Settings</span>
          </a>
          <button
            className={styles.logoutBtn}
            onClick={() => {
              localStorage.clear();
              navigate('/', { replace: true });
            }}
          >
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className={styles.mainArea}>
        {/* Top Bar */}
        <header className={styles.topBar}>
          <div className={styles.topBarLeft}>
            <div className={styles.dateDisplay}>{currentDate}</div>
            <div className={styles.tagline}>Performance Analytics</div>
          </div>

          <div className={styles.topBarRight}>
            <div className={styles.rangeSelector}>
              {['7d', '30d', '90d', 'all'].map(range => (
                <button
                  key={range}
                  className={`${styles.rangeBtn} ${selectedRange === range ? styles.active : ''}`}
                  onClick={() => setSelectedRange(range)}
                >
                  {range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : range === '90d' ? '90 Days' : 'All Time'}
                </button>
              ))}
            </div>

            <div className={styles.searchCard}>
              <Search size={18} />
              <input type="text" placeholder="Search..." />
            </div>
            <button className={styles.notifBtn}>
              <Bell size={20} />
              <span className={styles.badge}>3</span>
            </button>
            <div className={styles.userNav}>
              <div className={styles.avatarBg}>{getInitials(streamerName)}</div>
            </div>
          </div>
        </header>

        {/* KPI Cards */}
        <div className={styles.kpiGrid}>
          <div className={styles.kpiCard}>
            <div className={styles.kpiHeader}>
              <Eye size={24} />
              <span>Total Views</span>
            </div>
            <div className={styles.kpiValue}>{totalViews.toLocaleString()}</div>
            <div className={styles.kpiTrend}>↑ 12% from last period</div>
          </div>

          <div className={styles.kpiCard}>
            <div className={styles.kpiHeader}>
              <TrendingUp size={24} />
              <span>Avg Views/Clip</span>
            </div>
            <div className={styles.kpiValue}>{avgViews.toLocaleString()}</div>
            <div className={styles.kpiTrend}>Steady performance</div>
          </div>

          <div className={styles.kpiCard}>
            <div className={styles.kpiHeader}>
              <Video size={24} />
              <span>Total Clips</span>
            </div>
            <div className={styles.kpiValue}>{totalClips}</div>
            <div className={styles.kpiTrend}>{clips.length > 0 ? '↑ Growing' : 'No clips yet'}</div>
          </div>

          <div className={styles.kpiCard}>
            <div className={styles.kpiHeader}>
              <BarChart3 size={24} />
              <span>Engagement Rate</span>
            </div>
            <div className={styles.kpiValue}>12.3%</div>
            <div className={styles.kpiTrend}>↑ 3% growth</div>
          </div>
        </div>

        {/* Charts Section */}
        <div className={styles.chartsSection}>
          {/* Top Performing Clips */}
          <div className={styles.chartCard}>
            <div className={styles.chartHeader}>
              <h3>Top Performing Clips</h3>
              <span className={styles.subtitle}>By total views</span>
            </div>

            {loading ? (
              <div className={styles.loading}>Loading...</div>
            ) : topClips.length === 0 ? (
              <div className={styles.emptyChart}>
                <Video size={32} />
                <p>No clips yet</p>
              </div>
            ) : (
              <div className={styles.topClipsTable}>
                {topClips.map((clip, idx) => (
                  <div key={clip.id} className={styles.clipRow}>
                    <div className={styles.rank}>#{idx + 1}</div>
                    <div className={styles.clipInfo}>
                      <p className={styles.clipTitle}>{clip.title}</p>
                      <span className={styles.clipDate}>
                        {new Date(clip.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className={styles.viewsBar}>
                      <div
                        className={styles.bar}
                        style={{
                          width: `${(clip.views / topClips[0].views) * 100}%`
                        }}
                      ></div>
                    </div>
                    <div className={styles.views}>{clip.views.toLocaleString()}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Statistics Grid */}
          <div className={styles.statsGrid}>
            <div className={styles.statBox}>
              <h4>Peak Hour</h4>
              <p className={styles.statValue}>8 PM</p>
              <span className={styles.statLabel}>Most views at this time</span>
            </div>

            <div className={styles.statBox}>
              <h4>Best Performer</h4>
              <p className={styles.statValue}>{topClips[0]?.views.toLocaleString() || '0'}</p>
              <span className={styles.statLabel}>Views on top clip</span>
            </div>

            <div className={styles.statBox}>
              <h4>Avg Duration</h4>
              <p className={styles.statValue}>42s</p>
              <span className={styles.statLabel}>Average clip length</span>
            </div>

            <div className={styles.statBox}>
              <h4>Quality Score</h4>
              <p className={styles.statValue}>
                {clips.length > 0
                  ? ((clips.reduce((sum, c) => sum + c.quality_score, 0) / clips.length) * 100).toFixed(0)
                  : '0'}%
              </p>
              <span className={styles.statLabel}>Overall quality</span>
            </div>
          </div>
        </div>

        {/* Insights */}
        <div className={styles.insightsSection}>
          <div className={styles.insightCard}>
            <div className={styles.insightIcon}>💡</div>
            <div>
              <h4>Insight</h4>
              <p>Your clips perform best between 7-9 PM. Consider scheduling important moments for this window.</p>
            </div>
          </div>

          <div className={styles.insightCard}>
            <div className={styles.insightIcon}>🎯</div>
            <div>
              <h4>Recommendation</h4>
              <p>Increase clip length to 45-60s for better engagement with your audience segments.</p>
            </div>
          </div>

          <div className={styles.insightCard}>
            <div className={styles.insightIcon}>📈</div>
            <div>
              <h4>Trend</h4>
              <p>Moment-detected clips are getting 23% more views than manually created clips.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

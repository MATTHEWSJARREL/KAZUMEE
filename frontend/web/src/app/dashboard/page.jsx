'use client';

import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Video, TrendingUp, Settings, LogOut, Bell, Search, MoreVertical } from 'lucide-react';
import { useMomentWebSocket } from '@/hooks/useMomentWebSocket';
import { apiFetch, getAuthToken } from '@/lib/apiClient';
import styles from './dashboard.module.css';

export default function Dashboard() {
  const navigate = useNavigate();
  const [clips, setClips] = useState([]);
  const [momentStatus, setMomentStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [streamerName, setStreamerName] = useState('');
  const [streamerEmail, setStreamerEmail] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentDate, setCurrentDate] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const [clipping, setClipping] = useState(false);
  const [agentStatus, setAgentStatus] = useState(null);

  // Check actual agent registry status (source of truth)
  const checkAgentRegistry = useCallback(async () => {
    try {
      const res = await apiFetch('/api/agent/registry-status');
      if (res.ok) {
        const data = await res.json();
        const streamerIdNum = parseInt(localStorage.getItem('streamerId') || '0', 10);
        const isConnected = data.connected_streamer_ids?.includes(streamerIdNum);
        setAgentStatus(isConnected ? 'online' : 'offline');
        console.log(`[AGENT] Registry check: streamer=${streamerIdNum}, connected=${isConnected}`);
      }
    } catch (err) {
      console.warn('[AGENT] Registry check failed:', err);
    }
  }, []);

  // REAL FEATURE: Manually trigger clip capture
  const handleClipNow = async () => {
    setClipping(true);
    try {
      const res = await apiFetch('/api/moments/capture', { method: 'POST' });
      const data = await res.json();

      if (data.status === 'success') {
        // Show success toast
        alert('✅ Clip command sent! Your agent is capturing...');
        // Refresh clips in a moment
        setTimeout(fetchClipsAndStatus, 3000);
      } else if (data.status === 'agent_offline') {
        // Show error: agent not connected
        alert('❌ ' + data.message);
        setAgentStatus('offline');
      } else {
        alert('⚠️ ' + (data.message || 'Clip capture failed'));
      }
    } catch (err) {
      console.error('Clip capture error:', err);
      alert('❌ Failed to send clip command. Check your connection.');
    } finally {
      setClipping(false);
    }
  };

  // Handle real-time moment detection via WebSocket
  const handleMomentDetected = useCallback((momentData) => {
    // Refresh clips and status when moment is detected
    fetchClipsAndStatus();
  }, []);

  const handleStatusUpdate = useCallback((statusData) => {
    // Update moment status in real-time
    setMomentStatus(prev => ({
      ...prev,
      ...statusData
    }));
  }, []);

  const { isConnected } = useMomentWebSocket(handleMomentDetected, handleStatusUpdate);

  useEffect(() => {
    setWsConnected(isConnected);
    // Check agent registry whenever WebSocket connection status changes
    checkAgentRegistry();
  }, [isConnected, checkAgentRegistry]);

  // Fetch clips and status (used both on init and when moments detected)
  const fetchClipsAndStatus = useCallback(async () => {
    try {
      // Fetch status
      const statusRes = await apiFetch('/api/moments/status');
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setMomentStatus(statusData.detector);
      }

      const clipsToShow = [];

      // Fetch all clips from /api/clips/ endpoint with error handling
      try {
        const allClipsRes = await apiFetch('/api/clips/?limit=50');

        // Handle 403 Forbidden - viewer trying to access streamer features
        if (allClipsRes.status === 403) {
          const errorData = await allClipsRes.json();
          if (errorData.detail?.includes('streamer')) {
            // This is expected - show friendly message to viewers
            setClips([]);
            setLoading(false);
            return;
          }
        }

        if (allClipsRes.ok) {
          const allClipsData = await allClipsRes.json();
          console.log('✅ All clips fetched:', allClipsData.clips?.length || 0);

          // Transform and show all clips
          if (allClipsData.clips && Array.isArray(allClipsData.clips)) {
            clipsToShow.push(...allClipsData.clips.map(clip => ({
              id: clip.id,
              title: clip.title || 'Untitled Clip',
              description: clip.description || 'Auto-generated clip',
              views: 0,
              timestamp: new Date(clip.created_at).toLocaleString(),
              duration: clip.duration_seconds ? `${Math.round(clip.duration_seconds)}s` : '—',
              status: clip.status || 'pending'
            })));
          }
        } else {
          console.warn('All clips fetch returned:', allClipsRes.status);
        }
      } catch (err) {
        console.warn('Failed to fetch clips:', err);
      }

      setClips(clipsToShow);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  }, []);

  useEffect(() => {
    const token = getAuthToken();
    const role = localStorage.getItem('userRole');

    console.log('Dashboard auth check:', { token, role });

    if (!token || role !== 'streamer') {
      console.log('❌ Auth failed, redirecting to /auth');
      navigate('/auth', { replace: true });
      return;
    }

    console.log('✓ Auth valid, loading dashboard');
    setIsAuthenticated(true);

    // Set real date
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    setCurrentDate(now.toLocaleDateString('en-US', options));

    const name = localStorage.getItem('streamerName') || 'Streamer';
    const email = localStorage.getItem('streamerEmail') || 'streamer@email.com';
    setStreamerName(name);
    setStreamerEmail(email);

    // Initial fetch
    fetchClipsAndStatus().finally(() => setLoading(false));

    // Check agent registry initially and on interval (every 3s)
    checkAgentRegistry();
    const agentStatusInterval = setInterval(checkAgentRegistry, 3000);

    return () => clearInterval(agentStatusInterval);
  }, [fetchClipsAndStatus, navigate, checkAgentRegistry]);

  if (!isAuthenticated || loading) {
    return <div className={styles.loadingContainer}>Loading...</div>;
  }

  const initials = streamerName?.split(' ').map(n => n[0]).join('').toUpperCase() || 'ST';

  return (
    <div className={styles.dashboard}>
      <div className={styles.stars}></div>

      {/* Sidebar - Left */}
      <aside className={styles.sidebar}>
        <div className={styles.logoContainer}>
          <img src="/logo.png" alt="Kazumee" className={styles.logo} />
        </div>

        <nav className={styles.navMenu}>
          <a href="/dashboard" className={`${styles.navItem} ${styles.active}`}>
            <Home size={20} />
            <span>Dashboard</span>
          </a>
          <a href="/clips" className={styles.navItem}>
            <Video size={20} />
            <span>Clips</span>
          </a>
          <a href="/analytics" className={styles.navItem}>
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

      {/* Main Area */}
      <div className={styles.mainArea}>
        {/* Top Bar - Redesigned */}
        <header className={styles.topBar}>
          <div className={styles.topBarLeft}>
            <div className={styles.dateDisplay}>{currentDate}</div>
            <div className={styles.tagline}>Stream better with Kazumee</div>
          </div>

          <div className={styles.topBarRight}>
            <div className={styles.searchCard}>
              <Search size={18} />
              <input type="text" placeholder="Search clips..." />
            </div>
            {/* WebSocket connection indicator */}
            <div title={wsConnected ? 'Live connection active' : 'Connecting...'} style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: wsConnected ? '#10b981' : '#f59e0b',
              animation: wsConnected ? 'none' : 'pulse 2s infinite',
              cursor: 'help'
            }}>
            </div>
            <button className={styles.notifBtn}>
              <Bell size={20} />
            </button>
            <div className={styles.userNav}>
              <div className={styles.avatarBg}>{initials}</div>
              <div className={styles.userInfo}>
                <div>{streamerName}</div>
              </div>
            </div>
          </div>
        </header>

        {/* Content Area - Creates the "U" shape */}
        <div className={styles.contentWrapper}>
          {/* Main Content */}
          <div className={styles.mainContent}>
            {/* Heading */}
            <div className={styles.heading}>
              <div>
                <h1>Dashboard</h1>
              </div>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                {agentStatus && (
                  <span style={{
                    fontSize: '13px',
                    fontWeight: '500',
                    color: agentStatus === 'online' ? '#10b981' : '#f59e0b'
                  }}>
                    {agentStatus === 'online' ? '✓ Agent Online' : '⚠️ Agent Offline'}
                  </span>
                )}
                <button
                  className={styles.newBtn}
                  onClick={handleClipNow}
                  disabled={clipping}
                  style={{
                    opacity: clipping ? 0.6 : 1,
                    backgroundColor: '#9333ea',
                    fontWeight: '600'
                  }}
                  title="Manually trigger a clip capture on your stream"
                >
                  {clipping ? '🎬 Capturing...' : '🎬 Clip Now'}
                </button>
              </div>
            </div>

            {/* Stats Grid - Creates width for U shape */}
            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>STATUS</div>
                <div className={styles.statValue}>
                  <span className={styles.liveDot}></span>
                  LIVE
                </div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>VIEWERS</div>
                <div className={styles.statValue}>{momentStatus?.active_viewers !== undefined ? momentStatus.active_viewers : '—'}</div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>MOMENTS</div>
                <div className={styles.statValue}>{momentStatus?.total_moments || clips.filter(c => c.status === 'published').length}</div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>CLIPS GENERATED</div>
                <div className={styles.statValue}>{clips.length}</div>
              </div>
            </div>

            {/* Clips Section */}
            <section className={styles.section}>
              <div className={styles.sectionHeader}>
                <h2>Auto-Generated Clips</h2>
                <div className={styles.filterTabs}>
                  <button className={`${styles.filterBtn} ${styles.active}`}>All</button>
                  <button className={styles.filterBtn}>Published</button>
                  <button className={styles.filterBtn}>Processing</button>
                </div>
              </div>

              <div className={styles.clipsList}>
                {clips.length === 0 ? (
                  <div className={styles.empty}>
                    <Video size={48} />
                    <p>No clips generated yet</p>
                    <span>Clips appear here as moments are detected during your stream</span>
                  </div>
                ) : (
                  clips.map((clip) => (
                    <div key={clip.id} className={styles.clipCard}>
                      <div className={styles.clipLeft}>
                        <div className={styles.clipIcon}>
                          <Video size={24} />
                        </div>
                        <div className={styles.clipInfo}>
                          <h3>{clip.title}</h3>
                          <p>{clip.description}</p>
                          <div className={styles.clipMeta}>
                            <span>{clip.duration}</span>
                            <span>👁️ {clip.views}</span>
                            <span>{clip.timestamp}</span>
                          </div>
                        </div>
                      </div>
                      <div className={styles.clipRight}>
                        {clip.status === 'published' && (
                          <span className={styles.publishedBadge}>✓ Published</span>
                        )}
                        {clip.status === 'processing' && (
                          <div className={styles.processingBadge}>Processing...</div>
                        )}
                        <button className={styles.moreBtn}>
                          <MoreVertical size={18} />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>

          {/* Right Panel - Completes the U shape */}
          <aside className={styles.rightPanel}>
            {momentStatus && (
              <div className={styles.card}>
                <h3>Moment Detection</h3>
                <div className={styles.stat}>
                  <span>Chat Velocity</span>
                  <strong>{(momentStatus.chat_velocity || 0).toFixed(1)} msg/s</strong>
                </div>
                <div className={styles.stat}>
                  <span>Audio Peak</span>
                  <strong>{(momentStatus.audio_peak || 0).toFixed(2)}</strong>
                </div>
                <div className={styles.stat}>
                  <span>Last Moment</span>
                  <strong>{(momentStatus.time_since_last_moment || 0).toFixed(0)}s ago</strong>
                </div>
              </div>
            )}

            <div className={styles.card}>
              <h3>Quick Stats</h3>
              <div className={styles.stat}>
                <span>Avg Clip Length</span>
                <strong>{clips.length > 0 ? '41.7s' : '--'}</strong>
              </div>
              <div className={styles.stat}>
                <span>Total Views</span>
                <strong>{clips.length > 0 ? clips.reduce((sum, c) => sum + (c.views || 0), 0).toLocaleString() : '0'}</strong>
              </div>
              <div className={styles.stat}>
                <span>Published Clips</span>
                <strong>{clips.filter(c => c.status === 'published').length}</strong>
              </div>
            </div>

            <div className={styles.card}>
              <h3>Activity</h3>
              <div className={styles.activity}>
                <span className={styles.dot}></span>
                <div>
                  <p>Detection Active</p>
                  <small>Now</small>
                </div>
              </div>
              <div className={styles.activity}>
                <span className={styles.dot}></span>
                <div>
                  <p>Clip Published</p>
                  <small>5 min ago</small>
                </div>
              </div>
              <div className={styles.activity}>
                <span className={styles.dot}></span>
                <div>
                  <p>Moment Detected</p>
                  <small>12 min ago</small>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

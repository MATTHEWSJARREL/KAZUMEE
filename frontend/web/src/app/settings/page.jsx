'use client';

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Video, TrendingUp, Settings as SettingsIcon, LogOut, Bell, Search, Save, Eye, Lock, Volume2, Zap } from 'lucide-react';
import { apiFetch, getAuthToken } from '@/lib/apiClient';
import styles from './settings.module.css';

export default function SettingsPage() {
  const navigate = useNavigate();
  const [streamerName, setStreamerName] = useState('');
  const [streamerEmail, setStreamerEmail] = useState('');
  const [currentDate, setCurrentDate] = useState('');
  const [activeTab, setActiveTab] = useState('general');
  const [saving, setSaving] = useState(false);

  // Agent state
  const [agentToken, setAgentToken] = useState('');
  const [agentStatus, setAgentStatus] = useState('offline');
  const [agentMetadata, setAgentMetadata] = useState(null);
  const [loadingAgent, setLoadingAgent] = useState(false);
  const [generatingToken, setGeneratingToken] = useState(false);
  const [tokenCopied, setTokenCopied] = useState(false);

  // Settings state
  const [settings, setSettings] = useState({
    // General
    displayName: '',
    email: '',

    // Detection
    sensitivity: 0.7,
    detectionEnabled: true,

    // Auto-publish
    autoPublish: false,
    autoPublishPlatforms: [],
    minimumQualityScore: 0.6,

    // Notifications
    notifyOnClip: true,
    notifyOnPublish: true,
    notifyEmail: true,
  });

  useEffect(() => {
    const token = getAuthToken();
    const role = localStorage.getItem('userRole');

    if (!token || role !== 'streamer') {
      navigate('/auth', { replace: true });
      return;
    }

    const name = localStorage.getItem('streamerName') || 'Streamer';
    const email = localStorage.getItem('streamerEmail') || 'streamer@email.com';
    setStreamerName(name);
    setStreamerEmail(email);

    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    setCurrentDate(now.toLocaleDateString('en-US', options));

    // Load settings from localStorage
    const saved = localStorage.getItem('kazumi_settings');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSettings(prev => ({ ...prev, ...parsed }));
      } catch (e) {
        console.error('Failed to load settings:', e);
      }
    }

    setSettings(prev => ({
      ...prev,
      displayName: name,
      email: email
    }));

    // Fetch agent token metadata and status
    fetchAgentMetadata();
    fetchAgentStatus();
    // Poll status every 5 seconds
    const statusInterval = setInterval(fetchAgentStatus, 5000);
    return () => clearInterval(statusInterval);
  }, [navigate]);

  const fetchAgentMetadata = async () => {
    try {
      const response = await apiFetch('/api/agent/token');
      if (response.ok) {
        const data = await response.json();
        setAgentMetadata(data);
      }
    } catch (error) {
      console.error('Failed to fetch agent metadata:', error);
    }
  };

  const fetchAgentStatus = async () => {
    try {
      const response = await apiFetch('/api/agent/status');
      if (response.ok) {
        const data = await response.json();
        setAgentStatus(data.online ? 'connected' : 'offline');
      }
    } catch (error) {
      console.error('Failed to fetch agent status:', error);
    }
  };

  const generateNewAgentToken = async () => {
    setGeneratingToken(true);
    try {
      const response = await apiFetch('/api/agent/token', {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        setAgentToken(data.token);
        setTokenCopied(false);
        await fetchAgentMetadata();
        alert('New agent token generated! Copy it now—it won\'t be shown again.');
      } else {
        alert('Failed to generate token');
      }
    } catch (error) {
      console.error('Failed to generate token:', error);
      alert('Error generating token');
    } finally {
      setGeneratingToken(false);
    }
  };

  const copyAgentToken = () => {
    if (agentToken) {
      navigator.clipboard.writeText(agentToken);
      setTokenCopied(true);
      setTimeout(() => setTokenCopied(false), 2000);
    }
  };

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      localStorage.setItem('kazumi_settings', JSON.stringify(settings));
      // Success feedback
      setTimeout(() => setSaving(false), 500);
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaving(false);
    }
  };

  const handlePlatformToggle = (platform) => {
    setSettings(prev => ({
      ...prev,
      autoPublishPlatforms: prev.autoPublishPlatforms.includes(platform)
        ? prev.autoPublishPlatforms.filter(p => p !== platform)
        : [...prev.autoPublishPlatforms, platform]
    }));
  };

  const getInitials = (name) => name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'ST';

  return (
    <div className={styles.settingsPage}>
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
          <a href="/analytics" className={styles.navItem}>
            <TrendingUp size={20} />
            <span>Analytics</span>
          </a>
        </nav>

        <div className={styles.sidebarBottom}>
          <a href="/settings" className={`${styles.navItem} ${styles.active}`}>
            <SettingsIcon size={20} />
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
            <div className={styles.tagline}>Settings</div>
          </div>

          <div className={styles.topBarRight}>
            <div className={styles.searchCard}>
              <Search size={18} />
              <input type="text" placeholder="Search settings..." />
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

        {/* Settings Container */}
        <div className={styles.settingsContainer}>
          {/* Tabs */}
          <div className={styles.tabs}>
            <button
              className={`${styles.tab} ${activeTab === 'general' ? styles.active : ''}`}
              onClick={() => setActiveTab('general')}
            >
              General
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'detection' ? styles.active : ''}`}
              onClick={() => setActiveTab('detection')}
            >
              Moment Detection
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'publishing' ? styles.active : ''}`}
              onClick={() => setActiveTab('publishing')}
            >
              Publishing
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'notifications' ? styles.active : ''}`}
              onClick={() => setActiveTab('notifications')}
            >
              Notifications
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'agent' ? styles.active : ''}`}
              onClick={() => setActiveTab('agent')}
            >
              Agent Token
            </button>
          </div>

          {/* Tab Content */}
          <div className={styles.tabContent}>
            {/* General Tab */}
            {activeTab === 'general' && (
              <div className={styles.section}>
                <h2>Profile Settings</h2>
                <div className={styles.formGroup}>
                  <label>Display Name</label>
                  <input
                    type="text"
                    value={settings.displayName}
                    onChange={(e) => handleSettingChange('displayName', e.target.value)}
                    placeholder="Your streamer name"
                  />
                </div>

                <div className={styles.formGroup}>
                  <label>Email</label>
                  <input
                    type="email"
                    value={settings.email}
                    onChange={(e) => handleSettingChange('email', e.target.value)}
                    placeholder="your@email.com"
                    disabled
                  />
                </div>

                <div className={styles.infoBox}>
                  <h4>Account Information</h4>
                  <p>Email: <strong>{streamerEmail}</strong></p>
                  <p>Role: <strong>Streamer</strong></p>
                  <p>Member since: <strong>July 22, 2026</strong></p>
                </div>
              </div>
            )}

            {/* Detection Tab */}
            {activeTab === 'detection' && (
              <div className={styles.section}>
                <h2>Moment Detection Settings</h2>

                <div className={styles.toggleGroup}>
                  <div className={styles.toggleHeader}>
                    <Zap size={20} />
                    <div>
                      <h3>Enable Moment Detection</h3>
                      <p>Auto-detect streaming highlights in real-time</p>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.detectionEnabled}
                    onChange={(e) => handleSettingChange('detectionEnabled', e.target.checked)}
                    className={styles.toggle}
                  />
                </div>

                {settings.detectionEnabled && (
                  <>
                    <div className={styles.sliderGroup}>
                      <label>Detection Sensitivity</label>
                      <div className={styles.sliderContainer}>
                        <span className={styles.sliderLabel}>Low</span>
                        <input
                          type="range"
                          min="0.1"
                          max="1"
                          step="0.1"
                          value={settings.sensitivity}
                          onChange={(e) => handleSettingChange('sensitivity', parseFloat(e.target.value))}
                          className={styles.slider}
                        />
                        <span className={styles.sliderLabel}>High</span>
                      </div>
                      <p className={styles.helperText}>
                        Current: <strong>{(settings.sensitivity * 100).toFixed(0)}%</strong>
                        <br />
                        Higher sensitivity detects more moments, but may include false positives
                      </p>
                    </div>

                    <div className={styles.presets}>
                      <label>Quick Presets</label>
                      <div className={styles.presetButtons}>
                        <button
                          className={styles.presetBtn}
                          onClick={() => handleSettingChange('sensitivity', 0.4)}
                        >
                          Conservative
                        </button>
                        <button
                          className={styles.presetBtn}
                          onClick={() => handleSettingChange('sensitivity', 0.7)}
                        >
                          Balanced
                        </button>
                        <button
                          className={styles.presetBtn}
                          onClick={() => handleSettingChange('sensitivity', 1.0)}
                        >
                          Aggressive
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Publishing Tab */}
            {activeTab === 'publishing' && (
              <div className={styles.section}>
                <h2>Auto-Publishing Settings</h2>

                <div className={styles.toggleGroup}>
                  <div className={styles.toggleHeader}>
                    <Video size={20} />
                    <div>
                      <h3>Auto-Publish Clips</h3>
                      <p>Automatically publish clips to selected platforms</p>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.autoPublish}
                    onChange={(e) => handleSettingChange('autoPublish', e.target.checked)}
                    className={styles.toggle}
                  />
                </div>

                {settings.autoPublish && (
                  <>
                    <div className={styles.platformSelection}>
                      <label>Publish To</label>
                      <div className={styles.platforms}>
                        {['YouTube', 'TikTok', 'Instagram'].map(platform => (
                          <div key={platform} className={styles.platformOption}>
                            <input
                              type="checkbox"
                              id={platform}
                              checked={settings.autoPublishPlatforms.includes(platform)}
                              onChange={() => handlePlatformToggle(platform)}
                            />
                            <label htmlFor={platform}>{platform}</label>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className={styles.sliderGroup}>
                      <label>Minimum Quality Score</label>
                      <div className={styles.sliderContainer}>
                        <span className={styles.sliderLabel}>20%</span>
                        <input
                          type="range"
                          min="0.2"
                          max="1"
                          step="0.1"
                          value={settings.minimumQualityScore}
                          onChange={(e) => handleSettingChange('minimumQualityScore', parseFloat(e.target.value))}
                          className={styles.slider}
                        />
                        <span className={styles.sliderLabel}>100%</span>
                      </div>
                      <p className={styles.helperText}>
                        Only publish clips with quality above {(settings.minimumQualityScore * 100).toFixed(0)}%
                      </p>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Agent Tab */}
            {activeTab === 'agent' && (
              <div className={styles.section}>
                <h2>Kazumee Autonomous Clipping Agent</h2>
                <p style={{ marginBottom: '20px', color: '#888' }}>
                  Download and run the agent on your PC to auto-clip moments from OBS.
                </p>

                {/* Agent Status */}
                <div style={{
                  background: agentStatus === 'connected' ? '#0f3460' : '#3a1a1a',
                  border: `1px solid ${agentStatus === 'connected' ? '#16213e' : '#5a2a2a'}`,
                  borderRadius: '8px',
                  padding: '15px',
                  marginBottom: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '15px'
                }}>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: agentStatus === 'connected' ? '#4CAF50' : '#ff6b6b',
                    animation: agentStatus === 'connected' ? 'pulse 2s infinite' : 'none'
                  }} />
                  <div>
                    <h4 style={{ margin: '0 0 5px 0' }}>
                      Agent: <span style={{ color: agentStatus === 'connected' ? '#4CAF50' : '#ff6b6b' }}>
                        {agentStatus === 'connected' ? 'Connected' : 'Offline'}
                      </span>
                    </h4>
                    <p style={{ margin: 0, fontSize: '12px', color: '#aaa' }}>
                      {agentStatus === 'connected'
                        ? 'Your agent is running and ready to capture clips'
                        : 'Run KazumeeAgent.exe to start capturing'}
                    </p>
                  </div>
                </div>

                {/* Download Button */}
                <div style={{
                  background: 'linear-gradient(135deg, #0f9f6c 0%, #0d7a54 100%)',
                  borderRadius: '8px',
                  padding: '20px',
                  marginBottom: '20px',
                  textAlign: 'center'
                }}>
                  <h4 style={{ marginTop: 0, marginBottom: '10px' }}>Get Started</h4>
                  <p style={{ margin: '0 0 15px 0', fontSize: '14px' }}>
                    Download the agent for Windows (single-click install)
                  </p>
                  <a
                    href="https://github.com/MATTHEWSJARREL/KAZUMEE/releases"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'inline-block',
                      background: '#ffffff',
                      color: '#0f9f6c',
                      padding: '12px 30px',
                      borderRadius: '4px',
                      textDecoration: 'none',
                      fontWeight: 'bold',
                      fontSize: '16px'
                    }}
                  >
                    Download KazumeeAgent.exe
                  </a>
                </div>

                {/* Agent Token Section */}
                <div style={{
                  background: '#1a1a2e',
                  border: '1px solid #16213e',
                  borderRadius: '8px',
                  padding: '20px',
                  marginBottom: '20px'
                }}>
                  <h4 style={{ marginTop: 0, marginBottom: '15px' }}>Agent Token</h4>

                  {!agentToken && agentMetadata && (
                    <p style={{ color: '#aaa', fontSize: '14px', marginBottom: '15px' }}>
                      {agentMetadata.exists
                        ? `Token expires: ${new Date(agentMetadata.expires_at).toLocaleDateString()}`
                        : 'No active token. Generate one below.'}
                    </p>
                  )}

                  {agentToken ? (
                    <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
                      <input
                        type="text"
                        value={agentToken}
                        readOnly
                        style={{
                          flex: 1,
                          background: '#0f3460',
                          border: 'none',
                          color: '#00d4ff',
                          padding: '12px',
                          borderRadius: '4px',
                          fontFamily: 'monospace',
                          fontSize: '12px'
                        }}
                      />
                      <button
                        onClick={copyAgentToken}
                        style={{
                          background: tokenCopied ? '#4CAF50' : '#0f9f6c',
                          color: 'white',
                          border: 'none',
                          padding: '10px 20px',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontWeight: 'bold',
                          transition: 'all 0.2s'
                        }}
                      >
                        {tokenCopied ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                  ) : null}

                  <button
                    onClick={generateNewAgentToken}
                    disabled={generatingToken}
                    style={{
                      width: '100%',
                      background: '#0f3460',
                      color: '#00d4ff',
                      border: '1px solid #16213e',
                      padding: '12px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: 'bold'
                    }}
                  >
                    {generatingToken ? 'Generating...' : agentToken ? 'Show New Token' : 'Generate Agent Token'}
                  </button>

                  {agentToken && (
                    <p style={{ fontSize: '12px', color: '#ff9800', marginTop: '10px', margin: '10px 0 0 0' }}>
                      ⚠️ Copy this token now — it won't be shown again!
                    </p>
                  )}
                </div>

                {/* Setup Instructions */}
                <div style={{
                  background: '#0f3460',
                  border: '1px solid #16213e',
                  borderRadius: '8px',
                  padding: '15px',
                  marginBottom: '20px'
                }}>
                  <h4 style={{ marginTop: 0 }}>Setup (60 seconds)</h4>
                  <ol style={{ margin: '10px 0', paddingLeft: '20px', fontSize: '14px' }}>
                    <li>Download KazumeeAgent.exe above</li>
                    <li>Run it (double-click)</li>
                    <li>Paste your token from the step above</li>
                    <li>Agent sits in your system tray, ready to clip</li>
                  </ol>
                </div>

                {/* Security */}
                <div style={{
                  background: '#1a1a2e',
                  border: '1px solid #ff6b6b',
                  borderRadius: '8px',
                  padding: '15px'
                }}>
                  <h4 style={{ marginTop: 0, color: '#ff6b6b' }}>Security</h4>
                  <p style={{ fontSize: '14px', margin: '5px 0' }}>
                    • Never share your agent token
                  </p>
                  <p style={{ fontSize: '14px', margin: '5px 0' }}>
                    • Only run on your own PC
                  </p>
                  <p style={{ fontSize: '14px', margin: '5px 0' }}>
                    • Requires OBS with replay buffer enabled
                  </p>
                </div>
              </div>
            )}

            {/* Notifications Tab */}
            {activeTab === 'notifications' && (
              <div className={styles.section}>
                <h2>Notification Preferences</h2>

                <div className={styles.toggleGroup}>
                  <div className={styles.toggleHeader}>
                    <span>📹</span>
                    <div>
                      <h3>Notify on Clip Created</h3>
                      <p>Get notified when a new clip is created</p>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.notifyOnClip}
                    onChange={(e) => handleSettingChange('notifyOnClip', e.target.checked)}
                    className={styles.toggle}
                  />
                </div>

                <div className={styles.toggleGroup}>
                  <div className={styles.toggleHeader}>
                    <span>✅</span>
                    <div>
                      <h3>Notify on Clip Published</h3>
                      <p>Get notified when a clip is published</p>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.notifyOnPublish}
                    onChange={(e) => handleSettingChange('notifyOnPublish', e.target.checked)}
                    className={styles.toggle}
                  />
                </div>

                <div className={styles.toggleGroup}>
                  <div className={styles.toggleHeader}>
                    <span>📧</span>
                    <div>
                      <h3>Email Notifications</h3>
                      <p>Receive email updates about your clips</p>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.notifyEmail}
                    onChange={(e) => handleSettingChange('notifyEmail', e.target.checked)}
                    className={styles.toggle}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Save Button */}
          <div className={styles.saveSection}>
            <button
              className={`${styles.saveBtn} ${saving ? styles.saving : ''}`}
              onClick={handleSave}
              disabled={saving}
            >
              <Save size={20} />
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

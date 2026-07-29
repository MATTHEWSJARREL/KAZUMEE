'use client';

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Video, TrendingUp, Settings as SettingsIcon, LogOut, Bell, Search, Save, Eye, Lock, Volume2, Zap } from 'lucide-react';
import styles from './settings.module.css';

export default function SettingsPage() {
  const navigate = useNavigate();
  const [streamerName, setStreamerName] = useState('');
  const [streamerEmail, setStreamerEmail] = useState('');
  const [currentDate, setCurrentDate] = useState('');
  const [activeTab, setActiveTab] = useState('general');
  const [saving, setSaving] = useState(false);

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
    const token = localStorage.getItem('authToken');
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
  }, [navigate]);

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

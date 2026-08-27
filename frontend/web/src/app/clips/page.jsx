'use client';

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Video, TrendingUp, Settings, LogOut, Bell, Search, Eye, CheckCircle, Clock, Trash2, Download, Share2, Copy, Check, Smartphone, ThumbsUp, ThumbsDown, Play, Loader } from 'lucide-react';
import { apiFetch, getAuthToken } from '@/lib/apiClient';
import styles from './clips.module.css';
import VerticalPreviewModal from './VerticalPreviewModal';
import VideoPlayerModal from './VideoPlayerModal';

// Helper: Format duration seconds to "M:SS"
const formatDuration = (seconds) => {
  if (!seconds) return '—';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

// Helper: Format timestamp to relative time ("2h ago")
const formatRelativeTime = (isoString) => {
  if (!isoString) return '—';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

export default function ClipsPage() {
  const navigate = useNavigate();
  const [clips, setClips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [streamerName, setStreamerName] = useState('');
  const [currentDate, setCurrentDate] = useState('');
  const [showExportModal, setShowExportModal] = useState(false);
  const [selectedClip, setSelectedClip] = useState(null);
  const [showVerticalPreview, setShowVerticalPreview] = useState(false);
  const [previewClip, setPreviewClip] = useState(null);
  const [selectedClips, setSelectedClips] = useState(new Set());
  const [batchExporting, setBatchExporting] = useState(false);
  const [playingClip, setPlayingClip] = useState(null);
  const [showVideoPlayer, setShowVideoPlayer] = useState(false);
  const [exportSettings, setExportSettings] = useState({
    preset: 'tiktok',
    platforms: ['tiktok'],
    watermark: false,
    watermarkText: 'Created with Kazumee'
  });
  const [exporting, setExporting] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    const token = getAuthToken();
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

    fetchClips();
  }, [navigate]);

  const handleBatchExport = async () => {
    if (selectedClips.size === 0) {
      alert('Please select clips to export');
      return;
    }

    setBatchExporting(true);
    try {
      const res = await apiFetch('/api/clips/batch-export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          clip_ids: Array.from(selectedClips),
          platforms: ['tiktok', 'shorts', 'reels'],
          watermark: false
        })
      });

      if (!res.ok) throw new Error('Export failed');
      const data = await res.json();
      alert(`✓ Queued ${data.total_jobs} export(s) for ${data.clips_exported} clip(s)`);
      setSelectedClips(new Set());
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setBatchExporting(false);
    }
  };

  const toggleClipSelection = (clipId) => {
    const newSelected = new Set(selectedClips);
    if (newSelected.has(clipId)) {
      newSelected.delete(clipId);
    } else {
      newSelected.add(clipId);
    }
    setSelectedClips(newSelected);
  };

  const handlePlayClip = (clip) => {
    setPlayingClip(clip);
    setShowVideoPlayer(true);
  };

  const handleBurnCaptions = async (clip) => {
    setBurningCaption(clip.id);
    setBurningStatus('Burning captions...');
    try {
      const res = await apiFetch(`/api/clips/${clip.id}/burn-captions`, {
        method: 'POST'
      });

      if (!res.ok) {
        const error = await res.json();
        setBurningStatus(`Error: ${error.detail}`);
        return;
      }

      const data = await res.json();
      setBurningStatus(`✓ Captions burned! File: ${data.output_path}`);
      setTimeout(() => {
        setBurningCaption(null);
        setBurningStatus('');
      }, 3000);
    } catch (err) {
      setBurningStatus(`Error: ${err.message}`);
    }
  };

  const fetchClips = async () => {
    try {
      setLoading(true);
      const clipsToShow = [];

      // Fetch all clips from /api/clips/
      try {
        console.log('Fetching all clips...');
        const allRes = await apiFetch('/api/clips/?limit=50');
        console.log('All clips response:', allRes.status);
        if (allRes.ok) {
          const allData = await allRes.json();
          console.log('✅ All clips:', allData.clips?.length || 0);
          if (allData.clips && Array.isArray(allData.clips)) {
            // Process clips and fetch thumbnails as blobs
            const clipsWithThumbnails = await Promise.all(
              allData.clips.map(async (clip) => {
                let thumbnailUrl = null;

                // Fetch thumbnail as blob (requires auth)
                if (clip.urls?.thumbnail) {
                  try {
                    const thumbRes = await apiFetch(clip.urls.thumbnail.replace(window.location.origin, ''));
                    if (thumbRes.ok) {
                      const blob = await thumbRes.blob();
                      thumbnailUrl = window.URL.createObjectURL(blob);
                    }
                  } catch (err) {
                    console.warn(`Failed to load thumbnail for clip ${clip.id}:`, err);
                  }
                }

                return {
                  id: clip.id,
                  title: clip.title || 'Clip',
                  description: clip.description || 'Auto-generated clip',
                  created_at: clip.created_at,
                  duration_seconds: clip.duration_seconds,
                  quality_score: clip.quality_score,
                  status: clip.status || 'pending',
                  file_path: clip.file_path,
                  urls: {
                    thumbnail: thumbnailUrl,
                    stream: clip.urls?.stream,
                    download: clip.urls?.download
                  }
                };
              })
            );
            clipsToShow.push(...clipsWithThumbnails);
          }
        } else {
          console.error('Clips fetch failed:', allRes.status);
        }
      } catch (err) {
        console.warn('Failed to fetch clips:', err);
      }

      console.log('Total clips to show:', clipsToShow.length);
      setClips(clipsToShow);
    } catch (error) {
      console.error('Failed to fetch clips:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredClips = filter === 'all'
    ? clips
    : clips.filter(c => c.status === filter);

  const getInitials = (name) => name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'ST';

  const handleShare = async (clip) => {
    const clipUrl = `${window.location.origin}/clips/${clip.id}`;
    try {
      await navigator.clipboard.writeText(clipUrl);
      setCopiedId(clip.id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      alert('Failed to copy link');
    }
  };

  const handleDownload = async (clip) => {
    if (!clip.id) {
      alert('Clip ID not available');
      return;
    }
    try {
      const response = await apiFetch(`/api/clips/download/${clip.id}`);
      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = (clip.title || `clip_${clip.id}`).replace(/\s+/g, '_') + '.mp4';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      console.log('✓ Clip downloaded successfully');
    } catch (err) {
      console.error('Download failed:', err);
      alert(`❌ Failed to download clip: ${err.message}`);
    }
  };

  const handleApprove = async (clip) => {
    try {
      const response = await apiFetch('/api/clips/review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          clip_id: clip.id,
          action: 'approve',
          notes: 'Approved from dashboard'
        })
      });
      if (response.ok) {
        alert('✓ Clip approved!');
        fetchClips();
      } else {
        alert('❌ Approve failed');
      }
    } catch (error) {
      console.error('Approve error:', error);
      alert('❌ Error: ' + error.message);
    }
  };

  const handleReject = async (clip) => {
    if (!confirm(`Reject "${clip.title}"?`)) return;
    try {
      const response = await apiFetch('/api/clips/review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          clip_id: clip.id,
          action: 'reject',
          notes: 'Rejected from dashboard'
        })
      });
      if (response.ok) {
        alert('✓ Clip rejected');
        fetchClips();
      } else {
        alert('❌ Reject failed');
      }
    } catch (error) {
      console.error('Reject error:', error);
      alert('❌ Error: ' + error.message);
    }
  };

  const handleDelete = async (clip) => {
    if (!confirm(`Delete "${clip.title}"?`)) return;
    try {
      const response = await apiFetch(`/api/clips/${clip.id}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        console.log('Clip deleted');
        alert('✓ Clip deleted!');
        fetchClips(); // Refresh
      } else {
        alert('❌ Delete failed');
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('❌ Error: ' + error.message);
    }
  };

  const handleExport = async () => {
    if (!selectedClip) return;
    setExporting(true);
    try {
      const response = await apiFetch(`/api/clips/batch-export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          clip_ids: [selectedClip.id],
          platforms: [exportSettings.preset],
          watermark: exportSettings.watermark
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('✅ Export queued:', data);
        alert(`✅ Clip queued for export to ${exportSettings.preset.toUpperCase()}!`);
        setShowExportModal(false);
        fetchClips(); // Refresh clips
      } else {
        const error = await response.text();
        console.error('Export failed:', error);
        alert('❌ Export failed. Check console.');
      }
    } catch (error) {
      console.error('Export error:', error);
      alert('❌ Export error: ' + error.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className={styles.clipsPage}>
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
          <a href="/clips" className={`${styles.navItem} ${styles.active}`}>
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

      {/* Main Content */}
      <div className={styles.mainArea}>
        {/* Top Bar */}
        <header className={styles.topBar}>
          <div className={styles.topBarLeft}>
            <div className={styles.dateDisplay}>{currentDate}</div>
            <div className={styles.tagline}>All Your Clips</div>
          </div>

          <div className={styles.topBarRight}>
            <div className={styles.searchCard}>
              <Search size={18} />
              <input type="text" placeholder="Search clips..." />
            </div>
            <button className={styles.notifBtn}>
              <Bell size={20} />
              <span className={styles.badge}>3</span>
            </button>
            <div className={styles.userNav}>
              <div className={styles.avatarBg}>{getInitials(streamerName)}</div>
              <div className={styles.userInfo}>
                <div>{streamerName}</div>
              </div>
            </div>
          </div>
        </header>

        {/* Filters */}
        <div className={styles.filterSection}>
          {selectedClips.size > 0 && (
            <div className={styles.batchActionBar}>
              <span>{selectedClips.size} clip(s) selected</span>
              <button
                className={styles.batchExportBtn}
                onClick={handleBatchExport}
                disabled={batchExporting}
              >
                {batchExporting ? 'Exporting...' : 'Batch Export to All Platforms'}
              </button>
              <button
                className={styles.clearSelectionBtn}
                onClick={() => setSelectedClips(new Set())}
              >
                Clear
              </button>
            </div>
          )}
          <div className={styles.filterTabs}>
            <button
              className={`${styles.filterBtn} ${filter === 'all' ? styles.active : ''}`}
              onClick={() => setFilter('all')}
            >
              All Clips ({clips.length})
            </button>
            <button
              className={`${styles.filterBtn} ${filter === 'published' ? styles.active : ''}`}
              onClick={() => setFilter('published')}
            >
              Published ({clips.filter(c => c.status === 'published').length})
            </button>
            <button
              className={`${styles.filterBtn} ${filter === 'processing' ? styles.active : ''}`}
              onClick={() => setFilter('processing')}
            >
              Processing ({clips.filter(c => c.status === 'processing').length})
            </button>
          </div>
        </div>

        {/* Clips Grid */}
        {loading ? (
          <div className={styles.loadingState}>
            <Loader size={32} className={styles.spinner} />
            <p>Loading clips...</p>
          </div>
        ) : filteredClips.length === 0 ? (
          <div className={styles.emptyState}>
            <Video size={48} />
            <p>No clips yet</p>
            <span>Clips will appear here as moments are detected</span>
          </div>
        ) : (
          <div className={styles.clipsGrid}>
            {filteredClips.map((clip) => (
              <div key={clip.id} className={`${styles.clipCard} ${selectedClips.has(clip.id) ? styles.selected : ''}`}>
                <input
                  type="checkbox"
                  className={styles.clipCheckbox}
                  checked={selectedClips.has(clip.id)}
                  onChange={() => toggleClipSelection(clip.id)}
                />
                <div className={styles.clipThumbnail}>
                  {clip.urls?.thumbnail ? (
                    <img src={clip.urls.thumbnail} alt={clip.title} className={styles.thumbnailImage} />
                  ) : (
                    <div className={styles.placeholder}>
                      <Video size={32} />
                    </div>
                  )}
                  {clip.duration_seconds && (
                    <div className={styles.duration}>
                      {formatDuration(clip.duration_seconds)}
                    </div>
                  )}
                  {clip.status === 'published' && (
                    <div className={styles.publishedOverlay}>
                      <CheckCircle size={24} />
                      Published
                    </div>
                  )}
                  {clip.status === 'processing' && (
                    <div className={styles.processingOverlay}>
                      <Clock size={24} />
                      Processing
                    </div>
                  )}
                  {/* Play button overlay */}
                  <button
                    className={styles.playButton}
                    onClick={() => handlePlayClip(clip)}
                    title="Play video"
                    aria-label="Play video"
                  >
                    <Play size={32} fill="currentColor" />
                  </button>
                </div>

                <div className={styles.clipContent}>
                  <h3>{clip.title}</h3>
                  <p>{clip.description}</p>

                  <div className={styles.clipStats}>
                    {clip.quality_score && clip.quality_score > 0 && (
                      <span className={styles.stat}>
                        Quality: {(clip.quality_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>

                  <div className={styles.timestamp}>
                    {formatRelativeTime(clip.created_at)}
                  </div>
                </div>

                <div className={styles.clipActions}>
                  {clip.status === 'pending' && (
                    <>
                      <button
                        className={styles.actionBtn}
                        title="Approve clip"
                        onClick={() => handleApprove(clip)}
                        style={{ color: '#10b981' }}
                      >
                        <ThumbsUp size={18} />
                      </button>
                      <button
                        className={styles.actionBtn}
                        title="Reject clip"
                        onClick={() => handleReject(clip)}
                        style={{ color: '#ef4444' }}
                      >
                        <ThumbsDown size={18} />
                      </button>
                    </>
                  )}
                  <button
                    className={styles.actionBtn}
                    title="Preview vertical (9:16)"
                    onClick={() => {
                      setPreviewClip(clip);
                      setShowVerticalPreview(true);
                    }}
                  >
                    <Smartphone size={18} />
                  </button>
                  <button
                    className={`${styles.actionBtn} ${copiedId === clip.id ? styles.copied : ''}`}
                    title="Copy share link"
                    onClick={() => handleShare(clip)}
                  >
                    {copiedId === clip.id ? <Check size={18} /> : <Copy size={18} />}
                  </button>
                  <button
                    className={styles.actionBtn}
                    title="Download clip"
                    onClick={() => handleDownload(clip)}
                  >
                    <Download size={18} />
                  </button>
                  <button
                    className={styles.actionBtn}
                    title="Export to platforms (TikTok, Shorts, Reels)"
                    onClick={() => {
                      setSelectedClip(clip);
                      setShowExportModal(true);
                    }}
                  >
                    <Share2 size={18} />
                  </button>
                  <button
                    className={styles.actionBtn}
                    title="Delete clip"
                    onClick={() => handleDelete(clip)}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Vertical Preview Modal */}
      <VerticalPreviewModal
        clip={previewClip}
        isOpen={showVerticalPreview}
        onClose={() => setShowVerticalPreview(false)}
      />

      {/* Video Player Modal */}
      <VideoPlayerModal
        clip={playingClip}
        isOpen={showVideoPlayer}
        onClose={() => setShowVideoPlayer(false)}
      />

      {/* Export Modal */}
      {showExportModal && selectedClip && (
        <div className={styles.modalOverlay} onClick={() => setShowExportModal(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Export Clip</h2>
              <button className={styles.closeBtn} onClick={() => setShowExportModal(false)}>✕</button>
            </div>

            <div className={styles.modalContent}>
              <h3>{selectedClip.title}</h3>

              <div className={styles.formGroup}>
                <label>Export to Platform</label>
                <div className={styles.platformOptions}>
                  {[
                    { id: 'tiktok', name: 'TikTok', emoji: '🎵' },
                    { id: 'shorts', name: 'YouTube Shorts', emoji: '▶️' },
                    { id: 'reels', name: 'Instagram Reels', emoji: '📸' }
                  ].map(platform => (
                    <button
                      key={platform.id}
                      className={`${styles.platformOption} ${exportSettings.preset === platform.id ? styles.selected : ''}`}
                      onClick={() => setExportSettings({ ...exportSettings, preset: platform.id })}
                    >
                      {platform.emoji} {platform.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.formGroup}>
                <label>
                  <input
                    type="checkbox"
                    checked={exportSettings.watermark}
                    onChange={(e) => setExportSettings({ ...exportSettings, watermark: e.target.checked })}
                  />
                  Add Watermark
                </label>
                {exportSettings.watermark && (
                  <input
                    type="text"
                    className={styles.input}
                    placeholder="Watermark text"
                    value={exportSettings.watermarkText}
                    onChange={(e) => setExportSettings({ ...exportSettings, watermarkText: e.target.value })}
                  />
                )}
              </div>

              <div className={styles.modalFooter}>
                <button
                  className={styles.cancelBtn}
                  onClick={() => setShowExportModal(false)}
                  disabled={exporting}
                >
                  Cancel
                </button>
                <button
                  className={styles.exportBtn}
                  onClick={handleExport}
                  disabled={exporting}
                >
                  {exporting ? 'Exporting...' : `📤 Export to ${exportSettings.preset.toUpperCase()}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

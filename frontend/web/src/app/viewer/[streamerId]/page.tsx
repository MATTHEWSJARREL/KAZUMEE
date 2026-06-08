import { useEffect, useState } from 'react';
import { useParams } from 'react-router';
// @ts-ignore
import CatchUpNudge from '@/components/CatchUpNudge';
// @ts-ignore
import ClipCard from '@/components/ClipCard';
// @ts-ignore
import ViewerTopBar from '@/components/ViewerTopBar';
// @ts-ignore
import VibeBar from '@/components/VibeBar';
// @ts-ignore
import styles from './viewer.module.css';

/**
 * Viewer Page Component
 * 
 * Shows streamer's recent clips and activity.
 * Displays simplified top bar with streamer info.
 * Includes clip grid, share functionality, and vibe indicator.
 */
interface Clip {
  id: string;
  [key: string]: any;
}

interface Streamer {
  id: string;
  name: string;
  avatar_url?: string;
  bio?: string;
  is_streaming?: boolean;
  [key: string]: any;
}

export default function ViewerPage() {
  const { streamerId } = useParams<{ streamerId: string }>();
  const [clips, setClips] = useState<Clip[]>([]);
  const [streamer, setStreamer] = useState<Streamer | null>(null);
  const [loading, setLoading] = useState(true);
  const [vibeScore, setVibeScore] = useState(50);

  useEffect(() => {
    // Fetch streamer info
    const fetchStreamer = async () => {
      try {
        const response = await fetch(`/api/streamer/${streamerId}`, {
          credentials: "include",
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        setStreamer(data);
      } catch (error) {
        console.error('Failed to fetch streamer:', error);
      }
    };

    // Fetch recent clips
    const fetchClips = async () => {
      try {
        const response = await fetch(`/api/clips?streamer_id=${streamerId}&limit=20`, {
          credentials: "include",
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        setClips(data.clips || []);
      } catch (error) {
        console.error('Failed to fetch clips:', error);
      } finally {
        setLoading(false);
      }
    };

    // Fetch vibe score
    const fetchVibeScore = async () => {
      try {
        const response = await fetch(`/api/streamer/${streamerId}/vibe`, {
          credentials: "include",
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        setVibeScore(data.score || 50);
      } catch (error) {
        console.error('Failed to fetch vibe score:', error);
      }
    };

    if (streamerId) {
      fetchStreamer();
      fetchClips();
      fetchVibeScore();
    }
  }, [streamerId]);

  const handleCatchUp = () => {
    // Scroll to clips section
    const clipsSection = document.getElementById('clips-grid');
    clipsSection?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleShare = async (clipId: string) => {
    try {
      const clipUrl = `${window.location.origin}/viewer/${streamerId}?clip=${clipId}`;
      
      if (navigator.share) {
        // Use native share if available
        await navigator.share({
          title: `Check out this clip!`,
          url: clipUrl,
        });
      } else {
        // Fallback: copy to clipboard
        await navigator.clipboard.writeText(clipUrl);
        alert('Clip link copied to clipboard!');
      }
    } catch (error) {
      console.error('Share failed:', error);
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingState}>
          <p>Loading streamer content...</p>
        </div>
      </div>
    );
  }

  if (!streamer) {
    return (
      <div className={styles.page}>
        <div className={styles.errorState}>
          <p>Streamer not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* Top bar with streamer info */}
      <ViewerTopBar streamer={streamer} />

      {/* Vibe indicator */}
      <div className={styles.vibeSection}>
        <p className={styles.vibeLabel}>Vibe</p>
        <VibeBar score={vibeScore} />
      </div>

      {/* Clips grid */}
      <section id="clips-grid" className={styles.clipsSection}>
        <h2 className={styles.clipsTitle}>Recent Clips</h2>
        
        {clips.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No clips yet. Check back soon!</p>
          </div>
        ) : (
          <div className={styles.clipsGrid}>
            {clips.map((clip) => (
              <ClipCard
                key={clip.id}
                clip={clip}
                onShare={() => handleShare(clip.id)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Catch-up nudge */}
      <CatchUpNudge onCatchUp={handleCatchUp} />
    </div>
  );
}

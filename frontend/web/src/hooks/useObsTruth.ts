import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/apiClient';

export type ObsState = {
  connected: boolean;
  recording: boolean;
  streaming: boolean;
  scene: string;
  loading: boolean; // Added for UI feedback
};

export function useObsTruth(enabled: boolean = true) {
  // Initialize with a default object instead of null to prevent "Checking..." hangs
  const [state, setState] = useState<ObsState>({
    connected: false,
    recording: false,
    streaming: false,
    scene: 'unknown',
    loading: true, 
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      setState((prev) => ({ ...prev, loading: false }));
      setError(null);
      return;
    }

    let alive = true;

    const fetchState = async () => {
      try {
        // Use API-relative path for proxy compatibility
        const res = await apiFetch('/obs/status');
        
        if (!res.ok) throw new Error('OBS state fetch failed');
        const data = await res.json();
        
        if (alive) {
          setState({
            ...data,
            loading: false // Data arrived!
          });
          setError(null);
        }
      } catch (err) {
        if (alive) {
          setError('OBS unavailable');
          setState(prev => ({ ...prev, loading: false })); // Stop loading even on error
        }
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 2000); // 2s is safer than 1s for polling

    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [enabled]);

  return { state, error };
}

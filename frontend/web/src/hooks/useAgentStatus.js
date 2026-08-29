import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/apiClient';

/**
 * Shared hook to check agent connection status
 * Reads streamer_id from localStorage and checks /api/agent/registry-status
 * Updates every 3 seconds
 *
 * Returns: { agentStatus: 'online' | 'offline' | null }
 */
export function useAgentStatus() {
  const [agentStatus, setAgentStatus] = useState(null);

  const checkAgentRegistry = useCallback(async () => {
    try {
      const res = await apiFetch('/api/agent/registry-status');
      if (res.ok) {
        const data = await res.json();
        const streamerIdStr = localStorage.getItem('streamerId');
        const streamerIdNum = streamerIdStr ? parseInt(streamerIdStr, 10) : null;

        if (streamerIdNum === null) {
          console.warn('[AGENT] No streamer ID in localStorage. Login may not have stored it.');
          setAgentStatus('offline');
          return;
        }

        const connectedIds = data.connected_streamer_ids || [];
        const isConnected = connectedIds.includes(streamerIdNum);

        setAgentStatus(isConnected ? 'online' : 'offline');
        console.log('[AGENT] Registry check:', {
          streamerIdFromStorage: streamerIdStr,
          streamerIdParsed: streamerIdNum,
          connectedIds: connectedIds,
          isConnected: isConnected,
          status: isConnected ? 'ONLINE' : 'OFFLINE'
        });
      } else {
        console.warn('[AGENT] Registry check returned non-ok status:', res.status);
        setAgentStatus('offline');
      }
    } catch (err) {
      console.error('[AGENT] Registry check failed:', err);
      setAgentStatus('offline');
    }
  }, []);

  useEffect(() => {
    // Check immediately on mount
    checkAgentRegistry();

    // Poll every 3 seconds
    const interval = setInterval(checkAgentRegistry, 3000);

    return () => clearInterval(interval);
  }, [checkAgentRegistry]);

  return { agentStatus };
}

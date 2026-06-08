import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiFetch } from '@/lib/apiClient';

const ClipSearchContext = createContext({ results: [], setResults: () => {} });

export function ClipSearchProvider({ children }) {
  const [results, setResults] = useState([]);

  useEffect(() => {
    const handler = (ev) => {
      try {
        const data = ev?.data;
        if (!data) return;
        if (data.type === 'search_results') {
          const r = data.data?.results || [];
          setResults(r);
          console.log('Search results received (window):', r);
        }
      } catch (err) {
        // swallow
      }
    };

    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  useEffect(() => {
    // connect to backend websocket for real-time events
    let ws;
    let cancelled = false;

    const connect = async () => {
      try {
        const streamTokenRes = await apiFetch('/auth/stream-token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        if (!streamTokenRes.ok) return;
        const tokenData = await streamTokenRes.json();
        const streamToken = tokenData?.token;
        if (!streamToken || cancelled) return;

        const url = `ws://${window.location.hostname || '127.0.0.1'}:8000/ws/events?token=${encodeURIComponent(streamToken)}`;
        ws = new WebSocket(url);
        ws.onopen = () => console.log('ClipSearch WS connected', url);
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            if (msg?.type === 'search_results') {
              const r = msg.data?.results || [];
              setResults(r);
              console.log('Search results received (ws):', r);
            }
          } catch (e) {
            // ignore
          }
        };
        ws.onclose = () => console.log('ClipSearch WS closed');
        ws.onerror = (err) => console.warn('ClipSearch WS error', err);
      } catch (e) {
        console.warn('Failed to connect ClipSearch WS', e);
      }
    };

    void connect();

    return () => {
      cancelled = true;
      try {
        if (ws && ws.readyState === WebSocket.OPEN) ws.close();
      } catch (e) {
        /* noop */
      }
    };
  }, []);

  return (
    <ClipSearchContext.Provider value={{ results, setResults }}>{children}</ClipSearchContext.Provider>
  );
}

export function useClipSearch() {
  return useContext(ClipSearchContext);
}

export default ClipSearchContext;

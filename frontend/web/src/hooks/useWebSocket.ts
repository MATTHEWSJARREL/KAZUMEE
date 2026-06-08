import { useEffect, useRef, useState } from 'react';
import { apiFetch, getActiveStreamerId, getAuthToken, isAuthBypassEnabled, wsBase } from '@/lib/apiClient';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export function useWebSocket(url = `${wsBase}/ws`) {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [readyState, setReadyState] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof WebSocket === 'undefined') {
      return;
    }
    const token = getAuthToken();
    const bypass = isAuthBypassEnabled();
    if (!token && !bypass) {
      setReadyState(WebSocket.CLOSED);
      return;
    }
    let ws: WebSocket | null = null;
    let cancelled = false;

    const connect = async () => {
      let wsToken = token;
      if (token) {
        try {
          const streamerId = getActiveStreamerId();
          const res = await apiFetch('/auth/stream-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(streamerId ? { streamer_id: streamerId } : {}),
          });
          if (res.ok) {
            const data = await res.json();
            if (data?.token) wsToken = data.token;
          }
        } catch {
          // Fallback to existing token if short-lived token endpoint is unavailable.
        }
      }
      if (cancelled) return;

      let finalUrl = url;
      try {
        const parsed = new URL(url);
        if (wsToken) parsed.searchParams.set('token', wsToken);
        finalUrl = parsed.toString();
      } catch {
        // Keep provided URL if parsing fails.
        finalUrl = url;
      }

      ws = new WebSocket(finalUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setReadyState(WebSocket.OPEN);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        setReadyState(WebSocket.CLOSED);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setReadyState(WebSocket.CLOSED);
      };
    };

    void connect();

    return () => {
      cancelled = true;
      if (ws) ws.close();
    };
  }, [url]);

  const sendMessage = (message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not open. Cannot send message.');
    }
  };

  return { lastMessage, readyState, sendMessage };
}

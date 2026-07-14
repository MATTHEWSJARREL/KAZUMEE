"use client";

import { useCallback, useEffect, useState } from "react";
import { createOrGetRealtimeClient } from "./RealtimeClient";
import { apiFetch, getActiveStreamerId, getAuthToken, isAuthBypassEnabled, wsBase } from "../apiClient";

type RealtimeMessage = { type: string; [key: string]: any };

export function useRealtime() {
  const [readyState, setReadyState] = useState<number>(0);
  const [lastMessage, setLastMessage] = useState<RealtimeMessage | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || typeof WebSocket === "undefined") {
      setReadyState(WebSocket.CLOSED);
      return;
    }

    const token = getAuthToken();
    const bypass = isAuthBypassEnabled();
    if (!token && !bypass) {
      setReadyState(WebSocket.CLOSED);
      return;
    }

    let cancelled = false;

    const streamToken = async () => {
      let wsToken = token;
      if (token) {
        try {
          const streamerId = getActiveStreamerId();
          const res = await apiFetch("/auth/stream-token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(streamerId ? { streamer_id: streamerId } : {}),
          });
          if (res.ok) {
            const data = await res.json();
            if (data?.token) wsToken = data.token;
          }
        } catch {
          // Fallback to existing token.
        }
      }
      return wsToken;
    };

    const buildFinalUrl = (url: string, token2: string | null) => {
      let finalUrl = url;
      try {
        const parsed = new URL(url);
        if (token2) parsed.searchParams.set("token", token2);
        finalUrl = parsed.toString();
      } catch {
        finalUrl = url;
      }
      return finalUrl;
    };

    const shouldConnect = () => Boolean(getAuthToken() || isAuthBypassEnabled());

    const client = createOrGetRealtimeClient({
      url: `${wsBase}/ws`,
      connectToken: streamToken,
      shouldConnect,
      buildFinalUrl,
    });

    const unsubAll = client.subscribe((message: RealtimeMessage) => {
      if (!cancelled) setLastMessage(message);
    });

    const connect = async () => {
      await client.ensureConnected();
      if (!cancelled) setReadyState(client.getReadyState());
    };

    void connect();

    const interval = window.setInterval(() => {
      if (!cancelled) setReadyState(client.getReadyState());
    }, 250);

    return () => {
      cancelled = true;
      unsubAll();
      window.clearInterval(interval);
    };
  }, []);

  const subscribe = useCallback((handler: (message: RealtimeMessage) => void) => {
    const client = createOrGetRealtimeClient({
      url: `${wsBase}/ws`,
      connectToken: async () => getAuthToken(),
      shouldConnect: () => Boolean(getAuthToken() || isAuthBypassEnabled()),
      buildFinalUrl: (url, token) => url,
    });
    return client.subscribe(handler);
  }, []);

  const subscribeToType = useCallback((type: string, handler: (message: RealtimeMessage) => void) => {
    const client = createOrGetRealtimeClient({
      url: `${wsBase}/ws`,
      connectToken: async () => getAuthToken(),
      shouldConnect: () => Boolean(getAuthToken() || isAuthBypassEnabled()),
      buildFinalUrl: (url, token) => url,
    });
    return client.subscribeToType(type, handler);
  }, []);

  const sendMessage = useCallback((payload: any) => {
    const client = createOrGetRealtimeClient({
      url: `${wsBase}/ws`,
      connectToken: async () => getAuthToken(),
      shouldConnect: () => Boolean(getAuthToken() || isAuthBypassEnabled()),
      buildFinalUrl: (url, token) => url,
    });
    client.sendMessage(payload);
  }, []);

  return { readyState, lastMessage, subscribe, subscribeToType, sendMessage };
}


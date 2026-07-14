"use client";

import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "@/lib/apiClient";

const STORAGE_KEY = "kazumi_settings";

export const DEFAULT_SETTINGS = {
  profile: { displayName: "Kazumi Streamer", platforms: ["Twitch"] },
  voice: { model: "natural", responseSpeed: 75, enabled: true, triggerWord: "Kazumi" },
  ai: {
    personality: "helpful",
    creativeRange: 0.7,
    groqModel: "llama3-8b-8192",
    useGroq: true,
    assistantPrompt: "",
  },
  integrations: { obs: true, twitch: true, groq: true },
  moderation: { strictness: "medium", autoModerate: true, contextAware: true },
  automation: { autoClipping: true, autoHighlights: true, sceneControl: false },
  streamerAiSuite: {
    dynamicPrompter: { enabled: true, silenceSeconds: 10, cooldownSeconds: 90 },
    crossPlatformViralEngine: { enabled: true, autoPost: false, cooldownSeconds: 180, minHypeScore: 75 },
    sentimentShield: { enabled: true, nuanceDetection: true, antiHateRaid: { enabled: true, windowSeconds: 2, joinThreshold: 25 } },
    contentFarm: { enabled: true, autoCaptionStyle: "hormozi", verticalCropTarget: "face_plus_gameplay" },
    streamDoctor: { enabled: true, droppedFramesWarn: 120, highBitrateKbps: 6000, micSourceName: "Mic/Aux" },
    spoilerFilter: { enabled: true, action: "blur_for_streamer", keywords: ["ending", "final boss", "phase 2", "secret ending", "twist", "spoiler", "solution", "puzzle answer"] },
    empathyGuard: { enabled: true, autoWhisperResources: true },
    audioSafeMode: { enabled: true, desktopAudioSource: "Desktop Audio", copyrightThreshold: 0.8 },
  },
  superChatSorter: {
    enabled: true,
    extractQuestions: true,
    blockedQuestionKeywords: [],
    questionSourceMode: "all",
    muteQuestionsUntil: null,
  },
  appearance: { darkMode: false },
};

const SettingsContext = createContext({
  settings: DEFAULT_SETTINGS,
  loading: true,
  updateSetting: (category: string, key: string, value: any) => {},
  setSettings: (next: any) => {},
  saveSettings: async () => {},
  refreshSettings: async () => {},
});

const mergeSettings = (base: any, override: any) => {
  const merged = { ...base };
  Object.keys(override || {}).forEach((key) => {
    if (typeof override[key] === "object" && !Array.isArray(override[key]) && typeof merged[key] === "object") {
      merged[key] = mergeSettings(merged[key], override[key]);
    } else {
      merged[key] = override[key];
    }
  });
  return merged;
};

const applyTheme = (darkMode: boolean) => {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (darkMode) root.classList.add("kazumi-dark");
  else root.classList.remove("kazumi-dark");
};

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const autosaveTimer = useRef<any>(null);
  const prevSettings = useRef<any>(DEFAULT_SETTINGS);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        setSettings(mergeSettings(DEFAULT_SETTINGS, parsed));
      } catch {
        // ignore parse errors
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = () => {
      refreshSettings();
    };
    window.addEventListener("kazumi:auth", handler);
    return () => window.removeEventListener("kazumi:auth", handler);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    applyTheme(Boolean(settings?.appearance?.darkMode));
    window.dispatchEvent(new CustomEvent("kazumi:settings", { detail: settings }));
  }, [settings]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const prev = prevSettings.current;
    const next = settings;
    const togglesChanged =
      prev?.appearance?.darkMode !== next?.appearance?.darkMode ||
      prev?.ai?.useGroq !== next?.ai?.useGroq ||
      prev?.automation?.autoClipping !== next?.automation?.autoClipping ||
      prev?.automation?.autoHighlights !== next?.automation?.autoHighlights ||
      prev?.automation?.sceneControl !== next?.automation?.sceneControl;

    prevSettings.current = next;

    if (!togglesChanged) return;
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = setTimeout(() => {
      saveSettings().catch(() => {
        // silent fail, local cache already updated
      });
    }, 500);
  }, [settings]);

  const refreshSettings = async () => {
    // Skip for unauthenticated users or on auth pages
    if (typeof window !== "undefined") {
      const isAuthPage = window.location.pathname.startsWith("/auth");
      const isOnboarding = window.location.pathname.startsWith("/onboarding");
      const isLanding = window.location.pathname === "/";

      // Don't fetch settings on auth, onboarding, or landing pages
      if (isAuthPage || isOnboarding || isLanding) {
        return;
      }
    }

    try {
      const res = await apiFetch("/api/settings");
      if (!res.ok) return;
      const data = await res.json();
      setSettings(mergeSettings(DEFAULT_SETTINGS, data));
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    // Skip for unauthenticated users or on auth pages
    if (typeof window !== "undefined") {
      const isAuthPage = window.location.pathname.startsWith("/auth");
      const isOnboarding = window.location.pathname.startsWith("/onboarding");
      const isLanding = window.location.pathname === "/";

      // Don't fetch settings on auth, onboarding, or landing pages
      if (isAuthPage || isOnboarding || isLanding) {
        return;
      }
    }
    refreshSettings();
  }, []);

  const saveSettings = async () => {
    const res = await apiFetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    if (!res.ok) {
      throw new Error("Failed to save settings");
    }
    const data = await res.json();
    if (data?.settings) {
      setSettings(mergeSettings(DEFAULT_SETTINGS, data.settings));
    }
  };

  const updateSetting = (category: string, key: string, value: any) => {
    setSettings((prev: any) => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value,
      },
    }));
  };

  const value = useMemo(
    () => ({ settings, loading, updateSetting, setSettings, saveSettings, refreshSettings }),
    [settings, loading]
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  return useContext(SettingsContext);
}

export default SettingsContext;

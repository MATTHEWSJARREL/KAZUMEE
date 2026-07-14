"use client";

import { useState, useEffect, useMemo } from "react";
import { apiFetch, clearActiveStreamerId, clearAuthBypass, clearAuthToken, isAuthBypassEnabled, setAuthBypassEnabled } from "@/lib/apiClient";
import { useSettings } from "@/lib/SettingsContext";
import {
  Settings as SettingsIcon,
  User,
  Mic,
  Shield,
  Zap,
  Bell,
  Palette,
  Save,
  RefreshCw,
  Brain,
  Link,
  Moon,
  Sun,
  Server,
  CheckCircle,
  AlertTriangle
} from "lucide-react";

export default function SettingsPage() {
  const { settings, loading, updateSetting, saveSettings, refreshSettings, setSettings } = useSettings();
  const [saving, setSaving] = useState(false);
  const isDarkMode = Boolean(settings?.appearance?.darkMode);
  const [backendStatus, setBackendStatus] = useState("checking");
  const [connections, setConnections] = useState([]);
  const [oauthNotice, setOauthNotice] = useState("");
  const [twitchBroadcasterId, setTwitchBroadcasterId] = useState("");
  const [twitchModeratorId, setTwitchModeratorId] = useState("");
  const [twitchWebhookUrl, setTwitchWebhookUrl] = useState("");
  const [twitchAutoSubscribe, setTwitchAutoSubscribe] = useState(false);
  const [youtubeLiveChatId, setYoutubeLiveChatId] = useState("");
  const [youtubeAutoPoll, setYoutubeAutoPoll] = useState(false);
  const [presetOptions, setPresetOptions] = useState([]);
  const [presetValue, setPresetValue] = useState("balanced");
  const [presetSaving, setPresetSaving] = useState(false);
  const [profileUser, setProfileUser] = useState(null);
  const [streamerList, setStreamerList] = useState([]);
  const [platformInput, setPlatformInput] = useState("");
  const [activeStreamerId, setActiveStreamerId] = useState(null);
  const [roleSaving, setRoleSaving] = useState(false);
  const [activeStreamerSaving, setActiveStreamerSaving] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [diagnostics, setDiagnostics] = useState(null);
  const [diagLoading, setDiagLoading] = useState(false);
  const [twitchSubscribeLoading, setTwitchSubscribeLoading] = useState(false);
  const [youtubePollLoading, setYoutubePollLoading] = useState(false);
  const [streamerAiStatus, setStreamerAiStatus] = useState(null);
  const [streamerAiLoading, setStreamerAiLoading] = useState(false);
  const defaultPolicy = {
    chat: "allow",
    ask_lore: "allow",
    request_clip: "allow",
    vote_scene: "allow",
    suggestion: "allow",
    switch_scene: "approve",
    mute_mic: "approve",
    unmute_mic: "approve",
    start_recording: "approve",
    stop_recording: "approve",
    start_streaming: "deny",
    stop_streaming: "deny",
    panic_mode: "deny",
    restart_engine: "deny",
  };
  const [actionPolicy, setActionPolicy] = useState(defaultPolicy);
  const [policySaving, setPolicySaving] = useState(false);
  const [devBypass, setDevBypass] = useState(false);

  useEffect(() => {
    refreshSettings();
    checkBackend();
    fetchConnections();
    fetchIntegrationMeta("twitch");
    fetchIntegrationMeta("youtube");
    fetchPolicy();
    fetchPresetOptions();
    fetchPreferences();
    fetchProfile();
    fetchDiagnostics();
    setDevBypass(isAuthBypassEnabled());
    const params = new URLSearchParams(window.location.search);
    const status = params.get("oauth");
    const platform = params.get("platform");
    if (status === "success" && platform) {
      setOauthNotice(`${platform} connected successfully`);
    }
  }, []);

  useEffect(() => {
    const next = (settings?.profile?.platforms || []).join(", ");
    setPlatformInput(next);
  }, [settings?.profile?.platforms]);

  useEffect(() => {
    if (profileUser?.role === "streamer") {
      fetchStreamerAiStatus();
    }
  }, [profileUser?.role]);

  const checkBackend = async () => {
    try {
      const res = await apiFetch("/api/health");
      if (res.ok) setBackendStatus("online");
      else setBackendStatus("error");
    } catch {
      setBackendStatus("offline");
    }
  };

  const fetchProfile = async () => {
    try {
      const res = await apiFetch("/auth/me");
      const data = await res.json();
      setProfileUser(data?.user || null);
      if (data?.streamer_id) setActiveStreamerId(data.streamer_id);
      if (data?.user?.role === "viewer") {
        const listRes = await apiFetch("/auth/streamers");
        const listData = await listRes.json();
        setStreamerList(listData.streamers || []);
      }
    } catch (error) {
      console.error("Error fetching profile:", error);
    }
  };

  const fetchConnections = async () => {
    try {
      const res = await apiFetch("/integrations/status");
      const data = await res.json();
      setConnections(data.connections || []);
    } catch {
      setConnections([]);
    }
  };

  const fetchIntegrationMeta = async (platform) => {
    try {
      const res = await apiFetch(`/integrations/metadata?platform=${platform}`);
      const data = await res.json();
      const item = (data.connections || []).find((c) => c.platform === platform);
      const meta = item?.meta || {};
      if (platform === "twitch") {
        if (meta.broadcaster_id) setTwitchBroadcasterId(meta.broadcaster_id);
        if (meta.moderator_id) setTwitchModeratorId(meta.moderator_id);
        if (meta.webhook_url) setTwitchWebhookUrl(meta.webhook_url);
        if (typeof meta.auto_subscribe === "boolean") setTwitchAutoSubscribe(meta.auto_subscribe);
      }
      if (platform === "youtube") {
        if (meta.live_chat_id) setYoutubeLiveChatId(meta.live_chat_id);
        if (typeof meta.auto_poll === "boolean") setYoutubeAutoPoll(meta.auto_poll);
      }
    } catch (error) {
      console.error("Error fetching integration metadata:", error);
    }
  };

  const fetchDiagnostics = async () => {
    setDiagLoading(true);
    try {
      const res = await apiFetch("/integrations/diagnostics");
      if (!res.ok) return;
      const data = await res.json();
      setDiagnostics(data.diagnostics || null);
    } catch (error) {
      console.error("Error fetching diagnostics:", error);
    } finally {
      setDiagLoading(false);
    }
  };

  const fetchStreamerAiStatus = async () => {
    if (profileUser?.role !== "streamer") return;
    setStreamerAiLoading(true);
    try {
      const res = await apiFetch("/api/streamer/ai/status");
      if (!res.ok) return;
      const data = await res.json();
      setStreamerAiStatus(data || null);
    } catch (error) {
      console.error("Error fetching streamer AI status:", error);
    } finally {
      setStreamerAiLoading(false);
    }
  };

  const serviceStatusMap = useMemo(() => {
    const twitchConnected =
      Boolean(diagnostics?.twitch?.connected) && Boolean(diagnostics?.twitch?.token_valid);
    const youtubeConnected =
      Boolean(diagnostics?.youtube?.connected) && Boolean(diagnostics?.youtube?.token_valid);
    const obsConnected = Boolean(diagnostics?.obs?.connected);
    const groqConnected = Boolean(diagnostics?.groq?.reachable);

    return {
      twitch: {
        connected: twitchConnected,
        detail: diagnostics?.twitch?.token_valid ? "Token valid" : diagnostics?.twitch?.connected ? "Token invalid/expired" : "Not connected",
      },
      youtube: {
        connected: youtubeConnected,
        detail: diagnostics?.youtube?.token_valid ? "Token valid" : diagnostics?.youtube?.connected ? "Token invalid/expired" : "Not connected",
      },
      obs: {
        connected: obsConnected,
        detail: obsConnected
          ? `${diagnostics?.obs?.streaming ? "Streaming" : "Idle"}${diagnostics?.obs?.recording ? " • Recording" : ""}`
          : "OBS unreachable",
      },
      groq: {
        connected: groqConnected,
        detail: groqConnected ? `Reachable (${diagnostics?.groq?.model_count ?? 0} models)` : "API unreachable",
      },
    };
  }, [diagnostics]);

  const isConnected = (platform) => {
    if (serviceStatusMap[platform]) return Boolean(serviceStatusMap[platform].connected);
    return connections.some((c) => c.platform === platform && c.connected);
  };

  const connectPlatform = async (platform) => {
    try {
      const res = await apiFetch("/integrations/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data?.status === "error") {
        setOauthNotice(data?.message || `Failed to start ${platform} OAuth flow.`);
        return;
      }
      if (data?.auth_url) {
        window.location.href = data.auth_url;
      } else {
        setOauthNotice(`No OAuth URL returned for ${platform}.`);
      }
    } catch (error) {
      console.error(error);
      setOauthNotice(`Failed to connect ${platform}.`);
    }
  };

  const saveIntegrationMeta = async (platform, meta) => {
    try {
      const res = await apiFetch("/integrations/metadata", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform, meta }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data?.status === "error") {
        setOauthNotice(data?.message || "Failed to save integration metadata.");
        return false;
      }
      setOauthNotice("Integration metadata saved.");
      return true;
    } catch (error) {
      console.error(error);
      setOauthNotice("Failed to save integration metadata.");
      return false;
    }
  };

  const handleTwitchSubscribe = async () => {
    setTwitchSubscribeLoading(true);
    try {
      const res = await apiFetch("/integrations/twitch/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          broadcaster_id: twitchBroadcasterId,
          webhook_url: twitchWebhookUrl,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data?.status === "error") {
        const detail = data?.message || data?.detail || "Twitch subscribe failed.";
        setOauthNotice(`Twitch subscribe failed: ${detail}`);
        return;
      }
      setOauthNotice("Twitch EventSub subscription created successfully.");
      fetchDiagnostics();
    } catch (error) {
      console.error("Twitch subscribe failed:", error);
      setOauthNotice("Twitch subscribe failed due to network error.");
    } finally {
      setTwitchSubscribeLoading(false);
    }
  };

  const handleYoutubePoll = async () => {
    setYoutubePollLoading(true);
    try {
      const res = await apiFetch("/integrations/youtube/livechat/poll", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ live_chat_id: youtubeLiveChatId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data?.status === "error") {
        const detail = data?.message || data?.detail || "YouTube poll failed.";
        setOauthNotice(`YouTube poll failed: ${detail}`);
        return;
      }
      const pulled = Array.isArray(data?.data?.items) ? data.data.items.length : 0;
      setOauthNotice(`YouTube poll succeeded. Pulled ${pulled} chat message${pulled === 1 ? "" : "s"}.`);
      fetchDiagnostics();
    } catch (error) {
      console.error("YouTube poll failed:", error);
      setOauthNotice("YouTube poll failed due to network error.");
    } finally {
      setYoutubePollLoading(false);
    }
  };

  const fetchPolicy = async () => {
    try {
      const res = await apiFetch("/policy");
      if (!res.ok) return;
      const data = await res.json();
      if (data?.policy) setActionPolicy({ ...defaultPolicy, ...data.policy });
    } catch (error) {
      console.error("Error fetching policy:", error);
    }
  };

  const fetchPresetOptions = async () => {
    try {
      const res = await apiFetch("/api/preferences/presets");
      const data = await res.json();
      setPresetOptions(data.presets || []);
    } catch (error) {
      console.error("Error fetching presets:", error);
    }
  };

  const fetchPreferences = async () => {
    try {
      const res = await apiFetch("/api/preferences");
      if (!res.ok) return;
      const data = await res.json();
      setPresetValue(data?.preferences?.preset || "balanced");
    } catch (error) {
      console.error("Error fetching preferences:", error);
    }
  };

  const applyPreset = async (preset) => {
    setPresetSaving(true);
    try {
      const res = await apiFetch("/api/preferences/preset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset }),
      });
      if (res.ok) {
        setPresetValue(preset);
        setOauthNotice("Creator style updated.");
      }
    } catch (error) {
      console.error("Error saving preset:", error);
    } finally {
      setPresetSaving(false);
    }
  };

  const updatePolicy = (action, value) => {
    setActionPolicy((prev) => ({ ...prev, [action]: value }));
  };

  const savePolicy = async () => {
    setPolicySaving(true);
    try {
      await apiFetch("/policy", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy: actionPolicy }),
      });
      setOauthNotice("Policy saved.");
    } catch (error) {
      console.error("Error saving policy:", error);
    } finally {
      setPolicySaving(false);
    }
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      await saveSettings();
      setOauthNotice("Settings saved successfully!");
    } catch (error) {
      console.error("Error saving settings:", error);
      setOauthNotice("Local settings saved. Backend sync failed.");
    } finally {
      setSaving(false);
    }
  };

  const handleRoleChange = async (role) => {
    setRoleSaving(true);
    try {
      await apiFetch("/auth/role", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      await fetchProfile();
      await refreshSettings();
    } catch (error) {
      console.error("Error updating role:", error);
    } finally {
      setRoleSaving(false);
    }
  };

  const handleActiveStreamer = async (streamerId) => {
    setActiveStreamerSaving(true);
    try {
      await apiFetch("/auth/active-streamer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ streamer_id: streamerId }),
      });
      setActiveStreamerId(streamerId);
      setOauthNotice("Active streamer updated.");
    } catch (error) {
      console.error("Error updating active streamer:", error);
    } finally {
      setActiveStreamerSaving(false);
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    clearActiveStreamerId();
    clearAuthBypass();
    setAuthBypassEnabled(false);
    window.location.href = "/auth";
  };

  const updateSuiteSection = (section, patch) => {
    setSettings((prev) => ({
      ...prev,
      streamerAiSuite: {
        ...(prev?.streamerAiSuite || {}),
        [section]: {
          ...((prev?.streamerAiSuite || {})[section] || {}),
          ...patch,
        },
      },
    }));
  };

  const updateSuiteNested = (section, nestedKey, patch) => {
    setSettings((prev) => ({
      ...prev,
      streamerAiSuite: {
        ...(prev?.streamerAiSuite || {}),
        [section]: {
          ...((prev?.streamerAiSuite || {})[section] || {}),
          [nestedKey]: {
            ...(((prev?.streamerAiSuite || {})[section] || {})[nestedKey] || {}),
            ...patch,
          },
        },
      },
    }));
  };

  const aiSuite = settings?.streamerAiSuite || {};

  if (loading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${isDarkMode ? 'bg-[#08070F] text-[#EDE8FF]' : 'text-black'}`}>

        <div className="text-center">
          <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="font-medium">Configuring Kazumi Core...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${isDarkMode ? 'bg-[#08070F] text-[#EDE8FF]' : 'text-black'} p-6 md:p-10`}>
      {/* Breadcrumb */}
      <div className="text-sm text-[#6B6480] mb-1 flex items-center justify-between">

        <div>
          <a href="/dashboard" className="hover:text-black">Dashboard</a>
          <span className="mx-1.5 text-gray-300">/</span>
          <span>Settings</span>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${backendStatus === 'online' ? 'bg-green-500' : 'bg-red-500 animate-pulse'}`}></div>
          <span className="text-[10px] font-bold uppercase tracking-widest">Backend: {backendStatus}</span>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 gap-4">
        <h1 className="text-3xl md:text-4xl font-bold">Control Center</h1>
        <div className="flex gap-3">
          <button 
            onClick={() => updateSetting("appearance", "darkMode", !isDarkMode)}
            className={`p-2 rounded-md border ${isDarkMode ? 'border-[#242235] hover:bg-[#1A1828]' : 'border-[#242235] hover:bg-black/5'}`}
          >

            {isDarkMode ? <Sun className="w-5 h-5 text-yellow-500" /> : <Moon className="w-5 h-5 text-gray-600" />}
          </button>
          <button
                onClick={handleSaveSettings}
                disabled={saving}
                className="flex items-center gap-2 px-6 py-2 rounded-md text-white disabled:opacity-50 transition-all shadow-lg"
                style={{ background: "linear-gradient(135deg, #7C5CFC, #9060E8)" }}
              >

            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? "Syncing..." : "Save Config"}
          </button>
        </div>
      </div>
      {oauthNotice && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 text-green-800 text-sm px-4 py-2">
          {oauthNotice}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Sidebar */}
        <div className="lg:col-span-1">
                <div className={`rounded-xl border ${isDarkMode ? 'border-[#242235] bg-[#1A1828]/50' : 'border-[#242235] bg-[#131120]'} p-4 sticky top-6`}>

            <h2 className="text-xs font-bold uppercase text-[#6B6480] mb-4 px-2">Configuration</h2>

            <nav className="space-y-1">
              {[
                { icon: User, label: "Profile", id: "profile" },
                { icon: Brain, label: "AI Personality", id: "ai" },
                { icon: Mic, label: "Voice Engine", id: "voice" },
                { icon: Link, label: "Integrations", id: "integrations" },
                { icon: Shield, label: "Action Policy", id: "policy" },

                { icon: Zap, label: "Automation", id: "automation" },
                { icon: Brain, label: "Streamer AI", id: "streamer-ai" },
              ].map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isDarkMode ? 'hover:bg-gray-800 text-gray-300' : 'hover:bg-black/5 hover:shadow-sm text-gray-600'
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </a>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="lg:col-span-2 space-y-8 pb-20">
          {/* Profile */}
          <div id="profile" className={`rounded-xl border ${isDarkMode ? 'border-[#242235]' : 'border-[#242235]'} p-6 bg-[#131120]`}>

            <div className="flex items-center gap-3 mb-6">
              <User className="w-5 h-5 text-emerald-500" />
              <h2 className="text-lg font-bold">Profile</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold mb-2">Display Name</label>
                <input
                  type="text"
                  value={settings?.profile?.displayName || ""}
                  onChange={(e) => updateSetting("profile", "displayName", e.target.value)}
                  className={`w-full px-4 py-2 rounded-md border ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-black/10'}`}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-2">Platforms (comma separated)</label>
                <input
                  type="text"
                  value={platformInput}
                  onChange={(e) => {
                    const next = e.target.value;
                    setPlatformInput(next);
                    const platforms = next
                      .split(",")
                      .map((p) => p.trim())
                      .filter(Boolean);
                    updateSetting("profile", "platforms", platforms);
                  }}
                  className={`w-full px-4 py-2 rounded-md border ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-black/10'}`}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-2">Email</label>
                <input
                  type="text"
                  value={profileUser?.email || ""}
                  disabled
                  className={`w-full px-4 py-2 rounded-md border ${isDarkMode ? 'bg-[#1A1828] border-[#242235]' : 'bg-[#131120] border-[#242235]'} text-[#6B6480]`}
                />

              </div>
              <div>
                <label className="block text-sm font-semibold mb-2">Role</label>
                <select
                  value={profileUser?.role || "streamer"}
                  onChange={(e) => handleRoleChange(e.target.value)}
                  disabled={roleSaving}
                  className={`w-full px-4 py-2 rounded-md border ${isDarkMode ? 'bg-[#1A1828] border-[#242235]' : 'bg-[#131120] border-[#242235]'}`}
                >

                  <option value="streamer">Streamer</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
            </div>

            {profileUser?.role === "viewer" && (
              <div className="mt-4">
                <label className="block text-sm font-semibold mb-2">Active Streamer</label>
                <div className="flex flex-col md:flex-row gap-3">
                  <select
                    className={`flex-1 px-4 py-2 rounded-md border ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-black/10'}`}
                    value={activeStreamerId || ""}
                    onChange={(e) => handleActiveStreamer(Number(e.target.value))}
                    disabled={activeStreamerSaving}
                  >
                    <option value="" disabled>Select a streamer</option>
                    {streamerList.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.display_name || s.username}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleActiveStreamer(Number(streamerList[0]?.id || 0))}
                    disabled={activeStreamerSaving || streamerList.length === 0}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm"
                  >
                    {activeStreamerSaving ? "Saving..." : "Set Active"}
                  </button>
                </div>
              </div>
            )}

              <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={handleSaveSettings}
                disabled={saving}
                className="px-4 py-2 rounded-md text-white text-sm disabled:opacity-50"
                style={{ background: "linear-gradient(135deg, #7C5CFC, #9060E8)" }}
              >
                {saving ? "Saving..." : "Save Profile"}
              </button>
              <button
                onClick={handleLogout}
                className="px-4 py-2 border border-red-300 text-red-600 rounded-md text-sm"
              >
                Log out
              </button>
              <a
                href="/onboarding"
                className="px-4 py-2 border border-purple-300 text-purple-600 rounded-md text-sm"
              >
                Re-run Setup Wizard
              </a>
            </div>

          </div>
          
          {/* AI Personality (The Real Logic) */}
          <div id="ai" className={`rounded-xl border ${isDarkMode ? 'border-gray-800' : 'border-black/10'} p-6 bg-white`}>
            <div className="flex items-center gap-3 mb-6">
              <Brain className="w-5 h-5 text-purple-500" />
              <h2 className="text-lg font-bold">Kazumi Brain (LLM)</h2>
            </div>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-semibold mb-2">Personality Preset</label>
                <select 
                  value={settings?.ai?.personality}
                  onChange={(e) => updateSetting("ai", "personality", e.target.value)}
                  className={`w-full px-4 py-2 rounded-md border ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-black/10'}`}
                >
                  <option value="helpful">Helpful Director</option>
                  <option value="sarcastic">Sarcastic/Witty</option>
                  <option value="professional">Data Focused</option>
                  <option value="chaotic">Chaotic Gamer</option>
                </select>
              </div>
              <label className="flex items-center justify-between p-3 rounded-lg border border-dashed border-gray-300">
                <div className="text-sm font-medium">Use Groq Brain for Decisions</div>
                <input 
                  type="checkbox" 
                  checked={Boolean(settings?.ai?.useGroq)}
                  onChange={(e) => updateSetting("ai", "useGroq", e.target.checked)}
                />
              </label>
              <div>
                <label className="block text-sm font-semibold mb-2">Creator Style (Moment Scoring)</label>
                <select
                  value={presetValue}
                  onChange={(e) => applyPreset(e.target.value)}
                  className={`w-full px-4 py-2 rounded-md border ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-black/10'}`}
                  disabled={presetSaving}
                >
                  <option value="balanced">Balanced</option>
                  {(presetOptions || []).map((preset) => (
                    <option key={preset.name} value={preset.name}>
                      {preset.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-2">
                  Presets tune what Kazumi considers “clip worthy” from day one.
                </p>
              </div>
              <div>
                <label className="block text-sm font-semibold mb-2 justify-between">
                  Creativity (Temperature) <span>{settings?.ai?.creativeRange * 100}%</span>
                </label>
                <input 
                  type="range" min="0" max="1" step="0.1"
                  value={settings?.ai?.creativeRange}
                  onChange={(e) => updateSetting("ai", "creativeRange", parseFloat(e.target.value))}
                  className="w-full accent-black" 
                />
              </div>
            </div>
          </div>

          {/* Voice Settings */}
          <div id="voice" className={`rounded-xl border ${isDarkMode ? 'border-[#242235]' : 'border-[#242235]'} p-6 bg-[#131120]`}>

            <div className="flex items-center gap-3 mb-6">
              <Mic className="w-5 h-5 text-blue-500" />
              <h2 className="text-lg font-bold">Voice Engine</h2>
            </div>
            <div className="space-y-4">
                  <div>
                <label className="block text-sm font-semibold mb-2">Trigger Phrase</label>

                <input
                  type="text"
                  placeholder="e.g., 'Hey Kazumi'"
                  value={settings?.voice?.triggerWord || ""}
                  onChange={(e) => updateSetting("voice", "triggerWord", e.target.value)}
                  className={`w-full px-4 py-2 rounded-md border ${isDarkMode ? 'bg-[#1A1828] border-[#242235]' : 'bg-[#131120] border-[#242235]'}`}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">OBS WebSocket Password</label>
                <input
                  type="password"
                  placeholder="Your OBS WebSocket password"
                  value={settings?.obs?.password || ""}
                  onChange={(e) => updateSetting("obs", "password", e.target.value)}
                  className="w-full px-4 py-2 rounded-md border border-[#242235] bg-[#1A1828] text-[#EDE8FF]"
                />
                <p className="text-xs text-[#6B6480] mt-1">
                  Found in OBS → Tools → WebSocket Server Settings
                </p>
              </div>

              <label className="flex items-center justify-between p-3 rounded-lg border border-dashed border-gray-300">
                <div className="text-sm font-medium">Continuous Listening</div>
                <input 
                  type="checkbox" 
                  checked={settings?.voice?.enabled} 
                  onChange={(e) => updateSetting("voice", "enabled", e.target.checked)}
                />
              </label>

            </div>
          </div>

          {/* API Integrations */}
          <div id="integrations" className={`rounded-xl border ${isDarkMode ? 'border-gray-800' : 'border-black/10'} p-6 bg-white`}>
            <div className="flex items-center gap-3 mb-6">
              <Link className="w-5 h-5 text-green-500" />
              <h2 className="text-lg font-bold">Connected Services</h2>
            </div>
            {/* Setup Wizard */}
            <div className="mb-6 rounded-xl border border-black/10 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold">Integration Setup Wizard</div>
                <div className="text-[10px] text-gray-500">Step {wizardStep} of 3</div>
              </div>
              {wizardStep === 1 && (
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="font-semibold text-gray-900">1) Configure OAuth keys</div>
                  <div>Set `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` in `.env`.</div>
                  <button
                    onClick={() => setWizardStep(2)}
                    className="mt-2 px-3 py-1.5 text-xs rounded-md border border-gray-300"
                  >
                    Next
                  </button>
                </div>
              )}
              {wizardStep === 2 && (
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="font-semibold text-gray-900">2) Connect platforms</div>
                  <div>Use the connect buttons below to complete OAuth.</div>
                  <button
                    onClick={() => setWizardStep(3)}
                    className="mt-2 px-3 py-1.5 text-xs rounded-md border border-gray-300"
                  >
                    Next
                  </button>
                </div>
              )}
              {wizardStep === 3 && (
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="font-semibold text-gray-900">3) Configure metadata</div>
                  <div>Enter IDs + webhook URL only (broadcaster_id, moderator_id, live_chat_id). Never enter account passwords.</div>
                  <button
                    onClick={() => setWizardStep(1)}
                    className="mt-2 px-3 py-1.5 text-xs rounded-md border border-gray-300"
                  >
                    Restart wizard
                  </button>
                </div>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { key: "twitch", label: "Twitch" },
                { key: "youtube", label: "YouTube" },
                { key: "obs", label: "OBS WebSocket" },
                { key: "groq", label: "Groq (Llama 3)" },
              ].map((service) => {
                const status = serviceStatusMap[service.key] || { connected: false, detail: "Unknown" };
                return (
                  <div key={service.key} className={`p-4 rounded-lg border ${isDarkMode ? 'bg-gray-900 border-gray-800' : 'bg-black/5 border-black/10'} flex items-center justify-between gap-2`}>
                    <div>
                      <div className="text-sm font-bold">{service.label}</div>
                      <div className="text-[11px] text-gray-500 mt-1">{status.detail}</div>
                    </div>
                    <span className={`px-2 py-1 text-[10px] font-black uppercase rounded ${
                      status.connected ? 'bg-green-500/10 text-green-500' : 'bg-gray-200 text-gray-600'
                    }`}>
                      {status.connected ? 'Connected' : 'Not Connected'}
                    </span>
                  </div>
                );
              })}
            </div>
            {/* Diagnostics */}
            <div className="mt-6 rounded-xl border border-black/10 p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold">Diagnostics</div>
                <button
                  onClick={fetchDiagnostics}
                  className="px-2 py-1 text-xs rounded-md border border-gray-300"
                  disabled={diagLoading}
                >
                  {diagLoading ? "Checking..." : "Refresh"}
                </button>
              </div>
              {diagnostics ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="rounded-lg border border-black/10 p-3">
                    <div className="font-semibold mb-1 flex items-center gap-2">
                      {diagnostics.twitch?.token_valid ? <CheckCircle className="w-3 h-3 text-green-600" /> : <AlertTriangle className="w-3 h-3 text-yellow-600" />}
                      Twitch
                    </div>
                    <div>Client ID set: {String(Boolean(diagnostics.twitch?.client_id_set))}</div>
                    <div>Client Secret set: {String(Boolean(diagnostics.twitch?.client_secret_set))}</div>
                    <div>Webhook secret set: {String(Boolean(diagnostics.twitch?.webhook_secret_set))}</div>
                    <div>Token valid: {String(Boolean(diagnostics.twitch?.token_valid))}</div>
                    {diagnostics.twitch?.last_error && (
                      <div className="text-red-600 mt-1">Error: {String(diagnostics.twitch.last_error)}</div>
                    )}
                  </div>
                  <div className="rounded-lg border border-black/10 p-3">
                    <div className="font-semibold mb-1 flex items-center gap-2">
                      {diagnostics.youtube?.token_valid ? <CheckCircle className="w-3 h-3 text-green-600" /> : <AlertTriangle className="w-3 h-3 text-yellow-600" />}
                      YouTube
                    </div>
                    <div>Client ID set: {String(Boolean(diagnostics.youtube?.client_id_set))}</div>
                    <div>Client Secret set: {String(Boolean(diagnostics.youtube?.client_secret_set))}</div>
                    <div>Token valid: {String(Boolean(diagnostics.youtube?.token_valid))}</div>
                    {diagnostics.youtube?.last_error && (
                      <div className="text-red-600 mt-1">Error: {String(diagnostics.youtube.last_error)}</div>
                    )}
                  </div>
                  <div className="rounded-lg border border-black/10 p-3">
                    <div className="font-semibold mb-1 flex items-center gap-2">
                      {diagnostics.obs?.connected ? <CheckCircle className="w-3 h-3 text-green-600" /> : <AlertTriangle className="w-3 h-3 text-yellow-600" />}
                      OBS WebSocket
                    </div>
                    <div>Connected: {String(Boolean(diagnostics.obs?.connected))}</div>
                    <div>Streaming: {String(Boolean(diagnostics.obs?.streaming))}</div>
                    <div>Recording: {String(Boolean(diagnostics.obs?.recording))}</div>
                    {diagnostics.obs?.last_error && (
                      <div className="text-red-600 mt-1">Error: {String(diagnostics.obs.last_error)}</div>
                    )}
                  </div>
                  <div className="rounded-lg border border-black/10 p-3">
                    <div className="font-semibold mb-1 flex items-center gap-2">
                      {diagnostics.groq?.reachable ? <CheckCircle className="w-3 h-3 text-green-600" /> : <AlertTriangle className="w-3 h-3 text-yellow-600" />}
                      Groq
                    </div>
                    <div>API key set: {String(Boolean(diagnostics.groq?.api_key_set))}</div>
                    <div>Reachable: {String(Boolean(diagnostics.groq?.reachable))}</div>
                    {Number.isFinite(Number(diagnostics.groq?.model_count)) && (
                      <div>Models visible: {Number(diagnostics.groq?.model_count)}</div>
                    )}
                    {diagnostics.groq?.last_error && (
                      <div className="text-red-600 mt-1">Error: {String(diagnostics.groq.last_error)}</div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-xs text-gray-500">No diagnostics yet.</div>
              )}
            </div>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => connectPlatform("twitch")}
                className="px-4 py-2 bg-black text-white rounded-md text-sm"
              >
                Connect Twitch
              </button>
              <button
                onClick={() => connectPlatform("youtube")}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm"
              >
                Connect YouTube
              </button>
            </div>
            <div className="mt-3 text-xs rounded-md border border-emerald-200 bg-emerald-50 text-emerald-900 px-3 py-2">
              Kazumi never asks for streamer passwords. Use OAuth connect buttons, then save IDs/webhooks below.
            </div>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className={`p-4 rounded-lg border ${isDarkMode ? 'border-gray-800' : 'border-black/10'} bg-white`}>
                <div className="text-sm font-semibold mb-2">Twitch Setup</div>
                <input
                  value={twitchBroadcasterId}
                  onChange={(e) => setTwitchBroadcasterId(e.target.value)}
                  placeholder="Broadcaster ID"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm mb-2"
                />
                <input
                  value={twitchModeratorId}
                  onChange={(e) => setTwitchModeratorId(e.target.value)}
                  placeholder="Moderator ID (recommended)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm mb-2"
                />
                <input
                  value={twitchWebhookUrl}
                  onChange={(e) => setTwitchWebhookUrl(e.target.value)}
                  placeholder="Webhook URL"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm mb-3"
                />
                <div className="text-[11px] text-gray-500 mb-3">
                  Tip: if you are moderating your own channel, moderator ID can match broadcaster ID.
                </div>
                <label className="flex items-center justify-between text-xs text-gray-600 mb-3">
                  Auto-subscribe on start
                  <input
                    type="checkbox"
                    checked={twitchAutoSubscribe}
                    onChange={(e) => {
                      const next = e.target.checked;
                      setTwitchAutoSubscribe(next);
                      saveIntegrationMeta("twitch", {
                        broadcaster_id: twitchBroadcasterId,
                        moderator_id: twitchModeratorId,
                        webhook_url: twitchWebhookUrl,
                        auto_subscribe: next,
                      });
                    }}
                  />
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={() =>
                      saveIntegrationMeta("twitch", {
                        broadcaster_id: twitchBroadcasterId,
                        moderator_id: twitchModeratorId,
                        webhook_url: twitchWebhookUrl,
                        auto_subscribe: twitchAutoSubscribe,
                      })
                    }
                    className="px-3 py-2 bg-black text-white rounded-md text-sm"
                  >
                    Save
                  </button>
                  <button
                    onClick={handleTwitchSubscribe}
                    disabled={twitchSubscribeLoading}
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                  >
                    {twitchSubscribeLoading ? "Subscribing..." : "Subscribe"}
                  </button>
                </div>
              </div>

              <div className={`p-4 rounded-lg border ${isDarkMode ? 'border-gray-800' : 'border-black/10'} bg-white`}>
                <div className="text-sm font-semibold mb-2">YouTube Setup</div>
                <input
                  value={youtubeLiveChatId}
                  onChange={(e) => setYoutubeLiveChatId(e.target.value)}
                  placeholder="Live Chat ID"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm mb-3"
                />
                <label className="flex items-center justify-between text-xs text-gray-600 mb-3">
                  Auto-poll on start
                  <input
                    type="checkbox"
                    checked={youtubeAutoPoll}
                    onChange={(e) => {
                      const next = e.target.checked;
                      setYoutubeAutoPoll(next);
                      saveIntegrationMeta("youtube", {
                        live_chat_id: youtubeLiveChatId,
                        auto_poll: next,
                      });
                    }}
                  />
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={() =>
                      saveIntegrationMeta("youtube", {
                        live_chat_id: youtubeLiveChatId,
                        auto_poll: youtubeAutoPoll,
                      })
                    }
                    className="px-3 py-2 bg-black text-white rounded-md text-sm"
                  >
                    Save
                  </button>
                  <button
                    onClick={handleYoutubePoll}
                    disabled={youtubePollLoading}
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                  >
                    {youtubePollLoading ? "Polling..." : "Poll"}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Action Policy */}
          <div id="policy" className={`rounded-xl border ${isDarkMode ? 'border-gray-800' : 'border-black/10'} p-6 bg-white`}>
            <div className="flex items-center gap-3 mb-6">
              <Shield className="w-5 h-5 text-red-500" />
              <h2 className="text-lg font-bold">Viewer Action Policy</h2>
            </div>
            <div className="space-y-4">
              {[
                { action: "chat", label: "Chat / Questions" },
                { action: "ask_lore", label: "Lore Queries" },
                { action: "request_clip", label: "Clip Requests" },
                { action: "vote_scene", label: "Scene Voting" },
                { action: "suggestion", label: "Suggestions" },
                { action: "switch_scene", label: "Switch Scene" },
                { action: "mute_mic", label: "Mute Mic" },
                { action: "unmute_mic", label: "Unmute Mic" },
                { action: "start_recording", label: "Start Recording" },
                { action: "stop_recording", label: "Stop Recording" },
                { action: "start_streaming", label: "Start Streaming" },
                { action: "stop_streaming", label: "Stop Streaming" },
                { action: "panic_mode", label: "Panic Mode" },
                { action: "restart_engine", label: "Restart Engine" },
              ].map((item) => (
                <label key={item.action} className="flex items-center justify-between text-sm">
                  <span className="font-medium">{item.label}</span>
                  <select
                    value={actionPolicy?.[item.action] || "approve"}
                    onChange={(e) => updatePolicy(item.action, e.target.value)}
                    className={`px-3 py-2 rounded-md border text-xs ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-black/10'}`}
                  >
                    <option value="allow">Allow</option>
                    <option value="approve">Needs Approval</option>
                    <option value="deny">Deny</option>
                  </select>
                </label>
              ))}
            </div>
            <div className="mt-5">
              <button
                onClick={savePolicy}
                disabled={policySaving}
                className="px-4 py-2 bg-black text-white rounded-md text-sm disabled:opacity-50"
              >
                {policySaving ? "Saving..." : "Save Policy"}
              </button>
            </div>
          </div>

          {/* Automation */}
          <div id="automation" className={`rounded-xl border ${isDarkMode ? 'border-gray-800' : 'border-black/10'} p-6 bg-white`}>
            <div className="flex items-center gap-3 mb-6">
              <Zap className="w-5 h-5 text-yellow-500" />
              <h2 className="text-lg font-bold">Automation</h2>
            </div>
            <div className="space-y-3">
              {[
                { label: "Auto-Generate Clips", key: "autoClipping" },
                { label: "Smart Scene Switching", key: "sceneControl" },
                { label: "Auto-Highlights", key: "autoHighlights" }
              ].map((opt) => (
                <label key={opt.key} className="flex items-center justify-between py-2">
                  <span className="text-sm font-medium">{opt.label}</span>
                  <div className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer"
                      checked={settings?.automation?.[opt.key]}
                      onChange={(e) => updateSetting("automation", opt.key, e.target.checked)}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-black"></div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {profileUser?.role === "streamer" && (
            <div id="streamer-ai" className={`rounded-xl border ${isDarkMode ? 'border-gray-800' : 'border-black/10'} p-6 bg-white`}>
              <div className="flex items-center justify-between gap-3 mb-6">
                <div className="flex items-center gap-3">
                  <Brain className="w-5 h-5 text-indigo-500" />
                  <h2 className="text-lg font-bold">Streamer AI Suite</h2>
                </div>
                <button
                  onClick={fetchStreamerAiStatus}
                  className="px-3 py-1.5 text-xs rounded-md border border-gray-300"
                  disabled={streamerAiLoading}
                >
                  {streamerAiLoading ? "Refreshing..." : "Refresh Status"}
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5 text-xs">
                <div className="rounded-lg border border-black/10 p-3">
                  <div className="text-gray-500 mb-1">Last Activity</div>
                  <div className="font-semibold">{streamerAiStatus?.last_activity_at ? new Date(streamerAiStatus.last_activity_at).toLocaleTimeString() : "n/a"}</div>
                </div>
                <div className="rounded-lg border border-black/10 p-3">
                  <div className="text-gray-500 mb-1">Last Prompt</div>
                  <div className="font-semibold">{streamerAiStatus?.last_prompt_at ? new Date(streamerAiStatus.last_prompt_at).toLocaleTimeString() : "n/a"}</div>
                </div>
                <div className="rounded-lg border border-black/10 p-3">
                  <div className="text-gray-500 mb-1">Last Viral Trigger</div>
                  <div className="font-semibold">{streamerAiStatus?.last_viral_post_at ? new Date(streamerAiStatus.last_viral_post_at).toLocaleTimeString() : "n/a"}</div>
                </div>
              </div>

              <div className="space-y-5">
                <div className="rounded-lg border border-black/10 p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-sm">1. Dynamic Prompter</div>
                    <input
                      type="checkbox"
                      checked={Boolean(aiSuite?.dynamicPrompter?.enabled)}
                      onChange={(e) => updateSuiteSection("dynamicPrompter", { enabled: e.target.checked })}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
                    <label>
                      Silence Seconds
                      <input
                        type="number"
                        min="5"
                        max="120"
                        value={aiSuite?.dynamicPrompter?.silenceSeconds ?? 10}
                        onChange={(e) => updateSuiteSection("dynamicPrompter", { silenceSeconds: Number(e.target.value) || 10 })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      />
                    </label>
                    <label>
                      Cooldown Seconds
                      <input
                        type="number"
                        min="30"
                        max="900"
                        value={aiSuite?.dynamicPrompter?.cooldownSeconds ?? 90}
                        onChange={(e) => updateSuiteSection("dynamicPrompter", { cooldownSeconds: Number(e.target.value) || 90 })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      />
                    </label>
                  </div>
                </div>

                <div className="rounded-lg border border-black/10 p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-sm">2. Cross-Platform Viral Engine</div>
                    <input
                      type="checkbox"
                      checked={Boolean(aiSuite?.crossPlatformViralEngine?.enabled)}
                      onChange={(e) => updateSuiteSection("crossPlatformViralEngine", { enabled: e.target.checked })}
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3 text-xs">
                    <label className="flex items-center justify-between border border-black/10 rounded-md px-2 py-2">
                      Auto Post
                      <input
                        type="checkbox"
                        checked={Boolean(aiSuite?.crossPlatformViralEngine?.autoPost)}
                        onChange={(e) => updateSuiteSection("crossPlatformViralEngine", { autoPost: e.target.checked })}
                      />
                    </label>
                    <label>
                      Min Hype Score
                      <input
                        type="number"
                        min="40"
                        max="100"
                        value={aiSuite?.crossPlatformViralEngine?.minHypeScore ?? 75}
                        onChange={(e) => updateSuiteSection("crossPlatformViralEngine", { minHypeScore: Number(e.target.value) || 75 })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      />
                    </label>
                    <label>
                      Cooldown Seconds
                      <input
                        type="number"
                        min="60"
                        max="1800"
                        value={aiSuite?.crossPlatformViralEngine?.cooldownSeconds ?? 180}
                        onChange={(e) => updateSuiteSection("crossPlatformViralEngine", { cooldownSeconds: Number(e.target.value) || 180 })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      />
                    </label>
                  </div>
                </div>

                <div className="rounded-lg border border-black/10 p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-sm">3. Sentiment Shield</div>
                    <input
                      type="checkbox"
                      checked={Boolean(aiSuite?.sentimentShield?.enabled)}
                      onChange={(e) => updateSuiteSection("sentimentShield", { enabled: e.target.checked })}
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3 text-xs">
                    <label className="flex items-center justify-between border border-black/10 rounded-md px-2 py-2">
                      Nuance Detection
                      <input
                        type="checkbox"
                        checked={Boolean(aiSuite?.sentimentShield?.nuanceDetection)}
                        onChange={(e) => updateSuiteSection("sentimentShield", { nuanceDetection: e.target.checked })}
                      />
                    </label>
                    <label>
                      Raid Window (s)
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={aiSuite?.sentimentShield?.antiHateRaid?.windowSeconds ?? 2}
                        onChange={(e) => updateSuiteNested("sentimentShield", "antiHateRaid", { windowSeconds: Number(e.target.value) || 2 })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      />
                    </label>
                    <label>
                      Raid Threshold
                      <input
                        type="number"
                        min="5"
                        max="200"
                        value={aiSuite?.sentimentShield?.antiHateRaid?.joinThreshold ?? 25}
                        onChange={(e) => updateSuiteNested("sentimentShield", "antiHateRaid", { joinThreshold: Number(e.target.value) || 25 })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      />
                    </label>
                  </div>
                </div>

                <div className="rounded-lg border border-black/10 p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-sm">4. One-Click Content Farm</div>
                    <input
                      type="checkbox"
                      checked={Boolean(aiSuite?.contentFarm?.enabled)}
                      onChange={(e) => updateSuiteSection("contentFarm", { enabled: e.target.checked })}
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 text-xs">
                    <label>
                      Caption Style
                      <select
                        value={aiSuite?.contentFarm?.autoCaptionStyle || "hormozi"}
                        onChange={(e) => updateSuiteSection("contentFarm", { autoCaptionStyle: e.target.value })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      >
                        <option value="hormozi">Hormozi</option>
                        <option value="clean">Clean</option>
                        <option value="dynamic">Dynamic</option>
                      </select>
                    </label>
                    <label>
                      Crop Target
                      <select
                        value={aiSuite?.contentFarm?.verticalCropTarget || "face_plus_gameplay"}
                        onChange={(e) => updateSuiteSection("contentFarm", { verticalCropTarget: e.target.value })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      >
                        <option value="face_plus_gameplay">Face + Gameplay</option>
                        <option value="gameplay_focus">Gameplay Focus</option>
                        <option value="face_focus">Face Focus</option>
                      </select>
                    </label>
                  </div>
                </div>

                <div className="rounded-lg border border-black/10 p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-sm">5. Stream Doctor</div>
                    <input
                      type="checkbox"
                      checked={Boolean(aiSuite?.streamDoctor?.enabled)}
                      onChange={(e) => updateSuiteSection("streamDoctor", { enabled: e.target.checked })}
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3 text-xs">
                    <label>
                      Dropped Frames Warn
                      <input
                        type="number"
                        min="30"
                        max="2000"
                        value={aiSuite?.streamDoctor?.droppedFramesWarn ?? 120}
                        onChange={(e) => updateSuiteSection("streamDoctor", { droppedFramesWarn: Number(e.target.value) || 120 })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      />
                    </label>
                    <label>
                      High Bitrate (kbps)
                      <input
                        type="number"
                        min="2000"
                        max="12000"
                        value={aiSuite?.streamDoctor?.highBitrateKbps ?? 6000}
                        onChange={(e) => updateSuiteSection("streamDoctor", { highBitrateKbps: Number(e.target.value) || 6000 })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      />
                    </label>
                    <label>
                      Mic Source Name
                      <input
                        type="text"
                        value={aiSuite?.streamDoctor?.micSourceName || "Mic/Aux"}
                        onChange={(e) => updateSuiteSection("streamDoctor", { micSourceName: e.target.value })}
                        className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                      />
                    </label>
                  </div>
                </div>

                <div className="rounded-lg border border-black/10 p-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-semibold text-sm">6. Spoiler Filter</div>
                        <input
                          type="checkbox"
                          checked={Boolean(aiSuite?.spoilerFilter?.enabled)}
                          onChange={(e) => updateSuiteSection("spoilerFilter", { enabled: e.target.checked })}
                        />
                      </div>
                      <label>
                        Action
                        <select
                          value={aiSuite?.spoilerFilter?.action || "blur_for_streamer"}
                          onChange={(e) => updateSuiteSection("spoilerFilter", { action: e.target.value })}
                          className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                        >
                          <option value="blur_for_streamer">Blur for Streamer</option>
                          <option value="delete">Delete</option>
                        </select>
                      </label>
                      <label className="block mt-2">
                        Keywords (comma/new line)
                        <textarea
                          value={(aiSuite?.spoilerFilter?.keywords || []).join(", ")}
                          onChange={(e) => {
                            const keywords = e.target.value
                              .split(/[\n,]/)
                              .map((k) => k.trim())
                              .filter(Boolean)
                              .slice(0, 80);
                            updateSuiteSection("spoilerFilter", { keywords });
                          }}
                          className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md min-h-[72px]"
                        />
                      </label>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-semibold text-sm">7. Empathy Guard</div>
                          <input
                            type="checkbox"
                            checked={Boolean(aiSuite?.empathyGuard?.enabled)}
                            onChange={(e) => updateSuiteSection("empathyGuard", { enabled: e.target.checked })}
                          />
                        </div>
                        <label className="flex items-center justify-between border border-black/10 rounded-md px-2 py-2">
                          Auto Whisper Resources
                          <input
                            type="checkbox"
                            checked={Boolean(aiSuite?.empathyGuard?.autoWhisperResources)}
                            onChange={(e) => updateSuiteSection("empathyGuard", { autoWhisperResources: e.target.checked })}
                          />
                        </label>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-semibold text-sm">8. Audio Safe Mode</div>
                          <input
                            type="checkbox"
                            checked={Boolean(aiSuite?.audioSafeMode?.enabled)}
                            onChange={(e) => updateSuiteSection("audioSafeMode", { enabled: e.target.checked })}
                          />
                        </div>
                        <label className="block">
                          Desktop Audio Source
                          <input
                            type="text"
                            value={aiSuite?.audioSafeMode?.desktopAudioSource || "Desktop Audio"}
                            onChange={(e) => updateSuiteSection("audioSafeMode", { desktopAudioSource: e.target.value })}
                            className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                          />
                        </label>
                        <label className="block mt-2">
                          Copyright Threshold
                          <input
                            type="number"
                            min="0.5"
                            max="1"
                            step="0.05"
                            value={aiSuite?.audioSafeMode?.copyrightThreshold ?? 0.8}
                            onChange={(e) => updateSuiteSection("audioSafeMode", { copyrightThreshold: Number(e.target.value) || 0.8 })}
                            className="w-full mt-1 px-2 py-1 border border-black/10 rounded-md"
                          />
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Dev Tools */}
          <div className={`rounded-xl border ${isDarkMode ? 'border-gray-800' : 'border-black/10'} p-6 bg-white`}>
            <div className="flex items-center gap-3 mb-4">
              <Server className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-bold">Dev Tools</h2>
            </div>
            <label className="flex items-center justify-between text-sm">
              <span className="font-medium">Bypass Auth (local only)</span>
              <input
                type="checkbox"
                checked={devBypass}
                onChange={(e) => {
                  const next = e.target.checked;
                  setDevBypass(next);
                  setAuthBypassEnabled(next);
                  window.location.reload();
                }}
              />
            </label>
            <p className="text-xs text-gray-500 mt-2">
              Enables Demo Mode for UI testing without sign-in.
            </p>
          </div>

        </div>
      </div>
    </div>
  );
}

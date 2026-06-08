"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/apiClient";
import { CheckCircle, Circle, Server, Shield, Zap } from "lucide-react";

export default function SetupWizardPage() {
  const [health, setHealth] = useState(null);
  const [connections, setConnections] = useState([]);
  const [obsStatus, setObsStatus] = useState(null);
  const [metadata, setMetadata] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [healthRes, connRes, obsRes, metadataRes] = await Promise.all([
          apiFetch("/api/health"),
          apiFetch("/integrations/status"),
          apiFetch("/obs/status"),
          apiFetch("/integrations/metadata"),
        ]);
        setHealth(await healthRes.json());
        const connData = await connRes.json();
        setConnections(connData.connections || []);
        setObsStatus(await obsRes.json());
        const metadataData = await metadataRes.json();
        setMetadata(metadataData.connections || []);
      } catch {
        setHealth(null);
        setConnections([]);
        setObsStatus(null);
        setMetadata([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const isConnected = (platform) =>
    connections.some((c) => c.platform === platform && c.connected);

  const findMeta = (platform) =>
    metadata.find((item) => item.platform === platform)?.meta || {};

  const twitchMeta = findMeta("twitch");
  const youtubeMeta = findMeta("youtube");
  const hasTwitchMetadata = !isConnected("twitch")
    ? true
    : Boolean(twitchMeta.broadcaster_id);
  const hasYoutubeMetadata = !isConnected("youtube")
    ? true
    : Boolean(youtubeMeta.live_chat_id);
  const metadataReady = hasTwitchMetadata && hasYoutubeMetadata;

  const Step = ({ done, title, desc, action }) => (
    <div className="flex items-start gap-3 border border-gray-200 rounded-lg p-4">
      <div className="mt-1">
        {done ? (
          <CheckCircle className="w-5 h-5 text-green-600" />
        ) : (
          <Circle className="w-5 h-5 text-gray-300" />
        )}
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold">{title}</div>
        <div className="text-xs text-gray-500 mt-1">{desc}</div>
        {action}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading setup wizard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6 md:p-10">
      <div className="text-sm text-gray-500 mb-1">
        <a href="/" className="hover:text-black">Dashboard</a>
        <span className="mx-1.5 text-gray-300">/</span>
        <span>Setup Wizard</span>
      </div>

      <div className="flex items-center gap-3 mb-6">
        <Zap className="w-6 h-6 text-yellow-500" />
        <h1 className="text-3xl md:text-4xl font-bold">Streamer Setup Wizard</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Step
            done={isConnected("twitch") || isConnected("youtube")}
            title="Connect Twitch or YouTube"
            desc="Link your platforms so Kazumi can ingest chat and events."
            action={
              <div className="mt-3 flex gap-2">
                <a href="/settings" className="px-3 py-2 text-xs border border-gray-300 rounded-md">
                  Open Integrations
                </a>
              </div>
            }
          />

          <Step
            done={metadataReady}
            title="Add Platform Metadata (IDs only)"
            desc="Set Twitch broadcaster/moderator IDs + webhook and YouTube live_chat_id in Settings."
            action={
              <div className="mt-3 text-xs text-gray-500 space-y-1">
                <div>Twitch metadata: {hasTwitchMetadata ? "Ready" : "Missing broadcaster_id"}</div>
                <div>YouTube metadata: {hasYoutubeMetadata ? "Ready" : "Missing live_chat_id"}</div>
              </div>
            }
          />

          <Step
            done={obsStatus?.connected}
            title="Verify OBS Connection"
            desc="Kazumi needs OBS WebSocket to control scenes and clips."
            action={
              <div className="mt-3 text-xs text-gray-500">
                OBS status: {obsStatus?.connected ? "Connected" : "Not connected"}
              </div>
            }
          />

          <Step
            done={false}
            title="Start Local Agent"
            desc="Run the agent to execute commands instantly on your machine."
            action={
              <div className="mt-3 text-xs text-gray-500">
                Run: <span className="font-mono">python scripts/local_agent.py</span>
              </div>
            }
          />
        </div>

        <div className="space-y-4">
          <div className="border border-emerald-200 bg-emerald-50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-4 h-4 text-emerald-700" />
              <h2 className="text-sm font-bold text-emerald-900">Security Model</h2>
            </div>
            <ul className="text-xs text-emerald-900 space-y-1 list-disc pl-4">
              <li>No streamer passwords are requested anywhere.</li>
              <li>Kazumi uses OAuth tokens only, scoped to streaming/moderation actions.</li>
              <li>Streamers paste IDs and webhook URLs, not account credentials.</li>
            </ul>
          </div>

          <div className="border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Server className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-bold">System Checks</h2>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span>Backend</span>
                <span className="text-gray-600">{health?.status || "unknown"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Database</span>
                <span className="text-gray-600">{health?.checks?.database ? "ok" : "offline"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>OBS</span>
                <span className="text-gray-600">{health?.checks?.obs ? "ok" : "offline"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>OAuth</span>
                <span className="text-gray-600">{isConnected("twitch") || isConnected("youtube") ? "connected" : "pending"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Metadata</span>
                <span className="text-gray-600">{metadataReady ? "ready" : "pending"}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 text-xs text-gray-500">
        Need help? Go to <a href="/settings" className="underline">Settings</a> for keys and integrations.
      </div>
    </div>
  );
}

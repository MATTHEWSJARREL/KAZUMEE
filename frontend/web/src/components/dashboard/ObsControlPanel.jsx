"use client";

import { useEffect, useState } from "react";
import { Camera, Video, BarChart2 } from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/apiClient";
import ObsStatus from "../ObsStatus";

export default function ObsControlPanel({ userRole, obsState, activeStreamerId }) {
  const [obsSources, setObsSources] = useState([]);
  const [obsCameras, setObsCameras] = useState([]);
  const [sourcePanelLoading, setSourcePanelLoading] = useState(false);
  const [sourceActionBusy, setSourceActionBusy] = useState({});

  const setSourceBusy = (key, busy) => {
    setSourceActionBusy((prev) => {
      const next = { ...prev };
      if (busy) next[key] = true;
      else delete next[key];
      return next;
    });
  };

  const fetchObsSourcesAndCameras = async ({ silent = false } = {}) => {
    if (userRole !== "streamer") return;
    try {
      if (!silent) setSourcePanelLoading(true);
      const [sourceRes, cameraRes] = await Promise.all([apiFetch("/obs/sources"), apiFetch("/obs/cameras")]);
      const sourceData = await sourceRes.json().catch(() => ({}));
      const cameraData = await cameraRes.json().catch(() => ({}));
      if (sourceRes.ok) {
        setObsSources(Array.isArray(sourceData.sources) ? sourceData.sources : []);
      }
      if (cameraRes.ok) {
        setObsCameras(Array.isArray(cameraData.cameras) ? cameraData.cameras : []);
      }
    } catch (error) {
      if (!silent) {
        console.error("Failed to fetch OBS source panel:", error);
      }
    } finally {
      if (!silent) setSourcePanelLoading(false);
    }
  };

  useEffect(() => {
    if (userRole !== "streamer") return;
    void fetchObsSourcesAndCameras();
    const interval = window.setInterval(() => {
      void fetchObsSourcesAndCameras({ silent: true });
    }, 5000);
    return () => window.clearInterval(interval);
  }, [userRole, activeStreamerId]);

  const setSourceVisibility = async (sourceName, visible) => {
    if (!window.confirm(`${visible ? "Show" : "Hide"} OBS source "${sourceName}" now?`)) return;
    const key = `visibility:${sourceName}`;
    try {
      setSourceBusy(key, true);
      const response = await apiFetch("/obs/sources/visibility", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_name: sourceName, visible }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Could not update source visibility");
      }
      setObsSources((prev) =>
        prev.map((source) => (source.source_name === sourceName ? { ...source, visible: Boolean(payload.visible) } : source)),
      );
      toast.success(`${sourceName} ${visible ? "shown" : "hidden"}`);
      void fetchObsSourcesAndCameras({ silent: true });
    } catch (error) {
      toast.error("Source update failed", {
        description: error?.message || "Could not update source visibility.",
      });
    } finally {
      setSourceBusy(key, false);
    }
  };

  const switchSourceDevice = async (sourceName, deviceId) => {
    if (!deviceId) return;
    const cameraLabel = obsCameras.find((camera) => camera.device_id === deviceId)?.label || deviceId;
    if (!window.confirm(`Switch "${sourceName}" to camera "${cameraLabel}" now?`)) return;
    const key = `device:${sourceName}`;
    try {
      setSourceBusy(key, true);
      const response = await apiFetch("/obs/sources/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_name: sourceName,
          device_id: deviceId,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Could not switch camera");
      }
      setObsSources((prev) =>
        prev.map((source) => (source.source_name === sourceName ? { ...source, device_id: deviceId } : source)),
      );
      toast.success(`${sourceName} switched`);
      void fetchObsSourcesAndCameras({ silent: true });
    } catch (error) {
      toast.error("Camera switch failed", {
        description: error?.message || "Could not switch camera device.",
      });
    } finally {
      setSourceBusy(key, false);
    }
  };

  return (
    <>
      <div className="kazumi-card p-6 mb-8">
        <ObsStatus state={obsState} />
      </div>

      {userRole === "streamer" && (
        <div className="kazumi-card p-6 mb-8">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div>
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">OBS Control</div>
              <h2 className="text-lg font-bold">Sources & Cameras</h2>
            </div>
            <button
              onClick={() => void fetchObsSourcesAndCameras()}
              className="px-3 py-1.5 text-xs rounded-md border border-black/10 hover:bg-black/5"
            >
              Refresh
            </button>
          </div>

          {sourcePanelLoading ? (
            <div className="text-xs text-gray-500">Loading sources...</div>
          ) : obsSources.length === 0 ? (
            <div className="text-xs text-gray-500">No sources found for the active scene.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {obsSources.map((source) => {
                const busyVisibility = Boolean(sourceActionBusy[`visibility:${source.source_name}`]);
                const busyDevice = Boolean(sourceActionBusy[`device:${source.source_name}`]);
                return (
                  <div key={`${source.scene_item_id}-${source.source_name}`} className="rounded-xl border border-black/10 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          {source.is_camera ? <Camera className="w-4 h-4" /> : <Video className="w-4 h-4" />}
                          <div className="text-sm font-semibold truncate">{source.source_name}</div>
                        </div>
                        <div className="text-[11px] text-gray-500 mt-1">{source.source_type || "source"}</div>
                      </div>
                      <label className="inline-flex items-center gap-2 text-xs">
                        <span className="text-gray-500">{source.visible ? "Visible" : "Hidden"}</span>
                        <input
                          type="checkbox"
                          checked={Boolean(source.visible)}
                          disabled={busyVisibility}
                          onChange={(event) => setSourceVisibility(source.source_name, event.target.checked)}
                          className="accent-black"
                        />
                      </label>
                    </div>
                    {source.is_camera && (
                      <div className="mt-3">
                        <select
                          value={source.device_id || ""}
                          disabled={busyDevice || obsCameras.length === 0}
                          onChange={(event) => void switchSourceDevice(source.source_name, event.target.value)}
                          className="w-full border border-black/10 rounded-md px-2 py-1 text-xs bg-white"
                        >
                          <option value="">Select camera device</option>
                          {obsCameras.map((camera) => (
                            <option key={camera.device_id} value={camera.device_id}>
                              {camera.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div className="kazumi-card p-6 mb-8">
        <div className="flex items-center gap-6 mb-6">
          <div className="w-[52px] h-[52px] border border-black/10 rounded-2xl flex items-center justify-center flex-shrink-0 bg-white">
            <BarChart2 className="w-6 h-6" strokeWidth={1.5} />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">Current Scene</div>
            <div className="text-[28px] font-semibold leading-none">{obsState?.scene || "Unknown"}</div>
          </div>
        </div>

        <div className="h-56 w-full mb-4">
          <svg className="w-full h-full" viewBox="0 0 800 200">
            <path d="M 50 120 L 150 100 L 250 80 L 350 90 L 450 70 L 550 85 L 650 60 L 750 75" stroke="#000000" strokeWidth="2" fill="none" />
            <circle cx="750" cy="75" r="4" fill="#000000" />
          </svg>
        </div>
      </div>
    </>
  );
}

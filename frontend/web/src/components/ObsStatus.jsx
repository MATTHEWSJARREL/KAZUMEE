import React from "react";
import { CircleDot, Radio, Video } from "lucide-react";

/**
 * ObsStatus - Pure Renderer
 * It does not fetch data. It only renders the 'state' passed from parent.
 */
export default function ObsStatus({ state }) {
  if (!state) {
    return (
      <div className="flex items-center gap-2 text-gray-500 text-sm">
        <div className="w-2 h-2 bg-gray-300 rounded-full animate-pulse" />
        Checking OBS...
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-3 text-sm items-center">
      <span
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
          state.connected ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
        }`}
      >
        <CircleDot className="w-3.5 h-3.5" />
        OBS {state.connected ? "Connected" : "Disconnected"}
      </span>
      {!state.connected && (
        <span className="text-xs text-red-600">
          Check OBS WebSocket settings and restart OBS if needed.
        </span>
      )}
      <span
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
          state.streaming ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-600"
        }`}
      >
        <Radio className="w-3.5 h-3.5" />
        Streaming {state.streaming ? "Live" : "Off"}
      </span>
      <span
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
          state.recording ? "bg-rose-100 text-rose-700" : "bg-gray-100 text-gray-600"
        }`}
      >
        <Video className="w-3.5 h-3.5" />
        Recording {state.recording ? "On" : "Off"}
      </span>
      <span className="text-xs text-gray-600">
        Scene
        <span className="mx-1 text-gray-300">/</span>
        <span className="font-semibold text-gray-900">{state.scene || "Unknown"}</span>
      </span>
    </div>
  );
}

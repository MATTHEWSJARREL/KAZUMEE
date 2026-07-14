"use client";

import { useMemo, useState } from "react";
import { Activity } from "lucide-react";

export default function LiveEventsPanel({
  liveEvents,
  eventStreamStatus,
  eventPaused,
  setEventPaused,
}) {
  const [eventPlatformFilter, setEventPlatformFilter] = useState("all");
  const [eventTypeFilter, setEventTypeFilter] = useState("all");
  const eventTypes = useMemo(() => Array.from(new Set(liveEvents.map((event) => event.event_type))).filter(Boolean), [liveEvents]);
  const filteredEvents = useMemo(
    () =>
      liveEvents.filter((event) => {
        if (eventPlatformFilter !== "all" && event.platform !== eventPlatformFilter) return false;
        if (eventTypeFilter !== "all" && event.event_type !== eventTypeFilter) return false;
        return true;
      }),
    [liveEvents, eventPlatformFilter, eventTypeFilter],
  );

  return (
    <div className="kazumi-card p-6 mb-8">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5" />
          <h2 className="text-lg font-bold">Live Event Feed</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
          <select
            value={eventPlatformFilter}
            onChange={(event) => setEventPlatformFilter(event.target.value)}
            className="border border-black/10 rounded-md px-2 py-1 text-xs bg-white"
          >
            <option value="all">All platforms</option>
            <option value="twitch">Twitch</option>
            <option value="youtube">YouTube</option>
          </select>
          <select
            value={eventTypeFilter}
            onChange={(event) => setEventTypeFilter(event.target.value)}
            className="border border-black/10 rounded-md px-2 py-1 text-xs bg-white"
          >
            <option value="all">All types</option>
            {eventTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          <button
            onClick={() => setEventPaused((value) => !value)}
            className="border border-black/10 rounded-md px-2 py-1 text-xs bg-white"
          >
            {eventPaused ? "Resume" : "Pause"}
          </button>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span
              className={`w-2 h-2 rounded-full ${
                eventStreamStatus === "live" ? "bg-green-500" : eventStreamStatus === "connecting" ? "bg-yellow-500" : "bg-red-500"
              }`}
            />
            <span className="uppercase tracking-widest">{eventStreamStatus}</span>
          </div>
        </div>
      </div>

      {filteredEvents.length === 0 ? (
        <div className="text-sm text-gray-500">No live events yet.</div>
      ) : (
        <div className="space-y-3">
          {filteredEvents.slice(0, 6).map((event) => (
            <div key={event.id} className="flex items-start justify-between gap-4 border-b border-black/5 pb-3">
              <div>
                <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">
                  {event.platform} - {event.event_type}
                </div>
                <div className="text-sm font-medium">{event.username || "Anonymous"}</div>
                {event.message && <div className="text-xs text-gray-600 mt-1">{event.message}</div>}
              </div>
              <div className="text-[10px] text-gray-400 whitespace-nowrap">
                {event.received_at ? new Date(event.received_at).toLocaleTimeString() : ""}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

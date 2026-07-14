"use client";

import { useMemo, useState } from "react";
import { Clock } from "lucide-react";

export default function ActivityFeedPanel({ recentActivity }) {
  const [showFullFeed, setShowFullFeed] = useState(false);
  const compactRecentActivity = useMemo(() => {
    const seen = new Map();
    for (const item of recentActivity) {
      const key = [item?.action_type || item?.type || "watching", item?.description || "", item?.commentary || "", item?.action_label || ""]
        .join("|")
        .toLowerCase();
      if (seen.has(key)) {
        const existing = seen.get(key);
        existing.count += 1;
        continue;
      }
      seen.set(key, { ...item, count: 1 });
    }
    return Array.from(seen.values());
  }, [recentActivity]);
  const visibleRecentActivity = showFullFeed ? compactRecentActivity.slice(0, 20) : compactRecentActivity.slice(0, 5);

  const handleFeedAction = (item) => {
    const href = item?.action_href;
    if (href) {
      window.location.href = href;
      return;
    }
    if (item?.type?.includes("moderation")) {
      window.location.href = "/moderation";
      return;
    }
    window.location.href = "/commands";
  };

  return (
    <div className="kazumi-card p-5">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <Clock className="w-5 h-5" />
          <h2 className="text-lg font-bold">Kazumi Feed</h2>
        </div>
        {compactRecentActivity.length > 5 && (
          <button
            onClick={() => setShowFullFeed((value) => !value)}
            className="text-xs font-semibold px-3 py-1.5 rounded-md border border-white/10 bg-white/5 hover:bg-white/10"
          >
            {showFullFeed ? "Show less" : `Show ${Math.min(compactRecentActivity.length, 20)}`}
          </button>
        )}
      </div>

      <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
        {compactRecentActivity.length === 0 ? (
          <div className="text-sm text-gray-500">No recent activity yet.</div>
        ) : (
          visibleRecentActivity.map((activity, index) => {
            const actionType = activity?.action_type || "watching";
            const style =
              actionType === "handled"
                ? { dot: "#00E5A0", badge: "bg-[rgba(0,229,160,0.1)] text-[#00A36F]", label: "Handled", card: "bg-[rgba(0,229,160,0.06)]" }
                : actionType === "needs_you"
                  ? { dot: "#F5A623", badge: "bg-[rgba(245,166,35,0.12)] text-[#C97B0A]", label: "Needs you", card: "bg-[rgba(245,166,35,0.08)]" }
                  : { dot: "#4C9FFF", badge: "bg-[rgba(76,159,255,0.12)] text-[#2B79D5]", label: "Watching", card: "bg-[rgba(76,159,255,0.07)]" };

            return (
              <div key={index} className={`${style.card} rounded-xl px-3 py-2.5 flex items-start gap-3 border border-white/10`}>
                <div className={`w-2.5 h-2.5 rounded-full mt-1.5 ${actionType === "needs_you" ? "animate-pulse" : ""}`} style={{ backgroundColor: style.dot }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full ${style.badge}`}>{style.label}</span>
                    <span className="text-[10px] text-gray-400">{activity.time}</span>
                    {activity.count > 1 && <span className="text-[10px] text-gray-500">x{activity.count}</span>}
                  </div>
                  <p className="text-sm text-gray-800">{activity.description}</p>
                  {activity.commentary && <p className="text-xs text-gray-600 mt-1 line-clamp-2">{activity.commentary}</p>}
                  {actionType === "needs_you" && (
                    <button onClick={() => handleFeedAction(activity)} className="mt-2 text-xs font-semibold text-[#7C5CFC] underline underline-offset-2">
                      {activity.action_label || "Review"} {"->"}
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

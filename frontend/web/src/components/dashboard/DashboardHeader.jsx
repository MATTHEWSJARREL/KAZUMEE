"use client";

import { useAvatar } from "../../lib/avatar/useAvatar";
import KazumiAvatar from "../avatar/KazumiAvatar";

export default function DashboardHeader({
  title = "Main Dashboard",
  demoMode = false,
  actions = null,
  statusLabel = "",
}) {
  const { avatarState } = useAvatar();

  return (
    <div className="mb-8">
      <div className="text-sm text-gray-500 mb-1">
        <span>Pages</span>
        <span className="mx-1.5 text-gray-300">/</span>
        <span>{title}</span>
      </div>

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <KazumiAvatar state={avatarState} size={56} showSpeechVisualizer={false} className="shrink-0" />
          <h1 className="text-3xl md:text-4xl font-bold leading-tight">{title}</h1>
          {demoMode && (
            <span className="px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest bg-yellow-100 text-yellow-700">
              Demo Mode
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {statusLabel && (
            <div className="px-4 py-2 rounded-full border border-gray-200 text-xs font-semibold uppercase tracking-widest text-gray-600">
              {statusLabel}
            </div>
          )}
          {actions}
        </div>
      </div>
    </div>
  );
}

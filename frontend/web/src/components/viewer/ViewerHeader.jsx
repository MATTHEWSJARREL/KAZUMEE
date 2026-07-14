"use client";

import { useAvatar } from "../../lib/avatar/useAvatar";
import KazumiAvatar from "../avatar/KazumiAvatar";

export default function ViewerHeader({ streamerDisplayName, currentTitle, capabilityState }) {
  const { avatarState } = useAvatar();

  return (
    <section className="viewer-glass-card viewer-now-card">
      <div className="flex items-center gap-3 mb-3">
        <KazumiAvatar state={avatarState} size={48} showSpeechVisualizer={false} className="shrink-0" />
        <span className="viewer-eyebrow">Now Watching</span>
      </div>
      <h1>{streamerDisplayName}</h1>
      <p>{currentTitle}</p>
      <div className="viewer-now-actions">
        <button type="button" className="viewer-connected-button">
          {capabilityState}
        </button>
      </div>
    </section>
  );
}

"use client";

import { getAvatarStateMeta } from "./AvatarStateMachine";

export default function AvatarSpeechVisualizer({ state = "idle", bars = 5 }) {
  const meta = getAvatarStateMeta(state);
  const count = Math.max(3, bars);
  return (
    <div className={`avatar-speech-visualizer avatar-speech-visualizer--${meta.state}`} aria-hidden="true">
      {Array.from({ length: count }).map((_, index) => (
        <span
          key={index}
          className="avatar-speech-visualizer__bar"
          style={{ animationDelay: `${index * 90}ms` }}
        />
      ))}
    </div>
  );
}


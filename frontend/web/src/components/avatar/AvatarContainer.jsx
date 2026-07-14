"use client";

import AvatarStatusRing from "./AvatarStatusRing";
import AvatarSpeechVisualizer from "./AvatarSpeechVisualizer";
import { getAvatarStateMeta, normalizeAvatarState } from "./AvatarStateMachine";
import "./avatar.css";

export default function AvatarContainer({
  state = "idle",
  children,
  size = 220,
  className = "",
  showSpeechVisualizer = true,
}) {
  const normalized = normalizeAvatarState(state);
  const meta = getAvatarStateMeta(normalized);

  return (
    <div className={`avatar-shell avatar-shell--${meta.state} ${className}`.trim()}>
      <AvatarStatusRing state={normalized} size={size} />
      <div className="avatar-shell__core">
        <div className="avatar-shell__halo" />
        <div className="avatar-shell__face">
          <div className="avatar-shell__eyes">
            <span />
            <span />
          </div>
          <div className="avatar-shell__visor" />
        </div>
        <div className="avatar-shell__status">
          <span className="avatar-shell__label">{meta.label}</span>
          <span className="avatar-shell__subtitle">{meta.subtitle}</span>
        </div>
        {showSpeechVisualizer && <AvatarSpeechVisualizer state={normalized} />}
        {children}
      </div>
    </div>
  );
}


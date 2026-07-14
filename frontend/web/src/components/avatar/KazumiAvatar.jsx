"use client";

import AvatarContainer from "./AvatarContainer";
import { getAvatarStateMeta, normalizeAvatarState } from "./AvatarStateMachine";

export default function KazumiAvatar({
  state = "idle",
  label = "",
  subtitle = "",
  size = 220,
  className = "",
  showSpeechVisualizer = true,
}) {
  const normalized = normalizeAvatarState(state);
  const meta = getAvatarStateMeta(normalized);

  return (
    <AvatarContainer state={normalized} size={size} className={className} showSpeechVisualizer={showSpeechVisualizer}>
      {(label || subtitle) && (
        <div className="avatar-shell__copy">
          {label && <span className="avatar-shell__label">{label}</span>}
          {subtitle && <span className="avatar-shell__subtitle">{subtitle}</span>}
        </div>
      )}
      {!label && !subtitle && (
        <div className="avatar-shell__copy">
          <span className="avatar-shell__label">Kazumi</span>
          <span className="avatar-shell__subtitle">{meta.subtitle}</span>
        </div>
      )}
    </AvatarContainer>
  );
}


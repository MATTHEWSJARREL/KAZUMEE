"use client";

import { getAvatarStateMeta } from "./AvatarStateMachine";

export default function AvatarStatusRing({ state = "idle", size = 220 }) {
  const meta = getAvatarStateMeta(state);
  return (
    <div
      className={`avatar-status-ring avatar-status-ring--${meta.state}`}
      style={{ "--avatar-size": `${size}px` }}
      aria-hidden="true"
    >
      <span className="avatar-status-ring__orb avatar-status-ring__orb--outer" />
      <span className="avatar-status-ring__orb avatar-status-ring__orb--middle" />
      <span className="avatar-status-ring__orb avatar-status-ring__orb--inner" />
      <span className="avatar-status-ring__scan" />
    </div>
  );
}


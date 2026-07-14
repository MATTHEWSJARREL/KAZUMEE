"use client";

export default function ViewerShell({ sidebar, main, aside, nudge, toasts, modal, className = "" }) {
  return (
    <div className={`viewer-redesign-v2 ${className}`}>
      {sidebar}
      {main}
      {aside}
      {nudge}
      {toasts}
      {modal}
    </div>
  );
}

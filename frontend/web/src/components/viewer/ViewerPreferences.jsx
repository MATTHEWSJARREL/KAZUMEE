"use client";

export default function ViewerPreferences({ viewerData, viewerCredits, shieldLabel, streamStatusLabel, viewerCooldown }) {
  return (
    <section className="viewer-glass-card viewer-status-card">
      <h2>Credits & Status</h2>
      <dl>
        <div>
          <dt>Credits</dt>
          <dd>{viewerCredits}</dd>
        </div>
        <div>
          <dt>Shield</dt>
          <dd>{shieldLabel}</dd>
        </div>
        <div>
          <dt>Stream</dt>
          <dd>{streamStatusLabel}</dd>
        </div>
        <div>
          <dt>Cooldown</dt>
          <dd>{viewerCooldown}s</dd>
        </div>
      </dl>
    </section>
  );
}

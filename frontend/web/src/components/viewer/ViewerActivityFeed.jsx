"use client";

export default function ViewerActivityFeed({ groups, onToggleImportant, importantOnly, hiddenCount, showHiddenEvents, hiddenEvents }) {
  return (
    <section className="viewer-glass-card viewer-feed-panel">
      <div className="viewer-section-title-row compact">
        <div>
          <span className="viewer-eyebrow">Live Event Feed</span>
          <h2>Grouped events</h2>
        </div>
      </div>
      {groups}
      {showHiddenEvents && hiddenEvents}
    </section>
  );
}

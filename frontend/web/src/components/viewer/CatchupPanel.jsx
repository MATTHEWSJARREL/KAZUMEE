"use client";

export default function CatchupPanel({ title, recap, clips, onQuick, onFull, onClips, freshness, topics, dominantPlatform, onShare }) {
  return (
    <section className="viewer-glass-card viewer-recap-panel">
      <div className="viewer-recap-head">
        <img src="/logo.png" alt="Zumi" className="viewer-zumi-avatar" />
        <div>
          <span className="viewer-eyebrow">Catch-Up Recap</span>
          <h2>{title}</h2>
        </div>
      </div>
      <div className="viewer-tab-row">
        <button type="button" className="viewer-tab-button active" onClick={onQuick}>Quick</button>
        <button type="button" className="viewer-tab-button" onClick={onFull}>Full</button>
        <button type="button" className="viewer-tab-button" onClick={onClips}>Clips</button>
      </div>
      <div className="viewer-recap-box">
        <p>{recap}</p>
        {clips}
        {freshness && <small>{freshness}</small>}
        {topics?.length > 0 && <small>Topics: {topics.join(", ")}</small>}
        {dominantPlatform && <small>Main platform: {dominantPlatform}</small>}
      </div>
      <button type="button" className="viewer-secondary-button viewer-share-button" onClick={onShare}>Share recap</button>
    </section>
  );
}

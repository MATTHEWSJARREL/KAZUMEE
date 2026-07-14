"use client";

import { Heart, Timer, Vote } from "lucide-react";

export default function VotingPanel({ impactMessage, voteDelay, latencyMs, voteCounts, onVote }) {
  return (
    <section className="viewer-glass-card viewer-vote-card">
      <div className="viewer-card-heading">
        <Vote className="viewer-icon" />
        <h2>Scene Voting</h2>
      </div>
      {impactMessage && <p className="viewer-mini-note">{impactMessage}</p>}
      {voteDelay > 0 && (
        <p className="viewer-delay-note">
          <Timer className="viewer-tiny-icon" /> Results update in {voteDelay}s
        </p>
      )}
      <div className="viewer-scene-list">
        {["Gameplay Camera", "Reaction Cam", "Full Screen", "Chat Overlay"].map((scene) => (
          <button key={scene} type="button" onClick={() => onVote(scene)} className="viewer-scene-button">
            <span>{scene}</span>
            <small>
              {voteCounts[scene] || 0} votes <Heart className="viewer-heart" />
            </small>
          </button>
        ))}
      </div>
    </section>
  );
}

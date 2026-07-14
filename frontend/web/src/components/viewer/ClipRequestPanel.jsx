"use client";

import { MessageSquare, Send } from "lucide-react";

export default function ClipRequestPanel({ commandText, onCommandText, onSubmit, cooldown, shieldLabel }) {
  return (
    <section className="viewer-glass-card viewer-command-panel">
      <div className="viewer-card-heading">
        <MessageSquare className="viewer-icon" />
        <h2>Submit Command</h2>
      </div>
      {shieldLabel && <p className="viewer-mini-note">{shieldLabel}</p>}
      <textarea value={commandText} onChange={(e) => onCommandText(e.target.value)} className="viewer-textarea" rows={3} />
      <button type="button" onClick={onSubmit} disabled={cooldown > 0} className="viewer-primary-button viewer-full-button">
        <Send className="viewer-tiny-icon" />{cooldown > 0 ? `Wait ${cooldown}s` : "Submit Command"}
      </button>
    </section>
  );
}

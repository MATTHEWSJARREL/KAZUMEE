"use client";

export default function CompanionPanel({ suggestions, input, onInput, onAsk, loading, result, trackers, onCopy, onMarkSent, onRetry, onAnswered }) {
  return (
    <section id="viewer-ask-zumi" className="viewer-glass-card viewer-ask-panel">
      <div className="viewer-section-title-row compact">
        <div>
          <span className="viewer-eyebrow">Ask Zumi</span>
          <h2>Stream context</h2>
        </div>
      </div>
      <div className="viewer-question-pills">
        {suggestions?.slice(0, 3).map((suggestion, index) => (
          <button key={index} type="button" onClick={() => onInput(suggestion)}>{suggestion}</button>
        ))}
      </div>
      <textarea value={input} onChange={(e) => onInput(e.target.value)} className="viewer-textarea" rows={3} />
      <button type="button" className="viewer-primary-button viewer-full-button" onClick={onAsk} disabled={loading}>
        {loading ? "Thinking" : "Ask"}
      </button>
      {result && (
        <div className="viewer-answer-box">
          <span>Answer</span>
          <p>{result.improved_message}</p>
          <div className="viewer-answer-metrics">
            <small>Timing {result.timing_score}</small>
            <small>Notice {result.notice_score}</small>
            <small>Dupes {result.duplicate_count_recent}</small>
          </div>
          <div className="viewer-answer-actions">
            <button type="button" onClick={onCopy}>Copy</button>
            <button type="button" onClick={onMarkSent}>I Sent It</button>
          </div>
        </div>
      )}
      {trackers?.length > 0 && (
        <div className="viewer-tracker-list">{trackers}</div>
      )}
    </section>
  );
}

"use client";

export default function PostStreamReportPanel({ postStreamReport }) {
  if (!postStreamReport) return null;

  return (
    <div className="kazumi-card p-4 mb-8 border border-green-200 bg-green-50/60">
      <div className="text-xs uppercase tracking-widest text-green-700 mb-1">Post-Stream Report</div>
      <div className="text-sm text-green-900">{postStreamReport.summary || "Report generated successfully."}</div>
    </div>
  );
}

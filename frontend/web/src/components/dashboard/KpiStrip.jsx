"use client";

import { Activity, CheckCircle, Eye, Scissors, Shield, TrendingUp } from "lucide-react";

export default function KpiStrip({
  dashboardData,
  preStreamChecklist,
  userRole,
  isStreaming,
  onFixChecklist,
  streamPulse,
}) {
  const kpiCards = [
    {
      label: "Current Viewers",
      value: dashboardData?.currentViewers || "0",
      delta: dashboardData?.viewerChange || "+0%",
      icon: Eye,
      color: "text-blue-600",
    },
    {
      label: "Stream Health",
      value: dashboardData?.healthStatus || "Healthy",
      delta: `${dashboardData?.healthScore || 0}% score`,
      icon: Activity,
      color: "text-green-600",
    },
    {
      label: "Auto Clips Today",
      value: dashboardData?.autoClips || "0",
      delta: `${dashboardData?.manualClips || 0} manual`,
      icon: Scissors,
      color: "text-purple-600",
    },
    {
      label: "Mod Events",
      value: dashboardData?.modEvents || "0",
      delta: `${dashboardData?.autoModerated || 0}% auto`,
      icon: Shield,
      color: "text-orange-600",
    },
    {
      label: "Stream Pulse",
      value: String(dashboardData?.streamPulse?.score ?? 0),
      delta: `${(dashboardData?.streamPulse?.trend ?? 0) >= 0 ? "+" : ""}${dashboardData?.streamPulse?.trend ?? 0} trend`,
      icon: TrendingUp,
      color: "text-indigo-600",
    },
  ];

  return (
    <>
      {userRole === "streamer" && !isStreaming && (
        <div className="kazumi-card p-5 mb-8 border-l-4 border-black">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-sm">Pre-stream Checklist</h3>
            {preStreamChecklist?.ready && (
              <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded-full">
                Ready to go live
              </span>
            )}
          </div>
          <div className="space-y-2">
            {(preStreamChecklist?.checks || []).map((check) => (
              <div key={check.id} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-4 h-4 rounded-full flex items-center justify-center ${
                      check.passed ? "bg-green-500" : "bg-red-100 border border-red-300"
                    }`}
                  >
                    {check.passed ? <CheckCircle className="w-3 h-3 text-white" /> : null}
                  </div>
                  <span className={`text-sm ${check.passed ? "text-gray-600" : "text-gray-900 font-medium"}`}>
                    {check.label}
                  </span>
                </div>
                {!check.passed && (
                  <button
                    onClick={() => onFixChecklist(check)}
                    className="text-xs font-semibold text-black underline underline-offset-2"
                  >
                    {check.fix_label || "Fix"}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {kpiCards.map((card, index) => {
          const IconComponent = card.icon;
          return (
            <div key={index} className="kazumi-card p-6 flex items-center gap-4">
              <div className={`w-[52px] h-[52px] border border-black/10 rounded-2xl flex items-center justify-center flex-shrink-0 bg-white ${card.color}`}>
                <IconComponent className="w-6 h-6" strokeWidth={1.5} />
              </div>
              <div className="min-w-0">
                <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">{card.label}</div>
                <div className="text-[28px] font-semibold leading-none mb-1">{card.value}</div>
                <div className="text-xs text-[#16A34A]">{card.delta}</div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

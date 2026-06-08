"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/apiClient";
import {
  TrendingUp,
  Users,
  Eye,
  MessageSquare,
  Clock,
  Calendar,
  ArrowUp,
  ArrowDown,
  BarChart2,
  PieChart,
  Activity,
  Sparkles,
  Zap,
  Loader2
} from "lucide-react";

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState("7d");
  const [health, setHealth] = useState(null);
  const [streamHealth, setStreamHealth] = useState(null);
  const [recentEvents, setRecentEvents] = useState([]);
  
  // New AI Insight States
  const [aiSummary, setAiSummary] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    fetchAnalytics();
    fetchHealth();
    fetchRecentEvents();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const response = await apiFetch(`/api/analytics?range=${timeRange}`);
      if (!response.ok) throw new Error("Failed to fetch analytics");
      const data = await response.json();
      setAnalytics(data);
      
      // Generate AI Insights once data is loaded
      generateAiInsights(data);
    } catch (error) {
      console.error("Error fetching analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await apiFetch("/api/health");
      if (res.ok) setHealth(await res.json());
    } catch {}
    try {
      const res = await apiFetch("/api/stream-health");
      if (res.ok) setStreamHealth(await res.json());
    } catch {}
  };

  const fetchRecentEvents = async () => {
    try {
      const res = await apiFetch("/api/events/recent?limit=40");
      if (!res.ok) return;
      const data = await res.json();
      setRecentEvents(data.events || []);
    } catch {}
  };

  const generateAiInsights = async (data) => {
    setIsAnalyzing(true);
    try {
      // We send the raw numbers to our Brain endpoint for a summary
      const response = await apiFetch("/api/commands/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          command: `Analyze these stream stats for the last ${timeRange}: Avg Viewers ${data.avgViewers}, Peak ${data.peakViewers}, Total Messages ${data.totalMessages}. Give me a 2-sentence strategy.`,
          role: "streamer",
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result?.detail || result?.message || `Error (${response.status})`);
      }
      setAiSummary(result.message || "No insights available.");
    } catch (err) {
      console.error("AI insights error:", err);
      setAiSummary("Kazumi Brain is offline. Check your backend connection.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const metrics = [
    { label: "Avg Viewers", value: analytics?.avgViewers || 0, change: analytics?.viewerChange || 0, icon: Eye, color: "text-blue-600", bgColor: "bg-blue-100" },
    { label: "Peak Viewers", value: analytics?.peakViewers || 0, change: analytics?.peakChange || 0, icon: TrendingUp, color: "text-green-600", bgColor: "bg-green-100" },
    { label: "Total Messages", value: analytics?.totalMessages || 0, change: analytics?.messageChange || 0, icon: MessageSquare, color: "text-purple-600", bgColor: "bg-purple-100" },
    { label: "Stream Hours", value: analytics?.streamHours || 0, change: analytics?.hoursChange || 0, icon: Clock, color: "text-orange-600", bgColor: "bg-orange-100" },
  ];
  const opsMetrics = [
    { label: "Pending Approvals", value: analytics?.commands?.pending || 0 },
    { label: "Approval Rate", value: `${analytics?.approvalRate || 0}%` },
    { label: "Clips Pending", value: analytics?.clips?.pending || 0 },
    { label: "Clips Approved", value: analytics?.clips?.approved || 0 },
  ];
  const platformRows = Object.entries(analytics?.eventsByPlatform || {});
  const tasteTags = analytics?.tasteTags || [];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Syncing with Kazumi's memory...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 md:p-10">
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500 mb-1">
        <a href="/" className="hover:text-black">Dashboard</a>
        <span className="mx-1.5 text-gray-300">/</span>
        <span>Analytics</span>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 gap-4">
        <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-2">
          Insights Console <Zap className="text-yellow-500 fill-yellow-500 w-6 h-6" />
        </h1>
        <div className="flex bg-black/5 p-1 rounded-lg">
          {["24h", "7d", "30d", "90d"].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-1.5 rounded-md text-sm font-semibold transition-all ${
                timeRange === range ? "bg-black text-white shadow-sm" : "text-gray-500 hover:text-black"
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* --- NEW: AI STRATEGY CARD --- */}
      <div className="mb-8 p-6 rounded-2xl bg-gradient-to-r from-indigo-900 via-purple-900 to-black text-white shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4 opacity-10">
          <Sparkles className="w-32 h-32" />
        </div>
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-3">
            <div className="px-2 py-0.5 bg-yellow-400 text-black text-[10px] font-black rounded uppercase">AI Director Report</div>
          </div>
          <h2 className="text-xl font-bold mb-2">Kazumi's Growth Strategy</h2>
          {isAnalyzing ? (
            <div className="flex items-center gap-3 text-purple-200">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Crunching viewer behavior patterns...</span>
            </div>
          ) : (
            <p className="text-purple-100 text-lg leading-relaxed max-w-3xl">
              "{aiSummary || "No insights available for this time range yet."}"
            </p>
          )}
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metrics.map((metric, index) => {
          const IconComponent = metric.icon;
          const isPositive = metric.change >= 0;
          return (
            <div key={index} className="kazumi-card p-6">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 ${metric.bgColor} rounded-xl flex items-center justify-center`}>
                  <IconComponent className={`w-6 h-6 ${metric.color}`} />
                </div>
                <div className={`flex items-center gap-1 text-sm font-bold ${isPositive ? "text-green-600" : "text-red-600"}`}>
                  {isPositive ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                  {Math.abs(metric.change)}%
                </div>
              </div>
              <div className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-1">{metric.label}</div>
              <div className="text-3xl font-black">{metric.value.toLocaleString()}</div>
            </div>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="kazumi-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-blue-500" /> Viewer Retention
            </h2>
          </div>
          <div className="h-64 flex items-end justify-around gap-2 px-2">
            {(analytics?.viewerGrowth || []).map((value, index) => (
              <div key={index} className="flex-1 flex flex-col items-center group">
                <div 
                  className="w-full bg-gray-100 group-hover:bg-black rounded-t-lg transition-all duration-500 relative"
                  style={{ height: `${(value / Math.max(...(analytics?.viewerGrowth || [1]))) * 100}%` }}
                >
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-black text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                        {value}
                    </div>
                </div>
                <span className="text-[10px] text-gray-400 font-bold mt-2 uppercase">D{index + 1}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Engagement */}
        <div className="kazumi-card p-6">
          <h2 className="text-lg font-bold mb-6 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-purple-500" /> Interaction Health
          </h2>
          <div className="space-y-5">
            {Object.entries(analytics?.engagement || {}).map(([key, value], index) => (
              <div key={index}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold capitalize text-gray-700">{key}</span>
                  <span className="text-sm font-black text-black">{value}%</span>
                </div>
                <div className="w-full h-3 bg-gray-50 rounded-full overflow-hidden border border-gray-100">
                  <div className="h-full bg-gradient-to-r from-gray-400 to-black rounded-full transition-all duration-1000" style={{ width: `${value}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Ops + Platform Mix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="kazumi-card p-6">
          <h2 className="text-lg font-bold mb-6 flex items-center gap-2">
            <Activity className="w-5 h-5 text-green-500" /> Ops Health
          </h2>
          <div className="grid grid-cols-2 gap-4">
            {opsMetrics.map((item, index) => (
              <div key={index} className="rounded-xl border border-black/5 bg-white p-4">
                <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">
                  {item.label}
                </div>
                <div className="text-2xl font-black">{item.value}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
            <div className="rounded-lg border border-black/5 p-3">
              <div className="text-gray-400 uppercase tracking-widest text-[10px]">Backend</div>
              <div className="font-bold">{health?.status || "unknown"}</div>
            </div>
            <div className="rounded-lg border border-black/5 p-3">
              <div className="text-gray-400 uppercase tracking-widest text-[10px]">OBS</div>
              <div className="font-bold">{health?.checks?.obs ? "connected" : "disconnected"}</div>
            </div>
            <div className="rounded-lg border border-black/5 p-3">
              <div className="text-gray-400 uppercase tracking-widest text-[10px]">Groq</div>
              <div className="font-bold">{health?.checks?.groq ? "ready" : "offline"}</div>
            </div>
          </div>
        </div>

        <div className="kazumi-card p-6">
          <h2 className="text-lg font-bold mb-6 flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-blue-500" /> Platform Mix
          </h2>
          {platformRows.length === 0 ? (
            <div className="text-sm text-gray-500">No events yet.</div>
          ) : (
            <div className="space-y-4">
              {platformRows.map(([platform, count]) => {
                const total = Math.max(analytics?.totalMessages || 0, 1);
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={platform}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-bold uppercase text-gray-600">{platform}</span>
                      <span className="text-xs font-black text-gray-700">{pct}%</span>
                    </div>
                    <div className="w-full h-3 bg-gray-50 rounded-full overflow-hidden border border-gray-100">
                      <div className="h-full bg-black rounded-full" style={{ width: `${pct}%` }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Event Timeline + Clip Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="kazumi-card p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-500" /> Event Timeline
          </h2>
          {recentEvents.length === 0 ? (
            <div className="text-sm text-gray-500">No recent events.</div>
          ) : (
            <div className="space-y-3 max-h-[320px] overflow-y-auto pr-2">
              {recentEvents.map((ev) => (
                <div key={ev.id} className="border border-black/5 rounded-lg p-3">
                  <div className="text-[10px] uppercase tracking-widest text-gray-400">
                    {ev.platform} • {ev.event_type}
                  </div>
                  <div className="text-sm font-semibold text-gray-900">
                    {ev.username || "Unknown"}
                  </div>
                  {ev.message && (
                    <div className="text-xs text-gray-600 mt-1">{ev.message}</div>
                  )}
                  {ev.created_at && (
                    <div className="text-[10px] text-gray-400 mt-1">
                      {new Date(ev.created_at).toLocaleString()}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="kazumi-card p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-500" /> Clip Analytics
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-black/5 bg-white p-4">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Approved</div>
              <div className="text-2xl font-black">{analytics?.clips?.approved || 0}</div>
            </div>
            <div className="rounded-xl border border-black/5 bg-white p-4">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Pending</div>
              <div className="text-2xl font-black">{analytics?.clips?.pending || 0}</div>
            </div>
            <div className="rounded-xl border border-black/5 bg-white p-4">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Approval Rate</div>
              <div className="text-2xl font-black">{analytics?.approvalRate || 0}%</div>
            </div>
            <div className="rounded-xl border border-black/5 bg-white p-4">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Total Clips</div>
              <div className="text-2xl font-black">
                {(analytics?.clips?.approved || 0) + (analytics?.clips?.pending || 0)}
              </div>
            </div>
          </div>
          <div className="mt-4 text-xs text-gray-500">
            Tip: Approve clips to improve Kazumi’s taste model.
          </div>
        </div>
      </div>

      {/* Taste Profile */}
      <div className="kazumi-card p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-500" /> Taste Profile
          </h2>
          <span className="text-[10px] uppercase tracking-widest text-gray-400">Top Tags</span>
        </div>
        {tasteTags.length === 0 ? (
          <div className="text-sm text-gray-500">Approve a few clips to train Kazumi's taste model.</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {tasteTags.map(([tag, score]) => (
              <span
                key={tag}
                className="px-3 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800"
              >
                {tag} ({score})
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Top Clips Table */}
      <div className="kazumi-card overflow-hidden">
        <div className="p-6 border-b border-gray-50 flex items-center gap-2">
          <Activity className="w-5 h-5 text-red-500" />
          <h2 className="text-lg font-bold">Viral Clips (AI Detected)</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-[10px] font-black uppercase text-gray-400 tracking-widest border-b border-gray-100">
                <th className="py-4 px-6">Clip Title</th>
                <th className="py-4 px-6">Views</th>
                <th className="py-4 px-6">Hype Score</th>
                <th className="py-4 px-6">Trigger</th>
              </tr>
            </thead>
            <tbody>
              {(analytics?.topClips || []).map((clip, index) => (
                <tr key={index} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/50 transition-colors">
                  <td className="py-4 px-6 font-bold">{clip.title}</td>
                  <td className="py-4 px-6 font-mono text-gray-600">{clip.views.toLocaleString()}</td>
                  <td className="py-4 px-6">
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-black">{clip.score}%</span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                      <span className="text-xs font-bold uppercase text-gray-500">{clip.detection}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

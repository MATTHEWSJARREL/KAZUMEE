"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Flame,
  Shield,
  Siren,
  UserX,
} from "lucide-react";
import { apiFetch } from "@/lib/apiClient";

const DEFAULT_METRICS = {
  flagged_total: 0,
  pending: 0,
  resolved: 0,
  resolution_rate: 0,
  actions: {},
};

function severityBadge(severity) {
  if (severity === "critical" || severity === "high") return "bg-red-100 text-red-700 border-red-200";
  if (severity === "medium") return "bg-amber-100 text-amber-700 border-amber-200";
  return "bg-emerald-100 text-emerald-700 border-emerald-200";
}

export default function ModerationPage() {
  const [queue, setQueue] = useState([]);
  const [resolved, setResolved] = useState([]);
  const [auditEntries, setAuditEntries] = useState([]);
  const [summary, setSummary] = useState({ pending_total: 0, by_severity: {}, by_proposed_action: {} });
  const [metrics, setMetrics] = useState(DEFAULT_METRICS);
  const [loading, setLoading] = useState(true);
  const [busyCaseId, setBusyCaseId] = useState(null);
  const [panicBusy, setPanicBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");

  const visibleQueue = useMemo(() => {
    if (severityFilter === "all") return queue;
    return queue.filter((item) => item.severity === severityFilter);
  }, [queue, severityFilter]);

  const refresh = async () => {
    try {
      const [queueRes, resolvedRes, metricsRes, auditRes] = await Promise.all([
        apiFetch("/moderation/queue?limit=60"),
        apiFetch("/moderation/cases?status=resolved&limit=20"),
        apiFetch("/moderation/metrics?hours=24"),
        apiFetch("/moderation/audit?limit=40"),
      ]);

      const queueData = await queueRes.json().catch(() => ({}));
      const resolvedData = await resolvedRes.json().catch(() => ({}));
      const metricsData = await metricsRes.json().catch(() => ({}));
      const auditData = await auditRes.json().catch(() => ({}));

      setQueue(Array.isArray(queueData?.queue) ? queueData.queue : []);
      setSummary(queueData?.summary || { pending_total: 0, by_severity: {}, by_proposed_action: {} });
      setResolved(Array.isArray(resolvedData?.cases) ? resolvedData.cases : []);
      setMetrics({
        flagged_total: metricsData?.flagged_total || 0,
        pending: metricsData?.pending || 0,
        resolved: metricsData?.resolved || 0,
        resolution_rate: metricsData?.resolution_rate || 0,
        actions: metricsData?.actions || {},
      });
      setAuditEntries(Array.isArray(auditData?.entries) ? auditData.entries : []);
    } catch (error) {
      console.error("Failed to refresh moderation data", error);
      setStatusMessage("Could not refresh moderation data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, 12000);
    return () => clearInterval(timer);
  }, []);

  const reviewCase = async (caseId, action) => {
    setBusyCaseId(caseId);
    setStatusMessage("");
    try {
      const res = await apiFetch(`/moderation/cases/${caseId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || "Review failed");
      }
      setStatusMessage(`Case ${caseId} resolved as ${action}.`);
      await refresh();
    } catch (error) {
      setStatusMessage(error?.message || "Could not review case.");
    } finally {
      setBusyCaseId(null);
    }
  };

  const applyBundle = async (caseId, bundle) => {
    setBusyCaseId(caseId);
    setStatusMessage("");
    try {
      const res = await apiFetch("/moderation/bundles/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_id: caseId,
          bundle,
          notes: "Applied from Moderation Center",
          duration_seconds: 600,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || "Bundle failed");
      }
      setStatusMessage(`Bundle ${bundle} applied to case ${caseId}.`);
      await refresh();
    } catch (error) {
      setStatusMessage(error?.message || "Could not apply bundle.");
    } finally {
      setBusyCaseId(null);
    }
  };

  const triggerPanicShield = async () => {
    setPanicBusy(true);
    setStatusMessage("");
    try {
      const res = await apiFetch("/moderation/panic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled: true,
          safe_scene: "BRB",
          follower_only_minutes: 10,
          slow_mode_seconds: 5,
          reason: "Manual panic trigger from moderation center",
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || "Panic shield failed");
      }
      setStatusMessage("Panic shield activated.");
      await refresh();
    } catch (error) {
      setStatusMessage(error?.message || "Could not activate panic shield.");
    } finally {
      setPanicBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading moderation control center...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 md:p-10">
      <div className="text-sm text-gray-500 mb-1">
        <a href="/" className="hover:text-black">Dashboard</a>
        <span className="mx-1.5 text-gray-300">/</span>
        <span>Moderation</span>
      </div>

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold">Moderation Command Center</h1>
          <p className="text-gray-600 mt-1">Triage queue, one-click bundles, panic shield, and full audit trail.</p>
        </div>
        <button
          onClick={triggerPanicShield}
          disabled={panicBusy}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-red-600 text-white font-semibold disabled:opacity-50"
        >
          <Siren className="w-4 h-4" />
          {panicBusy ? "Activating..." : "Panic Shield"}
        </button>
      </div>

      {statusMessage && (
        <div className="mb-6 px-4 py-3 rounded-md border border-black/10 bg-black/5 text-sm text-gray-700">
          {statusMessage}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="kazumi-card p-4">
          <div className="text-xs uppercase text-gray-500">Flagged (24h)</div>
          <div className="text-2xl font-bold mt-1">{metrics.flagged_total}</div>
        </div>
        <div className="kazumi-card p-4">
          <div className="text-xs uppercase text-gray-500">Pending Queue</div>
          <div className="text-2xl font-bold mt-1">{summary.pending_total || metrics.pending}</div>
        </div>
        <div className="kazumi-card p-4">
          <div className="text-xs uppercase text-gray-500">Resolved (24h)</div>
          <div className="text-2xl font-bold mt-1">{metrics.resolved}</div>
        </div>
        <div className="kazumi-card p-4">
          <div className="text-xs uppercase text-gray-500">Resolution Rate</div>
          <div className="text-2xl font-bold mt-1">{metrics.resolution_rate}%</div>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        {["all", "critical", "high", "medium", "low"].map((severity) => (
          <button
            key={severity}
            onClick={() => setSeverityFilter(severity)}
            className={`px-3 py-1.5 rounded-md text-sm capitalize ${
              severityFilter === severity ? "bg-black text-white" : "bg-black/5 text-gray-700 hover:bg-black/10"
            }`}
          >
            {severity}
          </button>
        ))}
      </div>

      <div className="kazumi-card p-5 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5" />
          <h2 className="text-lg font-bold">Triage Queue</h2>
        </div>
        {visibleQueue.length === 0 ? (
          <div className="text-sm text-gray-500">No pending moderation cases.</div>
        ) : (
          <div className="space-y-4">
            {visibleQueue.map((item) => (
              <div key={item.id} className="border border-black/10 rounded-lg p-4">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <span className={`text-xs px-2 py-1 border rounded-md font-semibold ${severityBadge(item.severity)}`}>
                    {item.severity}
                  </span>
                  <span className="text-xs px-2 py-1 rounded-md bg-black/5">{item.platform}</span>
                  <span className="text-xs text-gray-500">confidence {(item.confidence * 100).toFixed(0)}%</span>
                  <span className="text-xs text-gray-500 ml-auto">{new Date(item.created_at).toLocaleString()}</span>
                </div>
                <div className="text-sm font-semibold mb-1">{item.username}</div>
                <div className="text-sm text-gray-700 mb-2">{item.message}</div>
                <div className="text-xs text-gray-500 mb-3">
                  Proposed: <span className="font-semibold">{item.proposed_action}</span> • Reason: {item.reason}
                </div>

                <div className="flex flex-wrap gap-2 mb-2">
                  {["allow", "warn", "timeout", "ban"].map((action) => (
                    <button
                      key={action}
                      disabled={busyCaseId === item.id}
                      onClick={() => reviewCase(item.id, action)}
                      className="px-3 py-1.5 text-xs rounded-md border border-black/15 hover:bg-black/5 disabled:opacity-50"
                    >
                      {action}
                    </button>
                  ))}
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    disabled={busyCaseId === item.id}
                    onClick={() => applyBundle(item.id, "warn_only")}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-md bg-blue-100 text-blue-700 border border-blue-200 disabled:opacity-50"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    Warn Bundle
                  </button>
                  <button
                    disabled={busyCaseId === item.id}
                    onClick={() => applyBundle(item.id, "timeout_purge")}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-md bg-amber-100 text-amber-700 border border-amber-200 disabled:opacity-50"
                  >
                    <Clock className="w-3.5 h-3.5" />
                    Timeout + Purge
                  </button>
                  <button
                    disabled={busyCaseId === item.id}
                    onClick={() => applyBundle(item.id, "nuke_user")}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-md bg-red-100 text-red-700 border border-red-200 disabled:opacity-50"
                  >
                    <UserX className="w-3.5 h-3.5" />
                    Nuke User
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="kazumi-card p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5" />
            <h2 className="text-lg font-bold">Recently Resolved</h2>
          </div>
          {resolved.length === 0 ? (
            <div className="text-sm text-gray-500">No resolved cases yet.</div>
          ) : (
            <div className="space-y-3">
              {resolved.slice(0, 10).map((item) => (
                <div key={item.id} className="border border-black/10 rounded-md p-3">
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                    <span>{item.username}</span>
                    <span>•</span>
                    <span>{item.final_action || item.proposed_action}</span>
                    <span className="ml-auto">{item.reviewer || "system"}</span>
                  </div>
                  <div className="text-sm text-gray-700">{item.message}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="kazumi-card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Flame className="w-5 h-5" />
            <h2 className="text-lg font-bold">Audit Trail</h2>
          </div>
          {auditEntries.length === 0 ? (
            <div className="text-sm text-gray-500">No audit entries yet.</div>
          ) : (
            <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
              {auditEntries.map((entry) => (
                <div key={entry.id} className="border border-black/10 rounded-md p-3">
                  <div className="text-xs text-gray-500 mb-1">
                    {new Date(entry.created_at).toLocaleString()} • {entry.action}
                  </div>
                  <div className="text-sm font-semibold">
                    {entry.target_user || "system"}
                    {entry.bundle ? ` • ${entry.bundle}` : ""}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    by {entry.actor_email || "unknown"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


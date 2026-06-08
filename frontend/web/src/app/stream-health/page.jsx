"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/apiClient";
import {
  Home,
  Radio,
  Activity,
  Cpu,
  HardDrive,
  Wifi,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  RefreshCw,
} from "lucide-react";

export default function StreamHealthPage() {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchHealthData();
    const interval = setInterval(fetchHealthData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchHealthData = async () => {
    try {
      setRefreshing(true);
      const response = await apiFetch("/api/stream-health");
      if (!response.ok) throw new Error("Failed to fetch health data");
      const data = await response.json();
      setHealthData(data);
    } catch (error) {
      console.error("Error fetching health data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const metrics = [
    {
      label: "CPU Usage",
      value: healthData?.cpuUsage || 0,
      unit: "%",
      icon: Cpu,
      status: (healthData?.cpuUsage || 0) > 80 ? "warning" : "healthy",
    },
    {
      label: "GPU Usage",
      value: healthData?.gpuUsage || 0,
      unit: "%",
      icon: Activity,
      status: (healthData?.gpuUsage || 0) > 90 ? "warning" : "healthy",
    },
    {
      label: "Memory Usage",
      value: healthData?.memoryUsage || 0,
      unit: "%",
      icon: HardDrive,
      status: (healthData?.memoryUsage || 0) > 85 ? "warning" : "healthy",
    },
    {
      label: "Network Latency",
      value: healthData?.networkLatency || 0,
      unit: "ms",
      icon: Wifi,
      status: (healthData?.networkLatency || 0) > 50 ? "warning" : "healthy",
    },
  ];

  const streamStats = [
    {
      label: "Bitrate",
      value: healthData?.bitrate || 0,
      unit: "kbps",
      trend: healthData?.bitrateTrend || "stable",
    },
    {
      label: "Dropped Frames",
      value: healthData?.droppedFrames || 0,
      unit: "frames",
      trend: healthData?.droppedFramesTrend || "stable",
    },
    {
      label: "Prediction Score",
      value: healthData?.predictionScore || 0,
      unit: "%",
      trend: healthData?.predictionTrend || "stable",
    },
  ];

  const actions = healthData?.actions || [];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading stream health...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 md:p-10">
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500 mb-1">
        <a href="/" className="hover:text-black">
          Dashboard
        </a>
        <span className="mx-1.5 text-gray-300">/</span>
        <span>Stream Health</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl md:text-4xl font-bold">
          Stream Health Monitor
        </h1>
        <button
          onClick={fetchHealthData}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-md hover:bg-gray-800 disabled:opacity-50"
        >
          <RefreshCw
            className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
          />
          Refresh
        </button>
      </div>

      {/* Overall Status */}
      <div className="kazumi-card p-6 mb-8">
        <div className="flex items-center gap-6">
          <div
            className={`w-16 h-16 rounded-full flex items-center justify-center ${
              healthData?.healthStatus === "healthy"
                ? "bg-green-100"
                : "bg-yellow-100"
            }`}
          >
            {healthData?.healthStatus === "healthy" ? (
              <CheckCircle className="w-8 h-8 text-green-600" />
            ) : (
              <AlertTriangle className="w-8 h-8 text-yellow-600" />
            )}
          </div>
          <div className="flex-1">
            <div className="text-sm text-gray-500 mb-1">Overall Status</div>
            <div className="text-3xl font-bold capitalize">
              {healthData?.healthStatus || "Unknown"}
            </div>
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <span
                className={`text-xs px-2 py-1 rounded-full border ${
                  healthData?.obsConnected
                    ? "bg-green-50 text-green-700 border-green-200"
                    : "bg-red-50 text-red-700 border-red-200"
                }`}
              >
                OBS {healthData?.obsConnected ? "Connected" : "Disconnected"}
              </span>
              <span className="text-xs text-gray-500">
                Last updated: {new Date().toLocaleTimeString()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* System Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metrics.map((metric, index) => {
          const IconComponent = metric.icon;
          const isWarning = metric.status === "warning";
          return (
            <div
              key={index}
              className={`rounded-2xl border p-6 ${
                isWarning ? "border-yellow-400 bg-yellow-50" : "border-black/10 bg-white"
              }`}
            >
              <div className="flex items-center justify-between mb-4">
                <IconComponent
                  className={`w-6 h-6 ${
                    isWarning ? "text-yellow-600" : "text-gray-600"
                  }`}
                />
                {isWarning && (
                  <AlertTriangle className="w-5 h-5 text-yellow-600" />
                )}
              </div>
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">
                {metric.label}
              </div>
              <div className="text-3xl font-bold">
                {metric.value}
                <span className="text-lg text-gray-500">{metric.unit}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Stream Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {streamStats.map((stat, index) => (
          <div key={index} className="kazumi-card p-6">
            <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">
              {stat.label}
            </div>
            <div className="flex items-baseline gap-2 mb-2">
              <div className="text-3xl font-bold">{stat.value}</div>
              <div className="text-sm text-gray-500">{stat.unit}</div>
            </div>
            <div className="flex items-center gap-1">
              {stat.trend === "up" && (
                <TrendingUp className="w-4 h-4 text-red-600" />
              )}
              {stat.trend === "down" && (
                <TrendingDown className="w-4 h-4 text-green-600" />
              )}
              <span className="text-xs text-gray-500 capitalize">
                {stat.trend}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Actionable Health Suggestions */}
      <div className="kazumi-card p-6 mb-8">
        <h2 className="text-lg font-bold mb-4">Actionable Health Suggestions</h2>
        {actions.length === 0 ? (
          <div className="text-center text-gray-500 py-4">
            No actions required right now
          </div>
        ) : (
          <div className="space-y-3">
            {actions.map((action, index) => (
              <div
                key={`${action.action}-${index}`}
                className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 p-3 bg-black/5 rounded-md"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      action.severity === "high"
                        ? "bg-red-500"
                        : action.severity === "warning"
                          ? "bg-yellow-500"
                          : "bg-green-500"
                    }`}
                  ></div>
                  <div>
                    <div className="text-sm font-semibold capitalize">
                      {action.action.replace(/_/g, " ")}
                    </div>
                    <div className="text-xs text-gray-600">{action.reason}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-600">
                  <span>{Math.round((action.confidence || 0) * 100)}%</span>
                  <span className="text-gray-300">•</span>
                  <span>{action.execute ? "Auto action queued" : "Suggested"}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI Predictions */}
      <div className="kazumi-card p-6">
        <h2 className="text-lg font-bold mb-4">AI Health Predictions</h2>
        <div className="space-y-3">
          {healthData?.predictions?.map((prediction, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-black/5 rounded-md"
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-2 h-2 rounded-full ${
                    prediction.severity === "high"
                      ? "bg-red-500"
                      : prediction.severity === "medium"
                        ? "bg-yellow-500"
                        : "bg-green-500"
                  }`}
                ></div>
                <span className="text-sm">{prediction.message}</span>
              </div>
              <span className="text-xs text-gray-500">
                {prediction.confidence}% confidence
              </span>
            </div>
          )) || (
            <div className="text-center text-gray-500 py-4">
              No predictions available
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

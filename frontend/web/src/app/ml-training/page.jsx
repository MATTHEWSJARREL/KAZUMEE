"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/apiClient";
import {
  Brain,
  TrendingUp,
  Zap,
  Target,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Settings,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";

export default function MLTrainingPage() {
  const [mlData, setMlData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    fetchMLData();
  }, []);

  const fetchMLData = async () => {
    try {
      const response = await apiFetch("/api/ml-training");
      if (!response.ok) throw new Error("Failed to fetch ML data");
      const data = await response.json();
      setMlData(data);
    } catch (error) {
      console.error("Error fetching ML data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleTrainingCycle = async () => {
    setTraining(true);
    setStatusMessage("");
    try {
      const response = await apiFetch("/api/ml-training", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "train" }),
      });
      if (!response.ok) throw new Error("Failed to start training");
      const payload = await response.json();
      setStatusMessage(payload.message || "Training completed.");
      await fetchMLData();
    } catch (error) {
      console.error("Error starting training:", error);
      setStatusMessage("Training failed. Check backend logs.");
    } finally {
      setTraining(false);
    }
  };

  const handleFeedback = async (dataId, feedbackType) => {
    try {
      const response = await apiFetch("/api/ml-training/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataId, feedback: feedbackType }),
      });
      if (!response.ok) throw new Error("Failed to submit feedback");
      setStatusMessage("Feedback applied to learning profile.");
      await fetchMLData();
    } catch (error) {
      console.error("Error submitting feedback:", error);
    }
  };

  const modelStats = [
    {
      label: "Overall Confidence",
      value: mlData?.overallConfidence || 0,
      icon: Brain,
      color: "text-purple-600",
      bgColor: "bg-purple-100",
    },
    {
      label: "Training Samples",
      value: mlData?.totalSamples || 0,
      icon: Target,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
    },
    {
      label: "Accuracy Rate",
      value: mlData?.accuracyRate || 0,
      icon: TrendingUp,
      color: "text-green-600",
      bgColor: "bg-green-100",
    },
    {
      label: "Active Models",
      value: mlData?.activeModels || 0,
      icon: Zap,
      color: "text-orange-600",
      bgColor: "bg-orange-100",
    },
  ];

  const learningCategories = mlData?.categories || [];
  const recentLearning = mlData?.recentLearning || [];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading ML training data...</p>
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
        <span>ML Training</span>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold mb-2">
            Machine Learning Dashboard
          </h1>
          <p className="text-gray-600">
            Monitor and tune Kazumi's feedback-driven learning profile
          </p>
        </div>
        <button
          onClick={handleTrainingCycle}
          disabled={training}
          className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-md hover:bg-gray-800 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${training ? "animate-spin" : ""}`} />
          {training ? "Rebuilding..." : "Rebuild Learning Profile"}
        </button>
      </div>
      {statusMessage && (
        <div className="mb-6 text-sm text-gray-700 bg-black/5 border border-black/10 rounded-md px-4 py-3">
          {statusMessage}
        </div>
      )}

      {/* Model Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {modelStats.map((stat, index) => {
          const IconComponent = stat.icon;
          return (
            <div key={index} className="kazumi-card p-6">
              <div className="flex items-center justify-between mb-4">
                <div
                  className={`w-12 h-12 ${stat.bgColor} rounded-full flex items-center justify-center`}
                >
                  <IconComponent className={`w-6 h-6 ${stat.color}`} />
                </div>
              </div>
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                {stat.label}
              </div>
              <div className="text-3xl font-bold">
                {stat.label.includes("Confidence") ||
                stat.label.includes("Accuracy")
                  ? `${stat.value}%`
                  : stat.value.toLocaleString()}
              </div>
            </div>
          );
        })}
      </div>

      {/* Learning Categories */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="kazumi-card p-6">
          <h2 className="text-lg font-bold mb-4">Learning Categories</h2>
          <div className="space-y-4">
            {learningCategories.map((category, index) => (
              <div key={index}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{category.name}</span>
                    <span className="text-xs text-gray-500">
                      ({category.samples} samples)
                    </span>
                  </div>
                  <span className="text-sm font-bold">
                    {category.confidence}%
                  </span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-600 rounded-full"
                    style={{ width: `${category.confidence}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Model Configuration */}
        <div className="kazumi-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Settings className="w-5 h-5" />
            <h2 className="text-lg font-bold">Model Configuration</h2>
          </div>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-2">
                Learning Rate
              </label>
              <input
                type="range"
                min="0"
                max="100"
                defaultValue={mlData?.learningRate || 75}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Conservative</span>
                <span>Aggressive</span>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">
                Automation Level
              </label>
              <input
                type="range"
                min="0"
                max="100"
                defaultValue={mlData?.automationLevel || 60}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Manual</span>
                <span>Full Auto</span>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">
                Confidence Threshold
              </label>
              <input
                type="range"
                min="0"
                max="100"
                defaultValue={mlData?.confidenceThreshold || 80}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Low</span>
                <span>High</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Learning Data */}
      <div className="kazumi-card overflow-hidden">
        <div className="p-6 border-b border-black/5">
          <h2 className="text-lg font-bold">Recent Learning Events</h2>
        </div>
        <div className="overflow-x-auto">
          <div className="grid grid-cols-[2fr,1fr,1fr,1fr,100px] bg-black/5 text-xs font-medium uppercase text-gray-500 py-3 px-4 min-w-[700px]">
            <div>Event</div>
            <div>Category</div>
            <div>Confidence</div>
            <div>Status</div>
            <div>Feedback</div>
          </div>
          {recentLearning.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No recent learning events
            </div>
          ) : (
            recentLearning.map((event, index) => (
              <div
                key={index}
                className="grid grid-cols-[2fr,1fr,1fr,1fr,100px] text-sm border-b border-black/5 py-3 px-4 min-w-[700px] items-center"
              >
                <div className="truncate">{event.content}</div>
                <div className="capitalize">{event.category}</div>
                <div>{event.confidence}%</div>
                <div>
                  {event.feedbackScore > 0 ? (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle className="w-4 h-4" />
                      Verified
                    </span>
                  ) : event.feedbackScore < 0 ? (
                    <span className="flex items-center gap-1 text-red-600">
                      <AlertCircle className="w-4 h-4" />
                      Rejected
                    </span>
                  ) : (
                    <span className="text-gray-500">Pending</span>
                  )}
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleFeedback(event.id, "positive")}
                    className="p-1 hover:bg-green-50 rounded"
                    title="Good"
                  >
                    <ThumbsUp className="w-4 h-4 text-green-600" />
                  </button>
                  <button
                    onClick={() => handleFeedback(event.id, "negative")}
                    className="p-1 hover:bg-red-50 rounded"
                    title="Bad"
                  >
                    <ThumbsDown className="w-4 h-4 text-red-600" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

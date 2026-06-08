"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/apiClient";
import {
  MessageSquare,
  Crown,
  Star,
  Users,
  CheckCircle,
  Clock,
  XCircle,
  Filter,
  ArrowUp,
  Zap,
  Send,
  Loader2
} from "lucide-react";

export default function CommandQueuePage() {
  const [commands, setCommands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterTier, setFilterTier] = useState("all");
  
  // New AI Brain States
  const [brainInput, setBrainInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastAiResponse, setLastAiResponse] = useState(null);

  useEffect(() => {
    fetchCommands();
    const interval = setInterval(fetchCommands, 3000);
    return () => clearInterval(interval);
  }, [filterStatus, filterTier]);

  const fetchCommands = async () => {
    try {
      const response = await apiFetch(
        `/api/commands?status=${filterStatus}&tier=${filterTier}`,
      );
      if (!response.ok) throw new Error("Failed to fetch commands");
      const data = await response.json();
      setCommands(data.commands || []);
    } catch (error) {
      console.error("Error fetching commands:", error);
    } finally {
      setLoading(false);
    }
  };

  // New: Handle sending natural language to the backend
  const handleBrainCommand = async (e) => {
    e.preventDefault();
    if (!brainInput.trim()) return;

    setIsProcessing(true);
    try {
      const response = await apiFetch("/api/commands/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: brainInput, role: "streamer" }),
      });
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || data?.message || `Error (${response.status})`);
      }
      setLastAiResponse(data.message || "Command processed successfully.");
      setBrainInput(""); // Clear input
      fetchCommands(); // Refresh list to see the new action
    } catch (error) {
      console.error("Brain Error:", error);
      setLastAiResponse(error?.message || "Error: Could not reach the Kazumi Brain.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExecuteCommand = async (commandId) => {
    const command = commands.find((item) => item.id === commandId);
    const label = command?.intent || command?.command_text || "this command";
    if (!window.confirm(`Run OBS action "${label}" now?`)) return;
    try {
      const response = await apiFetch(`/api/commands/${commandId}/execute`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to execute command");
      await fetchCommands();
    } catch (error) {
      console.error("Error executing command:", error);
    }
  };

  const handleRejectCommand = async (commandId) => {
    try {
      const response = await apiFetch(`/api/commands/${commandId}/reject`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to reject command");
      await fetchCommands();
    } catch (error) {
      console.error("Error rejecting command:", error);
    }
  };

  const getTierIcon = (tier) => {
    switch (tier) {
      case "vip":
        return <Crown className="w-4 h-4 text-yellow-600" />;
      case "premium":
        return <Star className="w-4 h-4 text-blue-600" />;
      default:
        return <Users className="w-4 h-4 text-gray-600" />;
    }
  };

  const getTierBadge = (tier) => {
    const colors = {
      vip: "bg-yellow-100 text-yellow-800",
      premium: "bg-blue-100 text-blue-800",
      free: "bg-gray-100 text-gray-800",
    };
    return colors[tier] || colors.free;
  };

  const stats = {
    pending: commands.filter((c) => c.status === "pending").length,
    executed: commands.filter((c) => c.status === "executed").length,
    vip: commands.filter((c) => c.viewer_tier === "vip").length,
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading command queue...</p>
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
        <span>Command Queue</span>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold mb-2">Command Center</h1>
          <p className="text-gray-600">Priority-based viewer management & AI Directives</p>
        </div>
      </div>

      {/* --- NEW: AI BRAIN CONSOLE --- */}
      <div className="mb-10 bg-black rounded-xl p-6 text-white shadow-2xl">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="w-5 h-5 text-yellow-400 fill-yellow-400" />
          <h2 className="text-lg font-semibold tracking-tight">Kazumi Brain Console</h2>
        </div>
        
        <form onSubmit={handleBrainCommand} className="relative">
          <input
            type="text"
            value={brainInput}
            onChange={(e) => setBrainInput(e.target.value)}
            placeholder="Type a natural language command (e.g. 'Switch to BRB and mute mic')..."
            className="w-full bg-gray-900 border border-gray-800 rounded-lg py-4 pl-4 pr-14 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 transition-all"
            disabled={isProcessing}
          />
          <button 
            type="submit"
            disabled={isProcessing || !brainInput.trim()}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 hover:bg-gray-800 rounded-md transition-colors disabled:opacity-50"
          >
            {isProcessing ? <Loader2 className="w-6 h-6 animate-spin" /> : <Send className="w-6 h-6 text-yellow-400" />}
          </button>
        </form>

        {lastAiResponse && (
          <div className="mt-4 p-3 bg-gray-900/50 border-l-2 border-yellow-500 rounded text-sm text-gray-300 italic">
            <strong>Brain Reasoning:</strong> {lastAiResponse}
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="kazumi-card p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
              <Clock className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Pending</div>
              <div className="text-2xl font-bold">{stats.pending}</div>
            </div>
          </div>
        </div>
        <div className="kazumi-card p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">Executed</div>
              <div className="text-2xl font-bold">{stats.executed}</div>
            </div>
          </div>
        </div>
        <div className="kazumi-card p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
              <Crown className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-gray-500">VIP Commands</div>
              <div className="text-2xl font-bold">{stats.vip}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="flex gap-2">
          {["all", "pending", "executed"].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-4 py-2 rounded-md text-sm font-medium capitalize ${
                filterStatus === status ? "bg-black text-white" : "bg-black/5 text-gray-700 hover:bg-black/10"
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Table Section */}
      <div className="kazumi-card overflow-hidden">
        <div className="overflow-x-auto">
          <div className="grid grid-cols-[auto,2fr,1fr,1fr,1fr,120px] bg-black/5 text-xs font-medium uppercase text-gray-500 py-3 px-4 min-w-[800px]">
            <div>Priority</div>
            <div>Command / AI Action</div>
            <div>Viewer / System</div>
            <div>Type</div>
            <div>Status</div>
            <div>Actions</div>
          </div>
          {commands.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No commands in queue</div>
          ) : (
            commands.map((command, index) => (
              <div key={index} className="grid grid-cols-[auto,2fr,1fr,1fr,1fr,120px] text-sm border-b border-black/5 py-3 px-4 min-w-[800px] items-center hover:bg-black/5 transition-colors">
                <div className="flex items-center gap-2">
                  <ArrowUp className={`w-4 h-4 ${command.priority > 50 ? "text-red-600" : "text-gray-400"}`} />
                  <span className="font-mono text-xs">{command.priority}</span>
                </div>
                <div className="pr-4">
                  <div className="truncate font-medium">
                    {command.command_text}
                  </div>
                  {(command.ai_reasoning || command.confidence_score) && (
                    <div className="text-[11px] text-gray-500 mt-1">
                      {command.ai_reasoning ? `Reason: ${command.ai_reasoning}` : "Reason: n/a"}
                      {command.confidence_score != null && (
                        <span className="ml-2">Confidence: {Number(command.confidence_score).toFixed(2)}</span>
                      )}
                    </div>
                  )}
                  {command.intent && (
                    <div className="text-[11px] text-gray-500 mt-1">
                      Intent: {command.intent}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {getTierIcon(command.viewer_tier)}
                  <span className="truncate">{command.viewer_username}</span>
                </div>
                <div>
                  <span className={`text-xs px-2 py-1 rounded-md ${getTierBadge(command.viewer_tier)}`}>
                    {command.command_type}
                  </span>
                </div>
                <div>
                   {/* Status Logic remains the same */}
                   {command.status === "executed" ? (
                    <span className="flex items-center gap-1 text-green-600 font-medium">
                      <CheckCircle className="w-4 h-4" /> Executed
                    </span>
                  ) : command.status === "rejected" ? (
                    <span className="flex items-center gap-1 text-red-600 font-medium">
                      <XCircle className="w-4 h-4" /> Rejected
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-yellow-600 font-medium">
                      <Clock className="w-4 h-4" /> Pending
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {command.status === "pending" && (
                    <>
                      <button onClick={() => handleExecuteCommand(command.id)} className="px-3 py-1 bg-black text-white rounded-md hover:bg-gray-800 text-xs">Run</button>
                      <button onClick={() => handleRejectCommand(command.id)} className="px-3 py-1 border border-red-300 text-red-600 rounded-md hover:bg-red-50 text-xs text-nowrap">Skip</button>
                    </>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

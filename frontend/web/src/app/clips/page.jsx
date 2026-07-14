"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/apiClient";
import {
  Scissors,
  Play,
  Eye,
  Tag,
  Download,
  Trash2,
  Edit,
  Sparkles,
  Plus,
  Search,
  Zap,
  Loader2,
  TrendingUp
} from "lucide-react";

export default function ClipsLibraryPage() {
  const [clips, setClips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isAiSearching, setIsAiSearching] = useState(false);

  useEffect(() => {
    fetchClips();
  }, [filter]);

  const fetchClips = async () => {
    try {
      setLoading(true);
      const response = await apiFetch(`/api/clips?filter=${filter}`);
      if (!response.ok) throw new Error("Failed to fetch clips");
      const data = await response.json();
      setClips(data.clips || []);
    } catch (error) {
      console.error("Error fetching clips:", error);
    } finally {
      setLoading(false);
    }
  };

  // NEW: Semantic Search (Uses Kazumi Brain)
  const handleAiSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsAiSearching(true);
    
    try {
      const response = await apiFetch("/api/commands/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          command: `Find clips that match this description: ${searchQuery}`,
          role: "streamer",
        }),
      });
      // Assuming your backend returns a list of matching clip IDs
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result?.detail || result?.message || `Error (${response.status})`);
      }
      console.log("AI Search Result:", result);
      // Logic to filter clips based on AI response would go here
    } catch (err) {
      console.error("AI Search failed:", err);
    } finally {
      setIsAiSearching(false);
    }
  };

  const handleDeleteClip = async (clipId) => {
    if (!confirm("Are you sure you want to delete this clip?")) return;
    setClips(clips.filter((c) => c.id !== clipId));
  };

  const formatDuration = (start, end) => `${Math.abs(end - start)}s`;

  const filteredClips = clips.filter((clip) => {
    if (searchQuery && !isAiSearching) {
      return (
        clip.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (clip.tags || []).some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400 font-medium">Scanning clip metadata...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 md:p-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
            <Scissors className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl md:text-2xl font-bold">Clips Library</h2>
            <p className="text-xs text-gray-400">Manage and export your best moments</p>
          </div>
        </div>
        <a href="/" className="px-4 py-2 rounded-lg bg-white/10 border border-white/20 hover:bg-white/20 transition-colors text-sm font-medium">
          ← Back to Dashboard
        </a>
      </div>

      <div className="p-6 md:p-10">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-10 gap-4">
        <div>
          <h1 className="text-4xl font-black tracking-tight">Your Clips</h1>
          <p className="text-gray-400 text-sm mt-1">{filteredClips.length} clips available</p>
        </div>
        <div className="flex gap-3">
            <button className="flex items-center gap-2 px-6 py-3 bg-white/10 border border-white/20 text-white font-bold rounded-xl hover:bg-white/20 transition-all">
                <Download className="w-4 h-4" /> Export All
            </button>
            <button className="flex items-center gap-2 px-6 py-3 bg-purple-600 text-white font-bold rounded-xl hover:bg-purple-700 shadow-lg shadow-purple-600/20 transition-all">
                <Plus className="w-4 h-4" /> Create Clip
            </button>
        </div>
      </div>

      {/* --- Kazumi Smart Search --- */}
      <div className="mb-10 group relative">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
          {isAiSearching ? <Loader2 className="w-5 h-5 text-purple-500 animate-spin" /> : <Search className="w-5 h-5 text-gray-400 group-focus-within:text-black" />}
        </div>
        <input
          type="text"
          placeholder="Ask Kazumi: 'Find the funniest deaths' or 'High energy moments'..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAiSearch()}
          className="w-full pl-12 pr-32 py-4 bg-black/5 border-2 border-transparent rounded-2xl focus:bg-white focus:border-black transition-all outline-none text-lg font-medium shadow-sm"
        />
        <button 
            onClick={handleAiSearch}
            className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-bold hover:bg-purple-700 transition-colors"
        >
            <Zap className="w-4 h-4 fill-white" /> AI Search
        </button>
      </div>

      {/* Clips Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredClips.map((clip) => (
          <div key={clip.id} className="group flex flex-col rounded-2xl overflow-hidden bg-slate-700/50 border border-white/10 hover:border-purple-500/50 transition-all hover:shadow-2xl hover:shadow-purple-600/20">
            {/* Thumbnail Box */}
            <div className="relative aspect-video overflow-hidden bg-gradient-to-br from-slate-600 to-slate-800 mb-0">
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent z-10" />
              <Play className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 text-white z-20 opacity-0 group-hover:opacity-100 transition-all scale-75 group-hover:scale-100 drop-shadow-lg" />
              
              {/* Badges */}
              <div className="absolute top-3 left-3 flex gap-2 z-20">
                {clip.auto_detected && (
                  <span className="px-2 py-1 bg-purple-600 text-[10px] font-black text-white rounded uppercase tracking-wider flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> AI Pick
                  </span>
                )}
                {clip.performance_score > 0.8 && (
                    <span className="px-2 py-1 bg-green-500 text-[10px] font-black text-white rounded uppercase tracking-wider flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" /> Viral
                    </span>
                )}
              </div>
              
              <span className="absolute bottom-3 right-3 px-2 py-1 bg-black/80 text-white text-[10px] font-bold rounded z-20">
                {formatDuration(clip.timestamp_start, clip.timestamp_end)}
              </span>
            </div>

            {/* Meta */}
            <div className="p-4 flex flex-col flex-1">
              <h3 className="font-bold text-lg mb-2 group-hover:text-purple-300 transition-colors truncate">{clip.title}</h3>
              <div className="flex items-center gap-4 text-gray-400 text-sm mb-4 flex-1">
                <span className="flex items-center gap-1 font-medium"><Eye className="w-4 h-4" /> {clip.view_count || 0}</span>
                <span className="flex items-center gap-1 font-medium"><Tag className="w-4 h-4" /> {Math.round((clip.performance_score || 0.5) * 100)}% Heat</span>
              </div>

              <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="flex-1 py-2 bg-purple-600 text-white text-xs font-bold rounded-lg hover:bg-purple-700 transition-colors">Edit</button>
                <button className="p-2 border border-white/20 text-gray-300 rounded-lg hover:bg-white/10 transition-colors"><Download className="w-4 h-4" /></button>
                <button onClick={() => handleDeleteClip(clip.id)} className="p-2 border border-red-500/30 text-red-400 rounded-lg hover:bg-red-500/20 transition-colors"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredClips.length === 0 && (
        <div className="text-center py-20">
          <Scissors className="w-16 h-16 text-gray-500 mx-auto mb-4 opacity-50" />
          <p className="text-gray-400 text-lg">No clips yet. Start clipping moments to see them here!</p>
        </div>
      )}
      </div>
    </div>
  );
}

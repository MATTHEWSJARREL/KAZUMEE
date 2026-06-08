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
    <div className="min-h-screen p-6 md:p-10">
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500 mb-1 flex items-center gap-2">
        <a href="/" className="hover:text-black">Dashboard</a>
        <span className="text-gray-300">/</span>
        <span className="text-black font-medium">Clips Library</span>
      </div>

      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-10 gap-4">
        <h1 className="text-4xl font-black tracking-tight">Clips Library</h1>
        <div className="flex gap-3">
            <button className="flex items-center gap-2 px-6 py-3 bg-black/5 text-black font-bold rounded-xl hover:bg-black/10 transition-all">
                <Download className="w-4 h-4" /> Export All
            </button>
            <button className="flex items-center gap-2 px-6 py-3 bg-black text-white font-bold rounded-xl hover:bg-gray-800 shadow-lg shadow-black/20 transition-all">
                <Plus className="w-4 h-4" /> Create Manual
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {filteredClips.map((clip) => (
          <div key={clip.id} className="group flex flex-col">
            {/* Thumbnail Box */}
            <div className="relative aspect-video rounded-2xl overflow-hidden bg-gray-200 mb-4 shadow-sm group-hover:shadow-xl transition-all duration-300 group-hover:-translate-y-1">
              <div className="absolute inset-0 bg-black/20 group-hover:bg-black/40 transition-colors z-10" />
              <Play className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 text-white z-20 opacity-0 group-hover:opacity-100 transition-all scale-75 group-hover:scale-100" />
              
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
            <div className="px-1">
              <h3 className="font-bold text-xl mb-1 group-hover:text-purple-600 transition-colors truncate">{clip.title}</h3>
              <div className="flex items-center gap-4 text-gray-500 text-sm mb-4">
                <span className="flex items-center gap-1 font-medium"><Eye className="w-4 h-4" /> {clip.view_count || 0}</span>
                <span className="flex items-center gap-1 font-medium"><Tag className="w-4 h-4" /> {Math.round((clip.performance_score || 0.5) * 100)}% Heat</span>
              </div>
              
              <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="flex-1 py-2 bg-black text-white text-xs font-bold rounded-lg hover:bg-gray-800 transition-colors">Edit Clip</button>
                <button className="p-2 border border-black/10 rounded-lg hover:bg-black/5 transition-colors"><Download className="w-4 h-4" /></button>
                <button onClick={() => handleDeleteClip(clip.id)} className="p-2 border border-red-100 text-red-500 rounded-lg hover:bg-red-50 transition-colors"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/apiClient";
import { toast } from "sonner";
import {
  CheckCircle,
  XCircle,
  Play,
  Clock,
  User,
  Video,
  Eye,
  AlertCircle,
  Search,
  Filter,
  Download,
  Share2,
  BarChart3,
  Tag,
  Calendar,
  Star,
} from "lucide-react";

export default function ClipManagement() {
  const [pendingClips, setPendingClips] = useState([]);
  const [recentClips, setRecentClips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedClip, setSelectedClip] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterRequester, setFilterRequester] = useState("all");
  const [sortBy, setSortBy] = useState("date");
  const [selectedClips, setSelectedClips] = useState([]);
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [activeTab, setActiveTab] = useState("pending");
  const [clipNotes, setClipNotes] = useState({});

  useEffect(() => {
    fetchClips();
  }, []);

  const fetchClips = async () => {
    try {
      const [pendingRes, recentRes] = await Promise.all([
        apiFetch("/clips/pending"),
        apiFetch("/clips/recent?limit=20"),
      ]);

      if (pendingRes.ok) {
        const pendingData = await pendingRes.json();
        setPendingClips(pendingData.clips);
      }

      if (recentRes.ok) {
        const recentData = await recentRes.json();
        setRecentClips(recentData.clips);
      }
    } catch (error) {
      console.error("Failed to fetch clips:", error);
      toast.error("Failed to load clips");
    } finally {
      setLoading(false);
    }
  };

  const handleReviewClip = async (clipId, action, notesOverride) => {
    try {
      const response = await apiFetch("/clips/review", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          clip_id: clipId,
          action: action,
          notes: notesOverride ?? clipNotes[clipId] ?? (action === 'reject' ? 'Rejected by streamer' : null)
        })
      });

      if (response.ok) {
        toast.success(`Clip ${action}d successfully`);
        fetchClips(); // Refresh the lists
      } else {
        toast.error(`Failed to ${action} clip`);
      }
    } catch (error) {
      console.error(`Failed to ${action} clip:`, error);
      toast.error(`Failed to ${action} clip`);
    }
  };

  const openClip = async (filePath) => {
    try {
      await apiFetch("/clips/open", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: filePath })
      });
    } catch (error) {
      console.error("Failed to open clip:", error);
      toast.error("Failed to open clip");
    }
  };

  const handleExportClip = async (clipId, preset) => {
    try {
      const response = await apiFetch(`/clips/${clipId}/export`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ preset }),
      });
      if (response.ok) {
        toast.success(`Export queued for ${preset}`);
      } else {
        toast.error(`Failed to export for ${preset}`);
      }
    } catch (error) {
      console.error("Failed to export clip:", error);
      toast.error("Failed to export clip");
    }
  };

  const formatExportStatus = (clip) => {
    if (!clip?.export_status) return "Not queued";
    return clip.export_status;
  };

  const toggleClipSelection = (clipId) => {
    setSelectedClips(prev =>
      prev.includes(clipId)
        ? prev.filter(id => id !== clipId)
        : [...prev, clipId]
    );
  };

  const handleBulkAction = async (action) => {
    if (selectedClips.length === 0) return;

    try {
      const promises = selectedClips.map(clipId =>
        apiFetch("/clips/review", {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            clip_id: clipId,
            action: action,
            notes: action === 'reject' ? 'Bulk rejected by streamer' : null
          })
        })
      );

      const results = await Promise.all(promises);
      const successCount = results.filter(res => res.ok).length;

      if (successCount === selectedClips.length) {
        toast.success(`Successfully ${action}d ${selectedClips.length} clips`);
      } else {
        toast.warning(`${action}d ${successCount}/${selectedClips.length} clips`);
      }

      setSelectedClips([]);
      fetchClips(); // Refresh the lists
    } catch (error) {
      console.error(`Failed to bulk ${action} clips:`, error);
      toast.error(`Failed to ${action} selected clips`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="w-8 h-8 border-4 border-black border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Video className="w-6 h-6" />
          <h1 className="text-2xl font-bold">Clip Management</h1>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={fetchClips}
            className="px-3 py-1.5 text-sm border border-black/10 rounded-md bg-white hover:bg-black/5 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setActiveTab("pending")}
          className={`px-4 py-2 rounded-lg text-sm font-semibold ${
            activeTab === "pending" ? "bg-black text-white" : "bg-black/5 text-gray-700"
          }`}
        >
          Pending ({pendingClips.length})
        </button>
        <button
          onClick={() => setActiveTab("recent")}
          className={`px-4 py-2 rounded-lg text-sm font-semibold ${
            activeTab === "recent" ? "bg-black text-white" : "bg-black/5 text-gray-700"
          }`}
        >
          Recent ({recentClips.length})
        </button>
      </div>

      {/* Search and Filter Controls */}
      <div className="kazumi-card p-6">
        <div className="flex flex-wrap gap-4 items-center">
          {/* Search */}
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search clips by title, description, or requester..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-black/10 rounded-md focus:ring-2 focus:ring-black/20 focus:border-transparent bg-white"
              />
            </div>
          </div>

          {/* Filters */}
          <div className="flex gap-2">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-black/10 rounded-md focus:ring-2 focus:ring-black/20 focus:border-transparent bg-white"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>

            <select
              value={filterRequester}
              onChange={(e) => setFilterRequester(e.target.value)}
              className="px-3 py-2 border border-black/10 rounded-md focus:ring-2 focus:ring-black/20 focus:border-transparent bg-white"
            >
              <option value="all">All Requesters</option>
              <option value="viewer">Viewers</option>
              <option value="streamer">Streamer</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-2 border border-black/10 rounded-md focus:ring-2 focus:ring-black/20 focus:border-transparent bg-white"
            >
              <option value="date">Sort by Date</option>
              <option value="quality">Sort by Quality</option>
              <option value="requester">Sort by Requester</option>
              <option value="title">Sort by Title</option>
            </select>
          </div>
        </div>

        {/* Bulk Actions */}
        {selectedClips.length > 0 && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md">
            <div className="flex items-center justify-between">
              <span className="text-sm text-amber-800">
                {selectedClips.length} clip{selectedClips.length > 1 ? 's' : ''} selected
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => handleBulkAction('approve')}
                  className="px-3 py-1 bg-green-500 text-white text-sm rounded-md hover:bg-green-600 transition-colors"
                >
                  Approve Selected
                </button>
                <button
                  onClick={() => handleBulkAction('reject')}
                  className="px-3 py-1 bg-red-500 text-white text-sm rounded-md hover:bg-red-600 transition-colors"
                >
                  Reject Selected
                </button>
                <button
                  onClick={() => setSelectedClips([])}
                  className="px-3 py-1 bg-gray-500 text-white text-sm rounded-md hover:bg-gray-600 transition-colors"
                >
                  Clear Selection
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Pending Clips Section */}
      {activeTab === "pending" && (
      <div className="kazumi-card overflow-hidden">
        <div className="p-6 border-b border-black/5">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-bold">Pending Review ({pendingClips.length})</h2>
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {pendingClips.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <AlertCircle className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No clips pending review</p>
            </div>
          ) : (
            pendingClips.map((clip) => (
              <div key={clip.id} className={`p-6 hover:bg-black/5 transition-colors ${selectedClips.includes(clip.id) ? 'bg-amber-50 border-l-4 border-amber-500' : ''}`}>
                <div className="flex items-start gap-4">
                  <input
                    type="checkbox"
                    checked={selectedClips.includes(clip.id)}
                    onChange={() => toggleClipSelection(clip.id)}
                    className="mt-1 w-4 h-4 text-amber-600 bg-gray-100 border-gray-300 rounded focus:ring-amber-500"
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <User className="w-4 h-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-600">
                        {clip.requested_by_name} ({clip.requested_by_type})
                      </span>
                      <span className="text-xs text-gray-400">
                        {new Date(clip.created_at).toLocaleString()}
                      </span>
                    </div>

                    {clip.title && (
                      <h3 className="font-medium text-gray-900 mb-1">{clip.title}</h3>
                    )}
                    {clip.description && (
                      <p className="text-sm text-gray-600 mb-3">{clip.description}</p>
                    )}

                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    {clip.duration_seconds && (
                      <span>Duration: {clip.duration_seconds}s</span>
                    )}
                    {clip.quality_score && (
                        <div className="flex items-center gap-1">
                          <Star className="w-3 h-3" />
                          <span>{clip.quality_score.toFixed(1)}/10</span>
                        </div>
                      )}
                      {clip.sentiment_score && (
                        <span>Sentiment: {clip.sentiment_score.toFixed(2)}</span>
                      )}
                      <span className="px-2 py-0.5 rounded-full border border-black/10 bg-white text-gray-700">
                        Export: {formatExportStatus(clip)}
                      </span>
                    </div>
                    <div className="mt-3">
                      <textarea
                        value={clipNotes[clip.id] ?? clip.notes ?? ""}
                        onChange={(e) => setClipNotes((prev) => ({ ...prev, [clip.id]: e.target.value }))}
                        placeholder="Approval notes (visible to your team)"
                        className="w-full px-3 py-2 border border-black/10 rounded-md text-xs bg-white"
                        rows={2}
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openClip(clip.file_path)}
                      className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
                      title="Preview clip"
                    >
                      <Play className="w-4 h-4" />
                    </button>

                    <button
                      onClick={() => handleReviewClip(clip.id, 'approve')}
                      className="flex items-center gap-1 px-3 py-1.5 bg-black text-white text-sm rounded-md hover:bg-gray-800 transition-colors"
                    >
                      <CheckCircle className="w-3 h-3" />
                      Approve
                    </button>

                    <button
                      onClick={() => handleReviewClip(clip.id, 'reject')}
                      className="flex items-center gap-1 px-3 py-1.5 border border-black/10 text-sm rounded-md hover:bg-black/5 transition-colors"
                    >
                      <XCircle className="w-3 h-3" />
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      )}

      {/* Recent Clips Section */}
      {activeTab === "recent" && (
      <div className="kazumi-card overflow-hidden">
        <div className="p-6 border-b border-black/5">
          <div className="flex items-center gap-3">
            <Eye className="w-5 h-5 text-blue-500" />
            <h2 className="text-lg font-bold">Recent Clips</h2>
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {recentClips.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <Video className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No approved clips yet</p>
            </div>
          ) : (
            recentClips.map((clip) => (
              <div key={clip.id} className="p-6 hover:bg-black/5 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <User className="w-4 h-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-600">
                        {clip.requested_by_name}
                      </span>
                      <span className="text-xs text-gray-400">
                        Approved {new Date(clip.approved_at).toLocaleString()}
                      </span>
                    </div>

                    {clip.title && (
                      <h3 className="font-medium text-gray-900 mb-1">{clip.title}</h3>
                    )}
                    {clip.description && (
                      <p className="text-sm text-gray-600 mb-3">{clip.description}</p>
                    )}

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      {clip.quality_score && (
                        <span>Quality: {clip.quality_score.toFixed(1)}/10</span>
                      )}
                      <span className="px-2 py-0.5 rounded-full border border-black/10 bg-white text-gray-700">
                        Export: {formatExportStatus(clip)}
                      </span>
                      {clip.tags && clip.tags.length > 0 && (
                        <div className="flex gap-1">
                          {clip.tags.slice(0, 3).map((tag, index) => (
                            <span key={index} className="px-2 py-0.5 bg-gray-100 rounded text-xs">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {clip.notes && (
                      <div className="mt-2 text-xs text-gray-500">
                        Notes: {clip.notes}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openClip(clip.file_path)}
                      className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                      title="Open clip"
                    >
                      <Play className="w-4 h-4" />
                    </button>

                    <button
                      onClick={() => handleExportClip(clip.id, "tiktok")}
                      className="flex items-center gap-1 px-3 py-1.5 bg-black text-white text-sm rounded-md hover:bg-gray-800 transition-colors"
                    >
                      <Download className="w-3 h-3" />
                      TikTok
                    </button>

                    <button
                      onClick={() => handleExportClip(clip.id, "shorts")}
                      className="flex items-center gap-1 px-3 py-1.5 border border-black/10 text-sm rounded-md hover:bg-black/5 transition-colors"
                    >
                      Shorts
                    </button>

                    <button
                      onClick={() => handleExportClip(clip.id, "reels")}
                      className="flex items-center gap-1 px-3 py-1.5 border border-black/10 text-sm rounded-md hover:bg-black/5 transition-colors"
                    >
                      Reels
                    </button>

                    <button
                      onClick={() => handleReviewClip(clip.id, 'delete')}
                      className="flex items-center gap-1 px-3 py-1.5 border border-red-300 text-red-600 text-sm rounded-md hover:bg-red-50 transition-colors"
                    >
                      <XCircle className="w-3 h-3" />
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      )}
    </div>
  );
}

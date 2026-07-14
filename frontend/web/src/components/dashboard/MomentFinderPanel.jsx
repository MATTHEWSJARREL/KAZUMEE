"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/apiClient";

const DEFAULT_PLATFORMS = ["twitch", "youtube", "tiktok", "kick"];

export default function MomentFinderPanel() {
  const [momentQuery, setMomentQuery] = useState("");
  const [momentResults, setMomentResults] = useState([]);
  const [momentLoading, setMomentLoading] = useState(false);
  const [momentMessage, setMomentMessage] = useState("");
  const [momentPlatforms, setMomentPlatforms] = useState(DEFAULT_PLATFORMS);
  const [savedMoments, setSavedMoments] = useState([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("kazumi_saved_moments");
      if (raw) setSavedMoments(JSON.parse(raw));
    } catch {
      setSavedMoments([]);
    }
  }, []);

  const searchMoments = async () => {
    if (!momentQuery.trim()) return;
    setMomentLoading(true);
    setMomentMessage("");
    try {
      const res = await apiFetch("/api/moment-finder/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: momentQuery.trim(),
          platforms: momentPlatforms,
          limit: 5,
        }),
      });
      const data = await res.json();
      setMomentResults(data.results || []);
      if (data.status !== "success") {
        setMomentMessage(data.message || "No results yet.");
      }
    } catch (error) {
      console.error("Moment Finder error:", error);
      setMomentMessage("Search failed. Check backend or API key.");
    } finally {
      setMomentLoading(false);
    }
  };

  const saveMoment = (item) => {
    const next = [item, ...savedMoments].slice(0, 20);
    setSavedMoments(next);
    localStorage.setItem("kazumi_saved_moments", JSON.stringify(next));
    toast.success("Saved to collection");
  };

  const togglePlatform = (platform) => {
    setMomentPlatforms((prev) =>
      prev.includes(platform) ? prev.filter((value) => value !== platform) : [...prev, platform],
    );
  };

  return (
    <div className="kazumi-card p-6 mb-8">
      <div className="flex items-center justify-between gap-4 mb-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Moment Finder</div>
          <h2 className="text-lg font-bold">Search Clips Across Platforms</h2>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        {DEFAULT_PLATFORMS.map((platform) => (
          <button
            key={platform}
            onClick={() => togglePlatform(platform)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${
              momentPlatforms.includes(platform) ? "bg-black text-white border-black" : "bg-white text-gray-600 border-gray-200"
            }`}
          >
            {platform}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {["best clip yesterday", "most viral moment this week", "funniest reaction clip", "top highlight last stream"].map((preset) => (
          <button
            key={preset}
            onClick={() => setMomentQuery(preset)}
            className="px-3 py-1.5 rounded-full text-xs font-semibold border border-gray-200 bg-gray-50 text-gray-600 hover:text-black"
          >
            {preset}
          </button>
        ))}
      </div>

      <div className="flex flex-col md:flex-row gap-3 mb-4">
        <input
          value={momentQuery}
          onChange={(event) => setMomentQuery(event.target.value)}
          placeholder="e.g., MrBeast money clip yesterday"
          className="flex-1 px-4 py-2 border border-black/10 rounded-md text-sm bg-white"
        />
        <button onClick={() => void searchMoments()} className="px-4 py-2 bg-black text-white rounded-md text-sm" disabled={momentLoading}>
          {momentLoading ? "Searching..." : "Search"}
        </button>
      </div>

      {momentMessage && <div className="text-xs text-gray-500 mb-3">{momentMessage}</div>}

      <div className="space-y-3">
        {momentResults.map((item, index) => (
          <div key={`${item.url}-${index}`} className="border border-black/5 rounded-xl p-4 hover:border-black/20 transition-colors bg-white">
            <a href={item.url} target="_blank" rel="noreferrer" className="block">
              <div className="text-sm font-semibold text-gray-900">{item.title || "Untitled Result"}</div>
              <div className="text-xs text-gray-500 break-all">{item.url}</div>
              {item.snippet && <div className="text-xs text-gray-600 mt-2">{item.snippet}</div>}
            </a>
            <div className="mt-3">
              <button onClick={() => saveMoment(item)} className="text-xs font-semibold text-gray-700 hover:text-black">
                Save to Collection
              </button>
            </div>
          </div>
        ))}
        {momentResults.length === 0 && !momentMessage && <div className="text-xs text-gray-500">No results yet.</div>}
      </div>

      {savedMoments.length > 0 && (
        <div className="mt-6">
          <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Saved Collection</div>
          <div className="space-y-2">
            {savedMoments.map((item, index) => (
              <a
                key={`${item.url}-saved-${index}`}
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="block border border-gray-100 rounded-md p-3 hover:border-gray-300 transition-colors"
              >
                <div className="text-xs font-semibold text-gray-800">{item.title || "Untitled Result"}</div>
                <div className="text-[10px] text-gray-500 break-all">{item.url}</div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { Filter, X } from "lucide-react";

export interface ClipsFilters {
  type: "all" | "ai-detected" | "manual" | "auto-clipped";
  performance: "all" | "viral" | "hot" | "trending" | "low";
  dateRange: "all" | "week" | "month" | "year";
  platforms: string[];
}

interface ClipsFilterSidebarProps {
  filters: ClipsFilters;
  onFiltersChange: (filters: ClipsFilters) => void;
  platforms?: string[];
}

export default function ClipsFilterSidebar({
  filters,
  onFiltersChange,
  platforms = ["Twitch", "YouTube", "TikTok", "Kick"],
}: ClipsFilterSidebarProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleTypeChange = (type: ClipsFilters["type"]) => {
    onFiltersChange({ ...filters, type });
  };

  const handlePerformanceChange = (performance: ClipsFilters["performance"]) => {
    onFiltersChange({ ...filters, performance });
  };

  const handleDateChange = (dateRange: ClipsFilters["dateRange"]) => {
    onFiltersChange({ ...filters, dateRange });
  };

  const handlePlatformChange = (platform: string) => {
    const updated = filters.platforms.includes(platform)
      ? filters.platforms.filter((p) => p !== platform)
      : [...filters.platforms, platform];
    onFiltersChange({ ...filters, platforms: updated });
  };

  const resetFilters = () => {
    onFiltersChange({
      type: "all",
      performance: "all",
      dateRange: "all",
      platforms: [],
    });
  };

  return (
    <>
      {/* Mobile Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden fixed bottom-6 right-6 z-40 p-4 rounded-full
                 bg-purple-600 text-white shadow-lg hover:bg-purple-700
                 transition-colors flex items-center gap-2"
      >
        <Filter className="w-5 h-5" />
        <span>Filters</span>
      </button>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed md:relative inset-y-0 left-0 z-40 w-64 bg-slate-900/95
                   backdrop-blur-xl border-r border-white/10 p-6
                   transform transition-transform md:transform-none
                   ${isOpen ? "translate-x-0" : "-translate-x-full"}
                   md:translate-x-0 overflow-y-auto`}
      >
        {/* Close Button */}
        <button
          onClick={() => setIsOpen(false)}
          className="md:hidden absolute top-4 right-4 p-2 hover:bg-white/10 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="space-y-6">
          {/* Header */}
          <div>
            <h3 className="text-lg font-bold text-white mb-4">Filters</h3>
          </div>

          {/* Clip Type Filter */}
          <div>
            <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
              Clip Type
            </h4>
            <div className="space-y-2">
              {[
                { value: "all", label: "All Clips" },
                { value: "ai-detected", label: "AI Detected" },
                { value: "manual", label: "Manual" },
                { value: "auto-clipped", label: "Auto-Clipped" },
              ].map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => handleTypeChange(value as any)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium
                           transition-all ${
                             filters.type === value
                               ? "bg-purple-600 text-white"
                               : "bg-white/5 text-gray-300 hover:bg-white/10"
                           }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Performance Filter */}
          <div>
            <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
              Performance
            </h4>
            <div className="space-y-2">
              {[
                { value: "all", label: "All", icon: "📊" },
                { value: "viral", label: "Viral", icon: "🚀" },
                { value: "hot", label: "Hot", icon: "🔥" },
                { value: "trending", label: "Trending", icon: "📈" },
                { value: "low", label: "Low", icon: "📉" },
              ].map(({ value, label, icon }) => (
                <button
                  key={value}
                  onClick={() => handlePerformanceChange(value as any)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium
                           transition-all flex items-center gap-2 ${
                             filters.performance === value
                               ? "bg-purple-600 text-white"
                               : "bg-white/5 text-gray-300 hover:bg-white/10"
                           }`}
                >
                  <span>{icon}</span>
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Date Range Filter */}
          <div>
            <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
              Date Range
            </h4>
            <div className="space-y-2">
              {[
                { value: "all", label: "All Time" },
                { value: "week", label: "Last 7 Days" },
                { value: "month", label: "Last 30 Days" },
                { value: "year", label: "Last Year" },
              ].map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => handleDateChange(value as any)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium
                           transition-all ${
                             filters.dateRange === value
                               ? "bg-purple-600 text-white"
                               : "bg-white/5 text-gray-300 hover:bg-white/10"
                           }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Platform Filter */}
          <div>
            <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
              Platforms
            </h4>
            <div className="space-y-2">
              {platforms.map((platform) => (
                <label
                  key={platform}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg
                          hover:bg-white/10 cursor-pointer transition-all"
                >
                  <input
                    type="checkbox"
                    checked={filters.platforms.includes(platform)}
                    onChange={() => handlePlatformChange(platform)}
                    className="w-4 h-4 rounded border-gray-400 text-purple-600
                           focus:ring-2 focus:ring-purple-500"
                  />
                  <span className="text-sm font-medium text-gray-300">
                    {platform}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Reset Button */}
          <button
            onClick={resetFilters}
            className="w-full px-4 py-2 rounded-lg bg-white/10 text-gray-300
                     hover:bg-white/20 text-sm font-semibold transition-all"
          >
            Reset Filters
          </button>
        </div>
      </div>
    </>
  );
}
